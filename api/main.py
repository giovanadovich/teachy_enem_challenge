# api/main.py
from fastapi import FastAPI, HTTPException
from api.models import QuestionIn, QuestionOut
from core.question_service import QuestionService
from db.sql_db import init_db 
from db.init_db import load_initial_data

# --- Etapas de Inicialização ---

# 1. Inicializa o banco de dados SQL (cria o arquivo questions.db)
init_db() 

# 2. Inicializa o serviço (que inicia as conexões com Qdrant/Gemini)
question_service = QuestionService()

# 3. Carga Inicial de Dados (popula o Qdrant In-Memory e o SQLite)
load_initial_data(question_service, "data/initial_enem_data.json")

# --- Aplicação FastAPI ---

app = FastAPI(
    title="ENEM Question Recommendation & Generation Service",
    description="Backend para recuperar, gerar e gerenciar questões ENEM-style.",
    version="1.0.0"
)

# Endpoint para a recomendação/geração
@app.get(
    "/questions", 
    response_model=List[QuestionOut], 
    summary="Busca ou Gera Questões ENEM Relevantes"
)
async def get_questions(topic: str, amount: int):
    """
    Retorna uma lista de questões ENEM (máx. 15). 
    Prefere questões existentes, gera novas se necessário.
    """
    if not 1 <= amount <= 15:
        raise HTTPException(status_code=400, detail="O parâmetro 'amount' deve estar entre 1 e 15.")
    
    if not topic or len(topic.strip()) < 3:
        raise HTTPException(status_code=400, detail="O parâmetro 'topic' deve ser especificado.")
    
    try:
        questions = question_service.get_or_generate_questions(topic, amount)
        if not questions:
             raise HTTPException(status_code=503, detail="Não foi possível recuperar ou gerar questões.")
             
        return questions
    except Exception as e:
        print(f"ERRO CRÍTICO no GET /questions: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor ao processar a requisição.")


# Endpoint para upload manual
@app.post(
    "/questions", 
    status_code=201, 
    summary="Upload Manual de Nova Questão"
)
async def upload_question(question: QuestionIn):
    """
    Permite o upload manual de uma nova questão ENEM, que é automaticamente indexada.
    """
    try:
        new_question = question_service.persist_new_question(question)
        return {"message": "Questão enviada e indexada com sucesso.", "id": new_question.id}
    except Exception as e:
        print(f"ERRO CRÍTICO no POST /questions: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor ao processar o upload.")