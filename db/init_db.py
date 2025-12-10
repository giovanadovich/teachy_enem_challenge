# db/init_db.py
import json
import os
from tqdm import tqdm
from api.models import QuestionIn, QuestionInternal
from core.question_service import QuestionService
from db.sql_db import init_db as init_sql_db

DATA_FILE_PATH = "data/initial_enem_data.json"

# Esta função DEVE ser chamada no main.py para garantir que o Qdrant In-Memory
# e o SQLite persistente sejam preenchidos no início de cada execução.

def load_initial_data(service: QuestionService, data_path: str):
    """
    Carrega questões de um arquivo JSON, salva no DB principal 
    e indexa no Vector DB.
    """
    # Cria o diretório de dados se não existir, mas não cria o arquivo.
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    
    if not os.path.exists(data_path):
        print(f"⚠️ Arquivo de dados inicial NÃO ENCONTRADO em {data_path}. Pulando carga.")
        print("A API funcionará, mas apenas gerando novas questões na primeira requisição.")
        return

    print(f"--- Iniciando Carga de Dados Iniciais de {data_path} ---")
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    total_loaded = 0
    for item in tqdm(data, desc="Processando Questões ENEM"):
        try:
            question_in = QuestionIn(**item)
            service.persist_new_question(question_in, source="INITIAL_LOAD")
            total_loaded += 1
        except Exception as e:
            # Captura erros de parsing/validação ou falhas de LLM/DB
            print(f"\nErro ao carregar item: {e}. Item: {item.get('statement', 'Sem enunciado')[:50]}...")
            continue
            
    print(f"--- Carga Inicial Finalizada. Total de questões carregadas: {total_loaded} ---")


if __name__ == "__main__":
    init_sql_db()
    service = QuestionService() 
    load_initial_data(service, DATA_FILE_PATH)