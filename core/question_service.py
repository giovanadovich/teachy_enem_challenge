# core/question_service.py

import json
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Importações de dependências (Assegure que QuestionBase esteja em db.schemas)
from .embedding_model import embedding_model
from db.sql_db import SessionLocal
from db.schemas import QuestionModel, QuestionTopic, QuestionBase 

class QuestionService:
    """
    Serviço responsável por interagir com o modelo de embedding e o banco de dados Qdrant/SQL.
    """
    
    def __init__(self, qdrant_client: QdrantClient):
        self.qdrant_client = qdrant_client
        self.collection_name = "enem_questions"
        self._init_qdrant_collection()
        
        self._check_and_load_data()

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
        """Verifica se há dados no Qdrant e carrega do SQL/JSON se necessário."""
        from db.init_db import load_initial_data
        
        try:
            count_result = self.qdrant_client.count(collection_name=self.collection_name, exact=True)
            if count_result.count == 0:
                print("--- Iniciando Carga de Dados Iniciais de data/initial_enem_data.json ---")
                load_initial_data(self) 
        except Exception as e:
            pass

    def _persist_question_and_vector(self, question_data: dict, vector: List[float]):
        """Salva a questão no SQL e insere o vetor no Qdrant."""
        
        # 1. Salvar no SQL (para obter o ID)
        with SessionLocal() as db:
            new_question = QuestionModel(
                text=question_data['text'],
                area=question_data['area'],
                alternatives=json.dumps(question_data['alternatives']),
                correct_answer=question_data['correct_answer']
            )
            db.add(new_question)
            db.commit()
            db.refresh(new_question)
            question_id = new_question.id

        # 2. Inserir no Qdrant
        payload = question_data.copy()
        payload['id'] = question_id
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
        
    # ⬇️ NOVO MÉTODO PARA ADICIONAR UMA ÚNICA QUESTÃO VIA POST
    def add_single_question(self, question: QuestionBase):
        """Gera o embedding e persiste uma única questão no SQL e Qdrant."""
        
        # 1. Converter QuestionBase (Pydantic) para dicionário
        # O método .model_dump() é preferido em versões mais recentes do Pydantic, 
        # mas .dict() funciona em muitas versões
        question_data = question.dict()
        
        # 2. Gerar vetor
        vector = embedding_model.generate_embedding(question_data['text'])
        
        # 3. Persistir (reutilizando a lógica existente)
        self._persist_question_and_vector(
            question_data=question_data, 
            vector=vector
        )

    def search_questions(self, topic: str, amount: int = 5) -> List[Dict[str, Any]]:
        """
        Gera o embedding para o tópico (query) e busca questões similares no Qdrant.
        """
        query_vector = embedding_model.generate_embedding(topic)

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
                    "text": question_data.get("text"),
                    "area": question_data.get("area"),
                    "alternatives": json.loads(question_data.get("alternatives")), 
                    "correct_answer": question_data.get("correct_answer"),
                    "score": hit.score
                })
            
            return results
            
        except Exception as e:
            print(f"ERRO CRÍTICO no search_questions: {e}")
            raise Exception("Erro interno do servidor ao processar a busca no banco de dados vetorial.")