# db/schemas.py

# Importações para Schemas Pydantic
from pydantic import BaseModel, Field
from typing import List, Optional

# ⬇️ Importações para o Modelo SQLAlchemy
from sqlalchemy import Column, Integer, String, JSON
# ⬇️ CHAVE: Importar Base do seu arquivo de configuração
from .sql_db import Base 

# ----------------------------------------------------
# 1. MODELO SQLAlchemy (DEFINE A TABELA)
# ----------------------------------------------------

class QuestionModel(Base):
    """Modelo ORM do SQLAlchemy que representa a tabela 'questions' no banco de dados."""
    
    # Define o nome da tabela
    __tablename__ = "questions"

    # Define as Colunas da Tabela
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String) # O texto da questão (statement)
    area = Column(String) # A área/tópico
    # Usamos JSON/String para armazenar a lista de alternativas
    alternatives = Column(JSON) 
    correct_answer = Column(String) 

# ----------------------------------------------------
# 2. SCHEMAS Pydantic (DEFINE FORMATOS DE DADOS DA API)
# ----------------------------------------------------

class QuestionBase(BaseModel):
    """Base schema para dados de questão (usado para inserção)."""
    # ⬇️ CHAVE: Usar 'statement' e 'topic' aqui, conforme seu JSON
    statement: str = Field(..., description="O corpo da questão do ENEM (chamado 'statement' no JSON).")
    topic: str = Field(..., description="Área do conhecimento (chamado 'topic' no JSON).")
    alternatives: List[str] = Field(..., description="Lista de alternativas da questão.")
    correct_answer: str = Field(..., description="A alternativa correta.")
    
    class Config:
        from_attributes = True # Compatibilidade com ORM (QuestionModel acima)

class QuestionInsert(QuestionBase):
    """Schema para a inserção de novos dados (não precisa de ID)."""
    pass

class QuestionTopic(BaseModel):
    """Schema usado para retornar a busca de similaridade (RAG)."""
    id: int
    text: str # Retornado como 'text' para o usuário
    area: str # Retornado como 'area' para o usuário
    alternatives: List[str]
    correct_answer: str
    score: Optional[float] = Field(None, description="Pontuação de similaridade do Qdrant.")
    
    class Config:
        from_attributes = True

class QuestionSearch(BaseModel):
    """Schema de entrada para a busca da API."""
    topic: str
    amount: int = 5