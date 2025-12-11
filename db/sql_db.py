# db/sql_db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ----------------------------------------------------
# 1. CONFIGURAÇÃO DO ENGINE
# ----------------------------------------------------

# Defina o Engine (o arquivo .db)
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(
    # check_same_thread=False é necessário apenas para SQLite, 
    # permitindo múltiplos threads (FastAPI) acessarem a mesma conexão.
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# ----------------------------------------------------
# 2. BASE E MAPEAMENTO
# ----------------------------------------------------

# Defina a Base para os modelos
Base = declarative_base()
from . import schemas

# ----------------------------------------------------
# 3. CRIAÇÃO DE TABELAS E SESSÃO
# ----------------------------------------------------


# Defina o SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)