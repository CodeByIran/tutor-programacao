# Tutor Programacao — Run instructions

This repository contains a FastAPI app that generates quiz questions with an LLM and stores them in PostgreSQL.

**Quick start (recommended: Docker Compose)**

1. Clone the repo and change directory:

```bash
git clone <repo-url>
cd tutor-programacao
```

2. Create `.env` (example):

```env
# Hugging Face
HF_TOKEN=your_hf_token_here
HUGGINGFACE_MODEL=some-model-name
# Database (when using Docker Compose the db service is used)
DATABASE_URL=postgresql://postgres:postgres@db:5432/llama
```

3. Build and run (Docker Compose):

```bash
docker compose up -d --build
```

- API: http://localhost:8000
- PgAdmin: http://localhost:5050 (user: `admin@admin.com`, pass: `admin`)


Running without Docker

1. Create and activate a virtualenv, then install dependencies:

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Ensure a Postgres instance is available and `DATABASE_URL` points to it.

3. Run the app:

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```


API endpoints

- GET `/question?topic=...&model=llama` — generate a single question (useful for quick tests)
- POST `/questoes/gerar` — generate and save questions
	- Request JSON: `{ "topic": "variaveis", "quantidade": 5, "model": "llama" }`
	- Returns saved record ids on success
- GET `/questoes?limit=20` — list last saved questions (default `limit=20`, max 200)

Example curl to generate and save 5 questions:

```bash
curl -X POST http://localhost:8000/questoes/gerar \
	-H "Content-Type: application/json" \
	-d '{"topic":"variaveis","quantidade":5,"model":"llama"}'
```

List saved questions:

```bash
curl 'http://localhost:8000/questoes?limit=20'
```

Inspect DB (with Docker Compose)

```bash
docker compose exec db psql -U postgres -d llama -c "SELECT id,enunciado,alternativas,correta FROM questoes ORDER BY id DESC LIMIT 20;"
```

Or open PgAdmin at http://localhost:5050 and browse database `llama` → public → Tables → `questoes`.

Notes and troubleshooting

- The LLM model and token are configured via environment variables. Replace `HUGGINGFACE_MODEL` and `HF_TOKEN` in `.env` with a model/token that works for you.
- If a model is not a chat model, the code tries fallback paths, but some models may return non-JSON output — in that case the response will include `raw` text to help debugging.
- To view API logs when running with Docker Compose:

```bash
docker compose logs --tail=200 api
```

Security

- Keep tokens out of source control. Add `.env` to `.gitignore` (already expected).


If you want, I can also:
- add a GET `/questoes/{id}` endpoint to fetch a single question;
- add a small admin page under `/static` to browse saved questions;
- produce a minimal Postman collection with the example requests.

Choose one and I implement it next.

