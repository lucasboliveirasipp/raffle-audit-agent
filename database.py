"""
Configuração do banco de dados usando SQLAlchemy
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker
from typing import Optional

# Obter caminho absoluto para o banco de dados
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "CG.db")

# Criar engine SQLite com caminho absoluto
engine = create_engine(f'sqlite:///{db_path}', echo=False)

# Base para modelos
class Base(DeclarativeBase):
    pass

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class CondicoesGerais(Base):
    """
    Modelo para a tabela de Condições Gerais
    Reflete a estrutura real da tabela existente (sem coluna id)
    """
    __tablename__ = "condicoes_gerais"
    
    plano_susep = Column(String, primary_key=True, index=True, nullable=False)
    texto_completo = Column(Text, nullable=False)
    
    def __repr__(self):
        return f"<CondicoesGerais(plano_susep='{self.plano_susep}')>"


def get_db_session():
    """
    Cria e retorna uma sessão do banco de dados
    """
    return SessionLocal()


def init_db():
    """
    Inicializa o banco de dados (cria tabelas se não existirem)
    """
    Base.metadata.create_all(bind=engine)


def close_db_session(session):
    """
    Fecha uma sessão do banco de dados
    """
    if session:
        session.close()


def get_db_path() -> str:
    """
    Retorna o caminho absoluto do banco de dados
    """
    return db_path