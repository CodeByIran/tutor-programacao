from pathlib import Path
from fastapi import FastAPI, Query, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi import status
import json as _json

from src.db import SessionLocal, init_db, Questao
from src.generator import generate_questions
from fastapi.staticfiles import StaticFiles
from src.generator import generate_question

app = FastAPI()
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")

def index():
    f = STATIC_DIR / "index.html"
    if f.exists():
        return FileResponse(str(f))
    return {"message": "UI missing"}


@app.on_event("startup")
def on_startup():
    # Cria tabelas se ainda não existirem
    try:
        init_db()
    except Exception:
        # não falhar o startup por problemas de DB; deixamos erros aparecerem nas rotas
        pass


@app.post("/questoes/gerar")
def gerar_questoes(topic: str = Body(..., embed=True), quantidade: int = Body(5, embed=True), model: str = Body("llama", embed=True)):
    """Gera `quantidade` questões via LLM, salva no banco e retorna a lista criada.

    Request body expected (JSON): {"topic": "...", "quantidade": 5, "model": "llama"}
    """
    # Gerar questões (não testaremos o modelo aqui — usuário substitui o modelo quando quiser)
    items = generate_questions(topic, quantidade, model=model)

    # Se algum item for erro, devolve 400 com detalhes
    for it in items:
        if isinstance(it, dict) and "error" in it:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Erro ao gerar questões", "details": items})

    db = SessionLocal()
    saved = []
    try:
        for it in items:
            enunciado = it.get("pergunta") or it.get("enunciado") or ""
            alternativas = it.get("alternativas") or []
            # garante string JSON
            alt_text = _json.dumps(alternativas, ensure_ascii=False)
            correta = it.get("resposta_correta") or it.get("correta") or ""
            feedback = it.get("explicacao") or it.get("feedback") or ""

            obj = Questao(enunciado=enunciado, alternativas=alt_text, correta=correta, feedback=feedback)
            db.add(obj)
            db.flush()
            saved.append({"id": obj.id, "enunciado": enunciado, "correta": correta})
        db.commit()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": str(e)})
    finally:
        db.close()

    return {"saved": saved}


@app.get("/question")
def question(topic: str = Query(...), model: str = Query("llama")):
    try:
        out = generate_question(topic, model=model)
        if isinstance(out, dict) and "error" in out:
            return JSONResponse(status_code=400, content=out)
        if isinstance(out, str):
            try:
                import json

                return json.loads(out)
            except Exception:
                return {"raw_output": out}
        return out
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/questoes")
def listar_questoes(limit: int = Query(20, ge=1, le=200)):
    """Retorna as últimas `limit` questões salvas na tabela `questoes`.

    - `limit`: número máximo de registros a retornar (default 20, máximo 200).
    """
    db = SessionLocal()
    try:
        q = db.query(Questao).order_by(Questao.id.desc()).limit(limit).all()
        items = []
        for row in q:
            try:
                alts = _json.loads(row.alternativas) if row.alternativas else []
            except Exception:
                alts = row.alternativas
            items.append({
                "id": row.id,
                "enunciado": row.enunciado,
                "alternativas": alts,
                "correta": row.correta,
                "feedback": row.feedback,
            })
        return {"count": len(items), "items": items}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()
