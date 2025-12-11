# core/question_service.py

import json
import os # Necessário para o método interno _load_initial_data
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Importações de dependências
from .embedding_model import embedding_model
# Importa o motor do banco de dados (Base e engine) para forçar o mapeamento
from db.sql_db import SessionLocal, Base, engine 
from db.schemas import QuestionModel, QuestionTopic, QuestionBase 

class QuestionService:
    """
    Serviço centralizado que gerencia a inicialização do DB, Qdrant e a lógica de busca/persisitência.
    """
    
    def __init__(self, qdrant_client: QdrantClient):
        self.qdrant_client = qdrant_client
        self.collection_name = "enem_questions"
        Base.metadata.create_all(bind=engine)
        # ⬇️ CHAVE: Sequência de Inicialização Forçada
        self._init_sql_db()
        self._init_qdrant_collection()
        self._check_and_load_data()

    def _init_sql_db(self):
        """Força o mapeamento do SQLAlchemy e a criação de tabelas."""
        print("DEBUG QS: Forçando mapeamento e criação de tabelas SQL.")
        try:
            # Garante que as classes sejam mapeadas e cria as tabelas
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"ERRO CRÍTICO no mapeamento do SQLAlchemy: {e}")
            raise # Interrompe a inicialização se falhar

    def _init_qdrant_collection(self):
        """Inicializa a coleção no Qdrant se ela não existir."""
        try:
            collections = self.qdrant_client.get_collections().collections
            if self.collection_name not in [c.name for c in collections]:
                print(f"Creating Qdrant In-Memory collection: {self.collection_name}")
                self.qdrant_client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=embedding_model.EMBEDDING_SIZE, 
                        distance=Distance.COSINE
                    ),
                )
        except Exception as e:
            print(f"Error initializing Qdrant collection: {e}")
            raise

    def _check_and_load_data(self):
        """Verifica se há dados no Qdrant e dispara a carga se necessário."""
        
        try:
            count_result = self.qdrant_client.count(collection_name=self.collection_name, exact=True)
            if count_result.count == 0:
                print("--- Iniciando Carga de Dados Iniciais (Indexação) ---")
                self._load_initial_data() 
            else:
                print(f"--- Qdrant já contém {count_result.count} questões. Pulando carga inicial. ---")

        except Exception as e:
            print(f"Erro ao verificar contagem inicial no Qdrant: {e}")
            pass

    def _load_initial_data(self): 
        """
        Lógica de carga inicial, agora interna ao QuestionService.
        """
        # Define o caminho do arquivo JSON
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        DATA_FILE_PATH = os.path.join(CURRENT_DIR, '..', 'data', 'initial_enem_data.json')
        
        if not os.path.exists(DATA_FILE_PATH):
            print(f"[ERRO DE ARQUIVO] Arquivo não encontrado: {DATA_FILE_PATH}")
            return

        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        total_loaded = 0
        total_items = len(data)
        
        print(f"DEBUG: Iniciando loop de indexação de {total_items} itens.")
        
        for i, item in enumerate(data): 
            try:
                # Filtro de dados para evitar erros de validação (None)
                if not item.get('statement') or not item.get('topic'):
                    continue
                alternatives = item.get('alternatives')
                if not alternatives or any(alt is None for alt in alternatives):
                    continue
                
                print(f"DEBUG INIT: Processando item {i+1}/{total_items} - Área: {item.get('topic')}") 
                
                # Gerar vetor
                vector = embedding_model.generate_embedding(item['statement']) 
                
                # Persistir
                self._persist_question_and_vector(
                    question_data=item, 
                    vector=vector
                )
                
                total_loaded += 1
                
            except Exception as e:
                # Captura e loga qualquer erro de persistência, mas continua o loop
                print(f"\n[ERRO CRÍTICO NO PIPELINE] Falha na indexação do item {i+1} ({item.get('topic')}): {type(e).__name__}: {e}. Item descartado.")
                continue 

        print("\n--- Carga Inicial Finalizada. Total de questões carregadas:", total_loaded, "---")


    def get_collection_count(self) -> int:
        """Retorna o número exato de pontos (questões) na coleção Qdrant."""
        try:
            count_result = self.qdrant_client.count(
                collection_name=self.collection_name, 
                exact=True
            )
            return count_result.count
        except Exception:
            return 0

    def _persist_question_and_vector(self, question_data: dict, vector: List[float]):
        """Salva a questão no SQL e insere o vetor no Qdrant."""
        
        # 1. Salvar no SQL (para obter o ID)
        with SessionLocal() as db:
            new_question = QuestionModel(
                text=question_data['statement'],
                area=question_data['topic'],     
                alternatives=question_data['alternatives'], # Lista direta para campo JSON/Text
                correct_answer=question_data['correct_answer']
            )
            db.add(new_question)
            db.commit()
            db.refresh(new_question)
            question_id = new_question.id

        # 2. Inserir no Qdrant
        payload = question_data.copy()
        payload['id'] = question_id
        # Converte a lista para string JSON para o payload do Qdrant
        payload['alternatives'] = json.dumps(payload['alternatives']) 
        
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=question_id,
                    vector=vector,
                    payload=payload
                )
            ],
            wait=True
        )

    def add_single_question(self, question: QuestionBase):
        """Gera o embedding e persiste uma única questão no SQL e Qdrant."""
        
        question_data = question.dict()
        vector = embedding_model.generate_embedding(question_data['statement']) 
        self._persist_question_and_vector(
            question_data=question_data, 
            vector=vector
        )

    def search_questions(self, topic: str, amount: int = 5) -> List[Dict[str, Any]]:
        """Busca questões similares no Qdrant."""
        try:
            query_vector = embedding_model.generate_embedding(topic)
        except Exception as e:
            print(f"ERRO CRÍTICO ao gerar embedding para a busca: {e}")
            raise 
        
        try:
            search_result = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=amount,
                with_payload=True,
            )
            
            results = []
            for hit in search_result:
                question_data = hit.payload
                
                results.append({
                    "id": question_data.get("id"),
                    "text": question_data.get("statement"),
                    "area": question_data.get("topic"),
                    "alternatives": json.loads(question_data.get("alternatives")), 
                    "correct_answer": question_data.get("correct_answer"),
                    "score": hit.score
                })
            
            return results
            
        except Exception as e:
            print(f"ERRO CRÍTICO no search_questions (Qdrant Search): {e}")
            raise Exception("Erro interno do servidor ao processar a busca no banco de dados vetorial.")