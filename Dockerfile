FROM python:3.11-slim-bookworm

# Always update to the latest patch-level fixes for 3.11 Bookworm.
# Rebuild the image to pick up security patches: `docker compose build --no-cache` or
# `docker compose up -d --build`.

RUN apt-get update && apt-get upgrade -y && apt-get dist-upgrade -y && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get upgrade -y && apt-get clean

# definir diretório de trabalho
WORKDIR /app

# instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copiar código
COPY ./src ./src

# expor porta
EXPOSE 8000

# rodar o FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
