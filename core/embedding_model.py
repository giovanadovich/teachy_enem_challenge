# core/embedding_model.py
from typing import List
from google import genai
from google.genai.errors import APIError

EMBEDDING_MODEL = 'text-embedding-004' 
EMBEDDING_SIZE = 768 

class EmbeddingModel:
    """Responsável por gerar vetores (embeddings) a partir de texto."""
    
    def __init__(self):
        try:
            self.client = genai.Client()
        except Exception as e:
            print(f"ERRO: Cliente GenAI não pôde ser inicializado. Verifique GEMINI_API_KEY. {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """Gera um embedding (vetor) para um dado texto."""
        if not text:
            return [0.0] * EMBEDDING_SIZE
            
        try:
            result = self.client.models.embed_content(
                model=EMBEDDING_MODEL,
                content=text,
                task_type="RETRIEVAL_DOCUMENT"
            )
            return result['embedding']
        except APIError as e:
            print(f"Erro na geração de embedding: {e}")
            raise

embedding_model = EmbeddingModel()