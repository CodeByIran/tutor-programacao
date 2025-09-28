from pathlib import Path
import logging
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from src.generator import generate_question

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deepseek")

app = FastAPI()

# Serve static UI (index.html)
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def read_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "UI not found. Place static files in src/static."}


@app.get("/question")
def get_question(topic: str = Query(..., description="Tema da questão")):
    logger.info("/question called, topic=%s", topic)
    try:
        result = generate_question(topic)
        # structured error from generator
        if isinstance(result, dict) and "error" in result:
            logger.info("/question returning error response: %s", result)
            return JSONResponse(status_code=400, content=result)

        # already structured payload
        if isinstance(result, dict):
            return result

        # try to parse stringified JSON
        if isinstance(result, str):
            try:
                import json

                parsed = json.loads(result)
                return parsed
            except Exception:
                return {"raw_output": result}

        # fallback
        logger.info("/question returning raw_output (type=%s)", type(result))
        return {"raw_output": str(result)}

    except Exception as e:
        logger.exception("Error in /question")
        return JSONResponse(status_code=500, content={"error": str(e)})
