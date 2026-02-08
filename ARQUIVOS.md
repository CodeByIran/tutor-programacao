# Documentação Detalhada dos Arquivos

**Guia linha-por-linha de cada arquivo do projeto**

---

## Índice

1. [src/main.py](#srcmainpy)
2. [src/generator.py](#srcgeneratorpy)
3. [src/db.py](#srcdbpy)
4. [Dockerfile](#dockerfile)
5. [docker-compose.yml](#docker-composeyml)
6. [requirements.txt](#requirementstxt)
7. [.env](#env)

---

## src/main.py

**Responsabilidade:** Definir rotas HTTP e orquestrar requisições

**Tamanho:** ~120 linhas

### Imports

```python
from pathlib import Path
from fastapi import FastAPI, Query, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi import status
import json as _json

from src.db import SessionLocal, init_db, Questao
from src.generator import generate_questions
from fastapi.staticfiles import StaticFiles
from src.generator import generate_question
```

**O que cada import faz:**

| Import | Uso |
|--------|-----|
| `FastAPI` | Framework web (cria a app) |
| `Query` | Parâmetro de query string (`?param=value`) |
| `Body` | Parâmetro no corpo JSON (POST) |
| `JSONResponse` | Retornar JSON com status code |
| `FileResponse` | Servir arquivos estáticos (HTML) |
| `SessionLocal` | Conexão com banco de dados |
| `init_db` | Criar tabelas se não existirem |
| `Questao` | Modelo do banco (tabela) |
| `StaticFiles` | Servir pasta `/static` |

### Inicialização da Aplicação

```python
app = FastAPI()
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
```

**Explicação:**
- `app = FastAPI()` → Cria a aplicação web
- `Path(__file__).resolve().parent` → Pega o diretório onde este arquivo está (`/app/src/`)
- `.parent / "static"` → Navega para `/app/src/static/`
- `app.mount()` → Se a pasta existe, serve arquivos estáticos em `http://localhost:8000/static/`

### Rota GET / (Home)

```python
@app.get("/")
def index():
    f = STATIC_DIR / "index.html"
    if f.exists():
        return FileResponse(str(f))
    return {"message": "UI missing"}
```

**O que faz:**
- Quando cliente acessa `http://localhost:8000/`
- Tenta retornar o arquivo `src/static/index.html`
- Se não existir, retorna JSON com mensagem de erro

**Caso de uso:** UI web (frontend)

### Evento de Startup

```python
@app.on_event("startup")
def on_startup():
    try:
        init_db()
    except Exception:
        pass
```

**O que faz:**
- Quando a app inicia, executa `init_db()`
- Cria as tabelas do banco se não existirem
- Ignora erros (para não falhar o startup)

### Rota POST /questoes/gerar

```python
@app.post("/questoes/gerar")
def gerar_questoes(
    topic: str = Body(..., embed=True),
    quantidade: int = Body(5, embed=True),
    model: str = Body("llama", embed=True)
):
```

**Parâmetros:**
- `topic`: Tópico obrigatório (`...` = required)
- `quantidade`: Número de questões (padrão 5)
- `model`: Modelo a usar (padrão "llama")
- `embed=True`: Força JSON body ao invés de query string

**Exemplo de requisição:**
```bash
curl -X POST http://localhost:8000/questoes/gerar \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "variaveis",
    "quantidade": 3,
    "model": "llama"
  }'
```

### Corpo da Função gerar_questoes

```python
items = generate_questions(topic, quantidade, model=model)

for it in items:
    if isinstance(it, dict) and "error" in it:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Erro ao gerar questões", "details": items}
        )
```

**Explicação:**
- Chama `generate_questions()` que retorna lista de dicts
- Valida: se qualquer item tem chave "error", falha
- Retorna 400 Bad Request com detalhes do erro

```python
db = SessionLocal()
saved = []
try:
    for it in items:
        categoria = it.get("categoria") or ""
        topico = it.get("topico") or ""
        enunciado = it.get("pergunta") or it.get("enunciado") or ""
        alternativas = it.get("alternativas") or []
        alt_text = _json.dumps(alternativas, ensure_ascii=False)
        correta = it.get("resposta_correta") or it.get("correta") or ""
        feedback = it.get("explicacao") or it.get("feedback") or ""
        explicacoes_erradas = it.get("explicacoes_erradas") or []
        exp_err_text = _json.dumps(explicacoes_erradas, ensure_ascii=False)

        obj = Questao(
            categoria=categoria,
            topico=topico,
            enunciado=enunciado,
            alternativas=alt_text,
            correta=correta,
            feedback=feedback,
            explicacoes_erradas=exp_err_text
        )
        db.add(obj)
        db.flush()
        saved.append({"id": obj.id, "enunciado": enunciado, "correta": correta})
    db.commit()
```

**Explicação linha por linha:**

1. `db = SessionLocal()` → Abre conexão com banco
2. `saved = []` → Lista para rastrear questões salvas
3. `try:` → Inicia transação (tudo ou nada)
4. `for it in items:` → Para cada questão gerada
5. Extrai cada campo: `categoria`, `topico`, etc.
   - Usa `it.get("campo", default)` para evitar KeyError
   - Se campo não existe, usa default vazio
6. `alt_text = _json.dumps(alternativas, ensure_ascii=False)` → Converte lista para JSON string
   - `ensure_ascii=False` → Permite caracteres acentuados
7. Cria objeto `Questao` (modelo SQLAlchemy)
8. `db.add(obj)` → Marca para inserção
9. `db.flush()` → Executa INSERT para pegar `obj.id`
10. Adiciona à lista de rastreamento
11. `db.commit()` → Confirma transação

```python
except Exception as e:
    db.rollback()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": str(e)}
    )
finally:
    db.close()

return {"saved": saved}
```

**Explicação:**
- `except`: Se algo falhar, desfaz tudo (`rollback()`)
- `finally`: Fecha conexão sempre (mesmo com erro)
- `return`: Retorna JSON com IDs das questões salvas

### Rota GET /question

```python
@app.get("/question")
def question(topic: str = Query(...), model: str = Query("llama")):
```

**Parâmetros:**
- `topic`: Tópico obrigatório
- `model`: Modelo (padrão "llama")

**Exemplo:** `GET http://localhost:8000/question?topic=variaveis&model=llama`

```python
try:
    out = generate_question(topic, model=model)
    if isinstance(out, dict) and "error" in out:
        return JSONResponse(status_code=400, content=out)
    if isinstance(out, str):
        try:
            import json
            out = json.loads(out)
        except Exception:
            return {"raw_output": out}
```

**Explicação:**
- Chama `generate_question()` (gera 1 questão)
- Valida se tem erro
- Se retorno é string, tenta fazer parse JSON

```python
    db = SessionLocal()
    try:
        categoria = out.get("categoria") or ""
        topico = out.get("topico") or ""
        enunciado = out.get("pergunta") or out.get("enunciado") or ""
        alternativas = out.get("alternativas") or []
        alt_text = _json.dumps(alternativas, ensure_ascii=False)
        correta = out.get("resposta_correta") or out.get("correta") or ""
        feedback = out.get("explicacao") or out.get("feedback") or ""
        explicacoes_erradas = out.get("explicacoes_erradas") or []
        exp_err_text = _json.dumps(explicacoes_erradas, ensure_ascii=False)
        
        obj = Questao(
            categoria=categoria,
            topico=topico,
            enunciado=enunciado,
            alternativas=alt_text,
            correta=correta,
            feedback=feedback,
            explicacoes_erradas=exp_err_text
        )
        db.add(obj)
        db.commit()
        out["id"] = obj.id
    except Exception as e:
        db.rollback()
        out["db_warning"] = f"Questão gerada mas não salva: {str(e)}"
    finally:
        db.close()
    
    return out
```

**Explicação:**
- Mesma lógica que `gerar_questoes`, mas:
  - Salva apenas 1 questão
  - Adiciona `"id"` à resposta
  - Adiciona `"db_warning"` se falhar ao salvar (não interrompe a resposta)

### Rota GET /questoes

```python
@app.get("/questoes")
def listar_questoes(limit: int = Query(20, ge=1, le=200)):
```

**Parâmetros:**
- `limit`: Número de questões a retornar
- `ge=1`: Mínimo 1
- `le=200`: Máximo 200

**Exemplo:** `GET http://localhost:8000/questoes?limit=50`

```python
db = SessionLocal()
try:
    q = db.query(Questao).order_by(Questao.id.desc()).limit(limit).all()
    # SELECT * FROM questoes ORDER BY id DESC LIMIT 50;
    
    items = []
    for row in q:
        try:
            alts = _json.loads(row.alternativas) if row.alternativas else []
        except Exception:
            alts = row.alternativas
        try:
            exp_err = _json.loads(row.explicacoes_erradas) if row.explicacoes_erradas else []
        except Exception:
            exp_err = row.explicacoes_erradas or []
        items.append({
            "id": row.id,
            "categoria": row.categoria,
            "topico": row.topico,
            "enunciado": row.enunciado,
            "alternativas": alts,
            "correta": row.correta,
            "feedback": row.feedback,
            "explicacoes_erradas": exp_err,
        })
    return {"count": len(items), "items": items}
```

**Explicação:**
- Query: `SELECT * FROM questoes ORDER BY id DESC LIMIT 50`
- Para cada linha:
  - Parse JSON strings de volta para arrays
  - Monta dicionário
- Retorna contagem e lista

---

## src/generator.py

**Responsabilidade:** Lógica de geração de questões

**Tamanho:** ~180 linhas

### Variáveis Globais

```python
import os
import re
import json
from unittest import result
import requests
from typing import Any, Dict

API_KEY = (
    os.getenv("HF_TOKEN")
    or os.getenv("HF_API_KEY")
    or os.getenv("HUGGINGFACE_API_KEY")
)
```

**Explicação:**
- Tenta ler token do Hugging Face de 3 variáveis de ambiente
- Prioritários: `HF_TOKEN` > `HF_API_KEY` > `HUGGINGFACE_API_KEY`
- Permite flexibilidade em diferentes setups

```python
MODEL = os.getenv(
    "HUGGINGFACE_MODEL"
) or "meta-llama/Meta-Llama-3-8B-Instruct"
ENDPOINT = os.getenv("HUGGINGFACE_ENDPOINT")
```

**Explicação:**
- `MODEL`: Lê variável de ambiente ou usa Llama-3 como padrão
- `ENDPOINT`: Endpoint customizado (opcional)

```python
try:
    from huggingface_hub import InferenceClient
except Exception:
    InferenceClient = None
```

**Explicação:**
- Tenta importar cliente do HF
- Se falhar (pacote não instalado), define como None
- Evita crash da app se HF não estiver disponível

### AVAILABLE_MODELS

```python
AVAILABLE_MODELS = {
    "llama": "meta-llama/Meta-Llama-3-8B-Instruct",
    "llama4": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "depseeack": "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    "starcoder": "bigcode/starcoder-2-7b",
    "gpt": "openai/gpt-oss-safeguard-20b",
}
```

**Explicação:**
- Mapeia apelidos curtos para nomes completos de modelos
- Permite: `?model=llama` em vez de `?model=meta-llama/Meta-Llama-3-8B-Instruct`
- Facilita adicionar/remover modelos

### Função _find_json()

```python
def _find_json(s: str):
    """Extrai bloco JSON válido de uma string"""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, flags=re.DOTALL)
    if not m:
        i = s.find("{")
        j = s.rfind("}")
        if i == -1 or j == -1:
            return None
        candidate = s[i: j + 1]
    else:
        candidate = m.group(1)
    try:
        return json.loads(candidate)
    except Exception:
        return None
```

**O que faz:**
Tenta extrair JSON válido de uma string que pode conter lixo

**Estratégia:**
1. Procura padrão ` ```json {...} ``` `
2. Se não achar, procura primeiro `{` e último `}`
3. Tenta fazer parse JSON
4. Se falhar, retorna None

**Exemplos:**

```python
# Input 1: JSON puro
_find_json('{"categoria": "Geral"}')
# Output: {"categoria": "Geral"}

# Input 2: JSON em code block
_find_json('```json\n{"categoria": "Geral"}\n```')
# Output: {"categoria": "Geral"}

# Input 3: JSON com texto lixo
_find_json('Aqui está a questão: {"categoria": "Geral"} fin')
# Output: {"categoria": "Geral"}

# Input 4: JSON inválido
_find_json('isso não é json')
# Output: None
```

### Função generate_question()

```python
def generate_question(
    topic: str,
    fase: int = 2,
    categoria: str = None,
    model: str = "llama"
) -> Dict[str, Any]:
```

**Parâmetros:**
- `topic`: Obrigatório (ex: "variaveis")
- `fase`: 1 ou 2 (afeta número de alternativas)
  - Fase 1: 4 alternativas (A, B, C, D)
  - Fase 2: 5 alternativas (A, B, C, D, E)
- `categoria`: Opcional (ex: "logica")
- `model`: Qual modelo usar (padrão: "llama")

```python
if model not in AVAILABLE_MODELS:
    return {"error": f"Modelo '{model}' não disponível..."}

model_name = AVAILABLE_MODELS[model]
```

**Explicação:**
- Valida se modelo existe
- Converte apelido para nome completo

```python
try:
    fase = int(fase)
except Exception:
    fase = 2
if fase not in (1, 2):
    fase = 2
```

**Explicação:**
- Tenta converter fase para inteiro
- Se falhar ou não é 1/2, usa 2 como padrão

```python
letters = ["A", "B", "C", "D", "E"]
num_alts = 4 if fase == 1 else 5
```

**Explicação:**
- Define quantas alternativas baseado na fase

```python
_raw_categorias = {
    "Lógica/Algoritmo": ["logica", "lógica", "raciocinio", "raciocínio"],
    "Conceitual": ["conceitual", "teorica", "teórica", "teorico"],
    "Ética e Sociedade": ["etica", "ética", "sociedade"],
    "Aplicações e História": ["aplicacoes", "aplicações"],
}
CATEGORIAS = {k: cat for k, keys in _raw_categorias.items() for cat in keys}
cat_key = (categoria or "").strip().lower()
cat_desc = CATEGORIAS.get(cat_key, "Geral")
```

**Explicação:**
- Mapeia variações de escrita da categoria para forma canônica
- Exemplo: "lógica", "logica" → "Lógica/Algoritmo"
- Se não encontra, usa "Geral"

```python
prompt = f"""
Você é um gerador de questões da Olimpíada Nacional de Inteligência Artificial (ONIA)...
Tópico específico: {topic}
(Categoria: {cat_desc})

Siga esta metodologia para gerar UMA questão de múltipla escolha com {num_alts} alternativas...

Responda SOMENTE com um JSON válido no formato:
{{
  "categoria": string,
  "topico": string,
  "pergunta": string,
  "alternativas": [string,...],
  "resposta_correta": string (uma letra 'A'–'E'),
  "explicacao": string,
  "explicacoes_erradas": [string,...]
}}
"""
```

**Explicação:**
- Constrói prompt para o LLM
- Muito específico (prompt engineering)
- Define formato de resposta esperado

```python
raw = call_huggingface_api(prompt, num_alts, letters, model_name=model_name)
if isinstance(raw, dict):
    result = raw
else:
    result = _find_json(raw)
if result is None:
    return {"error": "Resposta inválida do modelo", "raw": raw}
```

**Explicação:**
- Chama Hugging Face
- Se retorno é dict, usa direto
- Se é string, tenta extrair JSON
- Se ainda é None, retorna erro

```python
if "explicacoes_erradas" not in result or not isinstance(result["explicacoes_erradas"], list):
    result["explicacoes_erradas"] = [
        "" if letters[i] == result.get("resposta_correta") else "Explicação breve do porquê está errada"
        for i in range(num_alts)
    ]

return result
```

**Explicação:**
- Se LLM não retornou `explicacoes_erradas`, cria automáticamente
- Gera uma para cada alternativa (vazia para correta, placeholder para erradas)

### Função format_question()

```python
def format_question(parsed: Dict[str, Any], num_alts: int, letters: list) -> Dict[str, Any]:
    alts = parsed.get("alternativas")
    if isinstance(alts, list) and len(alts) == num_alts:
        parsed["alternativas"] = [
            f"{letters[i]}) {a}" for i, a in enumerate(alts)
        ]
        parsed["resposta_correta"] = parsed.get("resposta_correta", "").strip().upper()
        return parsed
    raise ValueError("Formato de alternativas inválido no JSON retornado")
```

**O que faz:**
- Formata alternativas adicionando letras
- Converte resposta correta para maiúscula

**Exemplo:**

```python
# Input
{
    "alternativas": ["Python é dinamicamente tipado", "Java é dinamicamente tipado"],
    "resposta_correta": "a"
}

# Output
{
    "alternativas": ["A) Python é dinamicamente tipado", "B) Java é dinamicamente tipado"],
    "resposta_correta": "A"
}
```

### Função call_huggingface_api()

```python
def call_huggingface_api(prompt: str, num_alts: int = 5, letters=None, model_name: str = None) -> Dict[str, Any]:
    letters = letters or ["A", "B", "C", "D", "E"]
    model_to_use = model_name or MODEL

    if not InferenceClient or not API_KEY:
        raise RuntimeError("InferenceClient não disponível ou HF_API_KEY não configurada")

    client = InferenceClient(api_key=API_KEY)
    r = client.chat_completion(
        model=model_to_use,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )
    text = r.get("choices", [{}])[0].get("message", {}).get("content", "")
    parsed = _find_json(text)
    if parsed:
        return format_question(parsed, num_alts, letters)
    raise ValueError(f"Resposta inválida do modelo: {text}")
```

**Explicação:**

1. `client = InferenceClient(api_key=API_KEY)` → Autencia com HF

2. `client.chat_completion(...)` → Chama chat endpoint
   - `model`: qual modelo usar
   - `messages`: histórico de conversa (aqui só 1 mensagem)
   - `max_tokens`: limite de tokens na resposta (400 ≈ 300 palavras)

3. Extrai texto da resposta
   - `r["choices"][0]["message"]["content"]`

4. Tenta extrair JSON do texto

5. Se sucesso, formata e retorna

6. Se falha, levanta erro

### Função generate_questions()

```python
def generate_questions(
    topic: str,
    quantidade: int = 5,
    fase: int = 2,
    categoria: str = None,
    model: str = "llama"
) -> list:
    results = []
    for i in range(int(quantidade)):
        try:
            q = generate_question(topic, fase=fase, categoria=categoria, model=model)
            results.append(q)
        except Exception as e:
            results.append({"error": f"Erro ao gerar questão #{i+1}: {e}"})
    return results
```

**O que faz:**
- Chama `generate_question()` múltiplas vezes
- Retorna lista com questões E erros (não para no primeiro erro)

**Exemplo:**

```python
generate_questions("variaveis", quantidade=3)

# Output
[
    {"categoria": "Geral", "topico": "variaveis", ...},
    {"categoria": "Geral", "topico": "variaveis", ...},
    {"error": "Erro ao gerar questão #3: Timeout"}
]
```

---

## src/db.py

**Responsabilidade:** Conexão e modelos de banco de dados

**Tamanho:** ~40 linhas

### Imports e Setup

```python
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
```

**Explicação:**
- Carrega variáveis de ambiente do `.env`
- Lê `DATABASE_URL`: string de conexão PostgreSQL

```python
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
```

**Explicação:**
- `engine`: Piscina de conexões com banco
- `SessionLocal`: Factory para criar sessões (conexões)
- `Base`: Classe base para modelos ORM

### Modelo Questao

```python
class Questao(Base):
    __tablename__ = "questoes"

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(String, nullable=True)
    topico = Column(String, nullable=True)
    enunciado = Column(Text, nullable=False)
    alternativas = Column(Text, nullable=False)
    correta = Column(String, nullable=False)
    feedback = Column(Text, nullable=True)
    explicacoes_erradas = Column(Text, nullable=True)
```

**Explicação:**
- Define estrutura da tabela `questoes`
- `Column(Integer, primary_key=True)` → ID auto-incremento
- `nullable=True` → Campo opcional
- `Text` → Texto longo (> 255 caracteres)

**Equivalente em SQL:**

```sql
CREATE TABLE questoes (
    id SERIAL PRIMARY KEY,
    categoria VARCHAR,
    topico VARCHAR,
    enunciado TEXT NOT NULL,
    alternativas TEXT NOT NULL,
    correta VARCHAR NOT NULL,
    feedback TEXT,
    explicacoes_erradas TEXT
);
```

### Função init_db()

```python
def init_db():
    Base.metadata.create_all(bind=engine)
```

**O que faz:**
- Cria todas as tabelas definidas em modelos Base
- Se tabela já existe, não faz nada
- Chamado automaticamente no startup da FastAPI

---

## Dockerfile

**Responsabilidade:** Definir imagem Docker da aplicação

**Tamanho:** ~20 linhas

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Linha por linha:**

1. `FROM python:3.11-slim` → Imagem base (Python 3.11, versão reduzida)
2. `WORKDIR /app` → Define pasta de trabalho dentro container
3. `RUN apt-get update && apt-get upgrade -y` → Atualiza repositórios
4. `apt-get install -y --no-install-recommends build-essential` → Instala compilador C (necessário para some packages)
5. `rm -rf /var/lib/apt/lists/*` → Remove cache de apt (reduz tamanho)
6. `COPY requirements.txt .` → Copia arquivo de dependências para `/app/`
7. `RUN pip install --no-cache-dir -r requirements.txt` → Instala dependências Python
8. `COPY ./src ./src` → Copia código para `/app/src/`
9. `EXPOSE 8000` → Documenta que app usa porta 8000 (informativo)
10. `CMD [...]` → Comando para rodar quando container inicia

---

## docker-compose.yml

**Responsabilidade:** Orquestrar múltiplos containers

**Tamanho:** ~50 linhas

```yaml
services:
  api:
    build: .
    container_name: llama_api
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./src:/app/src
    depends_on:
      - db
```

**Explicação:**

- `api`: Nome do serviço
- `build: .` → Build do Dockerfile na pasta atual
- `container_name` → Nome do container (para referência)
- `ports: - "8000:8000"` → Mapeia porta: `host:container`
- `env_file: - .env` → Carrega variáveis do `.env`
- `volumes: - ./src:/app/src` → Sincroniza pasta (hot reload)
- `depends_on: - db` → Espera banco iniciar antes

```yaml
  db:
    image: postgres:15
    container_name: llama_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: llama
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
```

**Explicação:**

- `image: postgres:15` → Usa imagem pronta (não build)
- `environment` → Variáveis de ambiente (credenciais)
- `volumes: - pgdata:/var/lib/postgresql/data` → Persiste dados entre restarts

```yaml
  pgadmin:
    image: dpage/pgadmin4
    container_name: llama_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@admin.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - db

volumes:
  pgdata:
```

**Explicação:**

- `pgadmin` → Interface gráfica para PostgreSQL
- Acessível em `http://localhost:5050`
- `volumes: pgdata:` → Define volume nomeado (persistente)

---

## requirements.txt

**Responsabilidade:** Listar dependências Python

```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
huggingface-hub==0.19.3
python-dotenv==1.0.0
requests==2.31.0
```

**O que cada uma faz:**

| Pacote | Versão | Função |
|--------|--------|--------|
| `fastapi` | 0.104.1 | Framework web |
| `uvicorn` | 0.24.0 | Servidor ASGI (roda FastAPI) |
| `sqlalchemy` | 2.0.23 | ORM para banco |
| `psycopg2-binary` | 2.9.9 | Driver PostgreSQL |
| `huggingface-hub` | 0.19.3 | Cliente Hugging Face |
| `python-dotenv` | 1.0.0 | Carrega variáveis .env |
| `requests` | 2.31.0 | HTTP client (fallback) |

**Como instalar:**
```bash
pip install -r requirements.txt
```

---

## .env

**Responsabilidade:** Variáveis de configuração sensíveis

```env
HF_API_KEY=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
HUGGINGFACE_MODEL=meta-llama/Meta-Llama-3-8B-Instruct
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/llama
HUGGINGFACE_MAX_TOKENS=2048
```

**Explicação:**

| Variável | Valor Exemplo | Função |
|----------|---------------|--------|
| `HF_API_KEY` | `hf_XNtzx...` | Token de autenticação Hugging Face |
| `HUGGINGFACE_MODEL` | `meta-llama/...` | Modelo padrão a usar |
| `DATABASE_URL` | `postgresql+...` | String conexão PostgreSQL |
| `HUGGINGFACE_MAX_TOKENS` | `2048` | Limite de tokens por geração |

**Formato DATABASE_URL:**
```
postgresql+psycopg2://usuario:senha@host:porta/banco
postgresql+psycopg2://postgres:postgres@db:5432/llama
                     ^^^^^^^^ ^^^^^^^^  ^^    ^^^^  ^^^^^
                     usuario  senha     host  porta banco
```

**Nota:** Este arquivo NÃO deve ser commitado (está no `.gitignore`)

---

**Próxima Leitura:** [DEPLOY.md](DEPLOY.md) - Como rodar em outro PC ou nuvem
