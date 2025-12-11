# api/main.py

import os
from fastapi import FastAPI, Depends, HTTPException, status
from typing import List

# Importações de Serviços e Modelos
from core.question_service import QuestionService
from db.schemas import QuestionSearch, QuestionTopic, QuestionBase # Importado QuestionBase para o POST
from qdrant_client import QdrantClient

# Verifica a chave de API
if not os.getenv("GEMINI_API_KEY"):
    print("AVISO CRÍTICO: Variável de ambiente GEMINI_API_KEY não está definida.")

# ----------------------------------------------------
# 1. INICIALIZAÇÃO DOS CLIENTES E SERVIÇOS
# ----------------------------------------------------

# Cria o cliente Qdrant In-Memory
qdrant_client = QdrantClient(":memory:")

# Inicializa o QuestionService, passando o cliente Qdrant
question_service = QuestionService(qdrant_client=qdrant_client)

# Inicialização da Aplicação FastAPI
app = FastAPI(
    title="Teachy ENEM RAG API",
    description="API de Busca por Similaridade Semântica de Questões do ENEM.",
    version="1.0.0"
)

# ----------------------------------------------------
# 2. ENDPOINTS DA API
# ----------------------------------------------------

@app.get("/", tags=["Root"])
def read_root():
    """Endpoint raiz para verificar o status da API (Health Check)."""
    return {"message": "API de Busca ENEM operacional."}

@app.get("/questions", tags=["Questions"], response_model=List[QuestionTopic])
def search_questions_endpoint(
    topic: str, 
    amount: int = 5,
    service: QuestionService = Depends(lambda: question_service)
):
    """
    Busca questões do ENEM por similaridade semântica (RAG).
    
    Args:
        topic (str): O tópico ou pergunta para buscar.
        amount (int): O número de questões a retornar.
    """
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

# ⬇️ NOVO ENDPOINT PARA CRIAÇÃO DE QUESTÕES
@app.post("/questions", tags=["Questions"], status_code=status.HTTP_201_CREATED)
def add_new_question_endpoint(
    question_data: QuestionBase,
    service: QuestionService = Depends(lambda: question_service)
):
    """
    Insere uma nova questão no banco de dados SQL e no índice vetorial Qdrant.
    
    O corpo da requisição (body) deve conter os campos: text, area, 
    alternatives (lista de strings) e correct_answer.
    """
    try:
        service.add_single_question(question_data)
        return {"message": "Questão inserida com sucesso."}
    except Exception as e:
        print(f"ERRO CRÍTICO no POST /questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor ao inserir a questão."
        )