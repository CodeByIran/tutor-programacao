from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, FileResponse
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


@app.get("/question")
def question(topic: str = Query(...)):
    try:
        out = generate_question(topic)
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
