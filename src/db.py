from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    enunciado = Column(Text, nullable=False)
    alternativas = Column(Text, nullable=False)
    correta = Column(String, nullable=False)
    feedback = Column(Text, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)
