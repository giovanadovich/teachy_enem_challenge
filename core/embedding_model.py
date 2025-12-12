# core/embedding_model.py
from typing import List
import os
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings 

EMBEDDING_MODEL = 'models/text-embedding-004' 
EMBEDDING_SIZE = 768 

class EmbeddingModel:
    """Responsável por gerar vetores (embeddings) a partir de texto usando LangChain/Gemini."""
    
    def __init__(self):
        self.EMBEDDING_SIZE = 768
        # A chave GEMINI_API_KEY deve ser setada como variável de ambiente
        if not os.getenv("GEMINI_API_KEY"):
            print("ERRO: Variável GEMINI_API_KEY não está definida.")

        # Cria o objeto de embedding
        self.embed_function = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
        )

    def generate_embedding(self, text: str) -> List[float]:
        """Gera um embedding (vetor) para um dado texto."""
        if not text:
            return [0.0] * EMBEDDING_SIZE
            
        try:
            # Usa o método embed_query
            embedding_vector = self.embed_function.embed_query(text)
            
            return embedding_vector
            
        except Exception as e:
             raise Exception(f"Falha de API no LangChain/Gemini. Verifique sua chave. {type(e).__name__}: {e}")

embedding_model = EmbeddingModel()