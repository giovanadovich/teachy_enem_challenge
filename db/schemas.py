# db/schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional

class QuestionBase(BaseModel):
    """Base schema para dados de questão (usado para inserção)."""
    text: str = Field(..., description="O corpo da questão do ENEM.")
    area: str = Field(..., description="Área do conhecimento (ex: Ciências da Natureza).")
    alternatives: List[str] = Field(..., description="Lista de alternativas da questão.")
    correct_answer: str = Field(..., description="A alternativa correta.")

class QuestionModel(QuestionBase):
    """Schema completo para a questão (incluindo o ID do banco de dados)."""
    id: Optional[int] = Field(None, description="ID único da questão no banco de dados.")

    class Config:
        # Configuração para compatibilidade com SQLAlchemy ORM
        from_attributes = True 

class QuestionTopic(BaseModel):
    """Schema usado para retornar a busca de similaridade (RAG)."""
    id: int
    text: str
    area: str
    alternatives: List[str]
    correct_answer: str
    score: Optional[float] = Field(None, description="Pontuação de similaridade do Qdrant.")

class QuestionSearch(BaseModel):
    """Schema de entrada para a busca da API."""
    topic: str
    amount: int = 5