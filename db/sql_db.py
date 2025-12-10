# db/sql_db.py
from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.sqlite import JSON

# Configuração do DB (usando SQLite local para facilidade)
DATABASE_URL = "sqlite:///./questions.db"
# Conexão: connect_args={"check_same_thread": False} é necessário para SQLite/FastAPI
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class QuestionModel(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, index=True) 
    statement = Column(Text, nullable=False)
    alternatives = Column(JSON, nullable=False) 
    correct_answer = Column(String(1), nullable=False)
    topic = Column(String, index=True)
    source = Column(String)

def init_db():
    """Cria as tabelas no banco de dados se elas não existirem."""
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized (SQLite).")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()