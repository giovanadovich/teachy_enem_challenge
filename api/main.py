# api/main.py

import os
import db.schemas # Força a importação do modelo de dados
from fastapi import FastAPI, Depends, HTTPException, status
from typing import List, Dict, Any

from core.question_service import QuestionService
from qdrant_client import QdrantClient
from db.schemas import QuestionSearch, QuestionTopic, QuestionBase 


# Verifica a chave de API
if not os.getenv("GEMINI_API_KEY"):
    print("AVISO CRÍTICO: Variável de ambiente GEMINI_API_KEY não está definida.")

# ----------------------------------------------------
# 1. INICIALIZAÇÃO DOS CLIENTES E SERVIÇOS (DIRETA E CENTRALIZADA)
# ----------------------------------------------------

# Cria o cliente Qdrant In-Memory
qdrant_client = QdrantClient(":memory:")

# Inicializa o QuestionService. Isso DISPARA TODO O PROCESSO de DB/Qdrant/Indexação.
question_service = QuestionService(qdrant_client=qdrant_client)

# Inicialização da Aplicação FastAPI
app = FastAPI(
    title="Teachy ENEM RAG API",
    description="API de Busca por Similaridade Semântica de Questões do ENEM.",
    version="1.0.0"
)

# ----------------------------------------------------
# 2. FUNÇÃO DE DEPENDÊNCIA (Para endpoints)
# ----------------------------------------------------

def get_question_service() -> QuestionService:
    return question_service

# ----------------------------------------------------
# 3. ENDPOINTS DA API
# ----------------------------------------------------

@app.get("/", tags=["Root"])
def read_root():
    """Endpoint raiz para verificar o status da API (Health Check)."""
    return {"message": "API de Busca ENEM operacional."}

@app.get("/status/count", tags=["Status"], response_model=Dict[str, Any])
def get_collection_count_endpoint(
    service: QuestionService = Depends(get_question_service)
):
    """Retorna o número atual de questões indexadas no Qdrant."""
    count = service.get_collection_count()
    return {"collection_name": service.collection_name, "count": count}

@app.get("/questions", tags=["Questions"], response_model=List[QuestionTopic])
def search_questions_endpoint(
    topic: str, 
    amount: int = 5,
    service: QuestionService = Depends(get_question_service)
):
    """Busca questões do ENEM por similaridade semântica (RAG)."""
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O parâmetro 'topic' não pode ser vazio."
        )

    try:
        results = service.search_questions(topic=topic, amount=amount)
        return results

    except Exception as e:
        print(f"ERRO CRÍTICO no GET /questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor ao processar a requisição."
        )

@app.post("/questions", tags=["Questions"], status_code=status.HTTP_201_CREATED)
def add_new_question_endpoint(
    question_data: QuestionBase,
    service: QuestionService = Depends(get_question_service)
):
    """Insere uma nova questão no banco de dados SQL e no índice vetorial Qdrant."""
    try:
        service.add_single_question(question_data)
        return {"message": "Questão inserida com sucesso."}
    except Exception as e:
        print(f"ERRO CRÍTICO no POST /questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor ao inserir a questão."
        )