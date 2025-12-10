# api/models.py
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# --- Modelos de Entrada/Saída da API ---

class QuestionIn(BaseModel):
    """Modelo para upload manual de novas questões (POST /questions)"""
    statement: str = Field(..., description="O enunciado completo da questão no estilo ENEM.")
    alternatives: List[str] = Field(..., description="Lista de 5 strings (A, B, C, D, E) representando as alternativas.")
    correct_answer: Literal["A", "B", "C", "D", "E"] = Field(..., description="A letra correspondente à alternativa correta.")
    topic: Optional[str] = Field(None, description="Tópico principal da questão para indexação inicial.")

class QuestionOut(BaseModel):
    """Modelo para as questões retornadas pela API (GET /questions)"""
    id: str = Field(..., description="ID único da questão.")
    statement: str
    alternatives: List[str]
    correct_answer: Literal["A", "B", "C", "D", "E"]

# --- Modelo de Dados Interno (Persistência) ---

class QuestionInternal(QuestionIn):
    """Modelo interno que adiciona campos de persistência e indexação."""
    id: Optional[str] = Field(None, description="ID único (gerado na persistência).")
    source: Literal["GENERATED", "UPLOADED", "INITIAL_LOAD"] = Field("GENERATED", description="Origem da questão.")
    embedding: Optional[List[float]] = None