# core/question_service.py

import json
import os 
from typing import List, Dict, Any, Optional

# Se você migrar para LangChain, substitua as importações Qdrant e embedding_model
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

# Importações de dependências
from .embedding_model import embedding_model
from db.sql_db import SessionLocal, Base, engine 
from db.schemas import QuestionModel, QuestionTopic, QuestionBase 

class QuestionService:
    """
    Serviço centralizado que gerencia a inicialização do DB, Qdrant e a lógica de busca/persisitência.
    """
    
    def __init__(self, qdrant_client: QdrantClient):
        self.qdrant_client = qdrant_client
        self.collection_name = "enem_questions"
        
        # Sequência de Inicialização Forçada
        Base.metadata.create_all(bind=engine)
        
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

    def _get_vector_context(self, statement: str, topic: str, alternatives: List[str]) -> str:
        """
        Gera a string de contexto completa para o embedding (Context Stacking).
        Esta é a chave para uma busca mais precisa.
        """
        alternatives_text = " ".join(alternatives)
        return (
            f"QUESTÃO - ÁREA {topic.upper()}: {statement}. "
            f"Detalhes: {alternatives_text}"
        )

    def _load_initial_data(self): 
        """
        Lógica de carga inicial, interna ao QuestionService.
        """
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
                
                # ⬇️ APLICAÇÃO DO CONTEXT STACKING
                context_string = self._get_vector_context(
                    statement=item['statement'],
                    topic=item['topic'],
                    alternatives=alternatives
                )
                
                # Gerar vetor
                vector = embedding_model.generate_embedding(context_string) 
                
                # Persistir
                self._persist_question_and_vector(
                    question_data=item, 
                    vector=vector
                )
                
                total_loaded += 1
                
            except Exception as e:
                print(f"\n[ERRO CRÍTICO NO PIPELINE] Falha na indexação do item {i+1}: {type(e).__name__}: {e}. Item descartado.")
                continue 

        print("\n--- Carga Inicial Finalizada. Total de questões carregadas:", total_loaded, "---")


    def get_collection_count(self) -> int:
        """Retorna o número exato de pontos (questões) na coleção Qdrant."""
        try:
            # Usando count() para verificar o número de itens
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
                alternatives=question_data['alternatives'], 
                correct_answer=question_data['correct_answer']
            )
            db.add(new_question)
            db.commit()
            db.refresh(new_question)
            question_id = new_question.id

        # 2. Inserir no Qdrant
        payload = question_data.copy()
        payload['id'] = question_id
        # Garante que as alternativas sejam strings JSON no payload do Qdrant
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
        
        # ⬇️ APLICAÇÃO DO CONTEXT STACKING para novas questões
        context_string = self._get_vector_context(
            statement=question_data['statement'],
            topic=question_data['topic'],
            alternatives=question_data['alternatives']
        )
        
        vector = embedding_model.generate_embedding(context_string) 
        self._persist_question_and_vector(
            question_data=question_data, 
            vector=vector
        )

    def search_questions(self, topic: str, amount: int = 15) -> List[Dict[str, Any]]:
        """
        Busca questões similares no Qdrant. 
        O parâmetro 'topic' do FastAPI agora é usado como query de busca.
        """
        
        # 1. ⬇️ ENRIQUECIMENTO DA QUERY: Adicionar contexto na busca
        try:
            enriched_query_text = f"Questão do ENEM na área de {topic}"
            query_vector = embedding_model.generate_embedding(enriched_query_text)
        except Exception as e:
            print(f"ERRO CRÍTICO ao gerar embedding para a busca: {e}")
            raise 
        
        # 2. APLICAÇÃO DO PAYLOAD FILTERING (Filtragem Estrutural)
        search_filter: Optional[Filter] = None
        TARGET_TOPICS = ["linguagens", "ciencias-natureza", "ciencias-humanas", "matematica"]
        
        if topic.lower() in TARGET_TOPICS:
            # Se a query do usuário for um tópico exato, filtramos o índice.
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="topic", 
                        match=MatchValue(value=topic.lower())
                    )
                ]
            )
            
        try:
            # ⬇️ Usando search_points para compatibilidade com a versão 1.9.0 do Qdrant
            search_result = self.qdrant_client.search( 
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=search_filter, # Aplica o filtro
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