from fastapi import FastAPI
from src.generator import generate_question

app = FastAPI()

@app.get("/")
def root():
    return {"msg": "DeepSeek Question Generator API"}

@app.get("/question")
def get_question(topic: str = "Inteligência Artificial"):
    question = generate_question(topic)
    return {"question": question}
