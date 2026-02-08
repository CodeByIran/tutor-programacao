# Guia de Deployment - Tutor Programação

## Rodando Localmente em Outro PC

### Pré-requisitos
- Git (opcional, para clonar o repositório)
- Docker Desktop ou Docker + Docker Compose instalados
- 4GB de RAM mínimo

### Passos

#### 1. Copiar/Clonar o Projeto
```bash
# Se estiver em um repositório Git
git clone <seu-repo-url>
cd tutor-programacao

# Ou copie a pasta manualmente
```

#### 2. Criar arquivo `.env`
Na raiz do projeto, crie um arquivo `.env` com:

```env
HF_API_KEY=sua_chave_huggingface_aqui
HUGGINGFACE_MODEL=meta-llama/Meta-Llama-3-8B-Instruct
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/llama
HUGGINGFACE_MAX_TOKENS=2048
```

**Importante:** Substitua `sua_chave_huggingface_aqui` pela sua chave real do Hugging Face.

#### 3. Instalar Docker
Se não tiver Docker instalado:
- **Windows/Mac:** Download [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Linux:** 
  ```bash
  sudo apt-get update
  sudo apt-get install docker.io docker-compose
  sudo usermod -aG docker $USER
  ```

#### 4. Rodar a Aplicação
```bash
cd tutor-programacao
docker compose up --build
```

Aguarde até aparecer:
```
llama_api      | Uvicorn running on http://0.0.0.0:8000
```

#### 5. Acessar a Aplicação
- **API:** http://localhost:8000
- **Documentação:** http://localhost:8000/docs
- **PgAdmin:** http://localhost:5050
  - Email: `admin@admin.com`
  - Senha: `admin`

---

## Endpoints Disponíveis

### Gerar uma questão
```bash
curl "http://localhost:8000/question?topic=variaveis"
```

### Gerar e salvar múltiplas questões
```bash
curl -X POST http://localhost:8000/questoes/gerar \
  -H "Content-Type: application/json" \
  -d '{"topic":"variaveis","quantidade":5,"model":"llama"}'
```

### Listar questões salvas
```bash
curl "http://localhost:8000/questoes?limit=20"
```

### Parametros disponíveis
- `topic`: Tópico da questão (ex: variaveis, loops, funcoes)
- `model`: Modelo a usar (llama, llama4, starcoder, depseeack, gpt)
- `quantidade`: Número de questões a gerar
- `fase`: 1 ou 2 (afeta número de alternativas)
- `categoria`: Categoria da questão

---

## Verificar Dados no Banco

### Via Terminal (PostgreSQL)
```bash
# Ver últimas 5 questões
docker compose exec db psql -U postgres -d llama -c "SELECT id, categoria, topico, correta FROM questoes ORDER BY id DESC LIMIT 5;"

# Contar total
docker compose exec db psql -U postgres -d llama -c "SELECT COUNT(*) FROM questoes;"

# Ver questão específica
docker compose exec db psql -U postgres -d llama -c "SELECT * FROM questoes WHERE id=1;"
```

### Via API
```bash
curl "http://localhost:8000/questoes?limit=50"
```

### Via PgAdmin (UI gráfica)
1. Acesse http://localhost:5050
2. Login: `admin@admin.com` / `admin`
3. Adicione servidor:
   - Name: `llama_db`
   - Host: `db`
   - Port: `5432`
   - Username: `postgres`
   - Password: `postgres`
4. Navegue até: Servers → llama_db → Databases → llama → Tables → questoes

---

## Estrutura do Banco de Dados

Tabela `questoes`:
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | ID único (PK) |
| categoria | String | Categoria da questão (ex: Geral) |
| topico | String | Tópico (ex: variaveis) |
| enunciado | Text | Pergunta completa |
| alternativas | Text | JSON com 4-5 alternativas |
| correta | String | Letra da resposta correta (A-E) |
| feedback | Text | Explicação da resposta |
| explicacoes_erradas | Text | JSON com explicações das alternativas incorretas |

---

## Deploy em Nuvem

### Opção 1: Render (Recomendado - Gratuito)
1. Push o projeto para GitHub
2. Crie conta em [Render](https://render.com)
3. Crie novo Web Service:
   - Conecte seu repositório
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn src.main:app --host 0.0.0.0`
4. Adicione variáveis de ambiente no Render:
   - `HF_API_KEY`
   - `HUGGINGFACE_MODEL`
   - `DATABASE_URL` (use PostgreSQL do Render)

### Opção 2: AWS EC2
1. Crie instância EC2 (t2.micro)
2. SSH para a instância
3. Instale Docker
4. Clone o repositório
5. Crie `.env` com variáveis
6. `docker compose up -d`

### Opção 3: Docker Hub + Heroku (Descontinuado)
- Use plataformas como Railway ou Fly.io como alternativa

---

## Troubleshooting

### Erro: "410 Client Error: Gone"
- O modelo não está disponível no endpoint
- Mude `HUGGINGFACE_MODEL` para: `meta-llama/Meta-Llama-3-8B-Instruct`

### Erro: "Database connection refused"
```bash
# Reinicie o container do banco
docker compose restart db

# Ou force rebuild
docker compose down
docker compose up --build
```

### Erro: "Column does not exist"
```bash
# Delete a tabela antiga e recrie
docker compose exec db psql -U postgres -d llama -c "DROP TABLE IF EXISTS questoes CASCADE;"
docker compose restart api
```

### Porta 8000 já em uso
```bash
# Mude a porta no docker-compose.yml
# Antes: ports: - "8000:8000"
# Depois: ports: - "8001:8000"
```

---

## Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `HF_API_KEY` | Token do Hugging Face | `hf_XXXXXXX...` |
| `HUGGINGFACE_MODEL` | Modelo padrão | `meta-llama/Meta-Llama-3-8B-Instruct` |
| `DATABASE_URL` | String de conexão PostgreSQL | `postgresql://user:pass@host/db` |
| `HUGGINGFACE_MAX_TOKENS` | Limite de tokens | `2048` |

---

## Arquitetura

```
┌─────────────────────────────────────────┐
│        Cliente (Browser)                 │
│     http://localhost:8000                │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│    FastAPI (API)                        │
│    - /question                          │
│    - /questoes                          │
│    - /questoes/gerar                    │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
┌───────▼──────┐  ┌──────▼─────────┐
│ Hugging Face │  │  PostgreSQL DB │
│  (LLM Model) │  │  (Armazena Q)  │
└──────────────┘  └────────────────┘
```

---

## Dúvidas Frequentes

**P: Preciso de internet?**
A: Sim, para chamar o modelo do Hugging Face. O banco é local.

**P: Posso usar outro modelo?**
A: Sim, altere `HUGGINGFACE_MODEL` no `.env` para outro modelo suportado.

**P: Quanto tempo leva para gerar uma questão?**
A: ~5-30 segundos, dependendo do modelo e conexão.

**P: Posso resetar o banco?**
A: Sim, delete a pasta `pgdata` e recrie: `docker compose down && docker compose up --build`

---

## Suporte

Para problemas, verifique:
1. Logs: `docker compose logs -f api`
2. Variáveis de ambiente: `docker compose config`
3. Conexão do DB: `docker compose exec db psql -U postgres -l`
