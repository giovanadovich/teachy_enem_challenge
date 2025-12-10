# db/vector_db.py
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams
from typing import List, Tuple

COLLECTION_NAME = "enem_questions"
EMBEDDING_SIZE = 768 # Tamanho do embedding (ajuste se mudar o modelo)

class VectorDBManager:
    """Gerencia a conexão e operações com o Qdrant In-Memory."""
    
    def __init__(self, location: str = ":memory:"): 
        self.client = QdrantClient(location=location)
        self.ensure_collection_exists()

    def ensure_collection_exists(self):
        """Cria a coleção se ela não existir, com os parâmetros corretos."""
        collections = self.client.get_collections().collections
        if COLLECTION_NAME not in [c.name for c in collections]:
            print(f"Creating Qdrant In-Memory collection: {COLLECTION_NAME}")
            self.client.recreate_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=EMBEDDING_SIZE, distance=Distance.COSINE),
            )

    def insert_vector(self, vector: List[float], q_id: str, payload: dict = None):
        """Insere um novo vetor (embedding) no Qdrant."""
        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=q_id,
                    vector=vector,
                    payload=payload if payload is not None else {}
                )
            ]
        )

    def search_vectors(self, query_vector: List[float], limit: int) -> List[Tuple[str, float]]:
        """
        Busca vetores semelhantes à query.
        Retorna uma lista de tuplas (ID da Questão, Score de Similaridade).
        """
        search_result = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit
        )
        return [(str(hit.id), hit.score) for hit in search_result]

vector_db_manager = VectorDBManager()