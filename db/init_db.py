# db/init_db.py
import json
import os
from tqdm import tqdm
from db.sql_db import init_db as init_sql_db
from api import QuestionIn
from pydantic import ValidationError # Importação adicionada para tratar erros específicos

DATA_FILE_PATH = "data/initial_enem_data.json"

def load_initial_data(service, data_path: str):
    """
    Carrega questões de um arquivo JSON, salva no DB principal 
    e indexa no Vector DB, usando a instância 'service' passada.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(BASE_DIR, 'data', 'initial_enem_data.json')
    0
    # Garantir que o diretório exista
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    
    if not os.path.exists(data_path) or os.path.getsize(data_path) == 0:
        print(f"⚠️ Arquivo de dados inicial NÃO ENCONTRADO ou VAZIO em {data_path}. Execute 'python collect_data.py'.")
        return

    print(f"--- Iniciando Carga de Dados Iniciais de {data_path} ---")
    
    with open(data_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("Erro ao decodificar JSON. Verifique o arquivo.")
            return

    if not isinstance(data, list):
         print("Erro: O arquivo JSON não contém uma lista no nível raiz.")
         return
         
    total_loaded = 0
    for item in tqdm(data, desc="Indexando Questões ENEM"):
        try:
            # 1. Valida o item com o Pydantic (QuestionIn)
            question_in = QuestionIn(**item)
            
            # 2. Persiste e Indexa
            service.persist_new_question(question_in, source="INITIAL_LOAD")
            total_loaded += 1
            
        except ValidationError as e:
            # Captura erros de formato/tipo de dado (Pydantic)
            print(f"\n[ERRO Pydantic - Descarte de Item] Falha de validação: {e.errors()[0]['loc']} -> {e.errors()[0]['msg']}. Item descartado.")
        except Exception as e:
            # Captura outros erros (ex: falha na API Gemini ao gerar embedding)
            print(f"\n[ERRO GERAL DE INDEXAÇÃO] Falha ao processar item: {type(e).__name__}: {e}. Item descartado.")
            
            # Se o erro for crítico (como a chave Gemini falhando), podemos querer parar
            if "Missing key inputs argument" in str(e):
                 print("\nERRO CRÍTICO: Chave Gemini não encontrada/inválida. Parando a indexação.")
                 break
            
            continue
            
    print(f"\n--- Carga Inicial Finalizada. Total de questões carregadas: {total_loaded} ---")