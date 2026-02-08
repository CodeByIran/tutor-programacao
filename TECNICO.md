# Documentação Técnica Completa - Tutor Programação

**Projeto:** Sistema de Geração de Questões de Programação com IA
**Desenvolvedor Anterior:** [Seu Nome]
**Data de Criação:** Fevereiro 2026
**Status:** Em Produção

---

## Índice

1. [Visão Geral do Projeto](#visão-geral-do-projeto)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Arquitetura Geral](#arquitetura-geral)
4. [Fluxo de Dados](#fluxo-de-dados)
5. [Estrutura do Banco de Dados](#estrutura-do-banco-de-dados)
6. [Decisões de Design](#decisões-de-design)
7. [Como Funciona Passo a Passo](#como-funciona-passo-a-passo)
8. [Possíveis Evoluções](#possíveis-evoluções)
9. [Problemas Conhecidos e Soluções](#problemas-conhecidos-e-soluções)

---

## Visão Geral do Projeto

### O que o Projeto Faz?
Este é um **gerador automático de questões de programação** usando IA (Large Language Models). A aplicação:

1. **Recebe uma solicitação** com um tópico (ex: "variáveis", "loops", "funções")
2. **Consulta um modelo de IA** (Hugging Face) para gerar uma questão
3. **Formata a questão** em um padrão estruturado (JSON)
4. **Salva no banco de dados** (PostgreSQL)
5. **Retorna a questão** para o cliente

### Público-Alvo
- Estudantes de programação
- Plataformas de educação
- Sistemas de avaliação automática

### Objetivo Principal
Gerar questões de múltipla escolha em estilo ONIA (Olimpíada Nacional de Inteligência Artificial) de forma rápida e escalável.

---

## Stack Tecnológico

### Backend
- **Framework:** FastAPI (Python)
- **Servidor:** Uvicorn
- **Versão Python:** 3.11

### IA/LLM
- **Provider:** Hugging Face Inference API
- **Modelo Padrão:** `meta-llama/Meta-Llama-3-8B-Instruct`
- **Alternativas:** Mistral, DeepSeek, StarCoder, GPT

### Banco de Dados
- **SGBD:** PostgreSQL 15
- **ORM:** SQLAlchemy
- **Gerenciador de Sessão:** SQLAlchemy ORM

### DevOps/Containerização
- **Docker:** Containerização da aplicação
- **Docker Compose:** Orquestração multi-container

### Dependências Python Principais
```
fastapi==0.104.1           # Framework web
uvicorn==0.24.0            # Servidor ASGI
sqlalchemy==2.0.23         # ORM para banco
psycopg2-binary==2.9.9     # Driver PostgreSQL
huggingface-hub==0.19.3    # Cliente Hugging Face
python-dotenv==1.0.0       # Gerenciar variáveis de ambiente
```

---

## Arquitetura Geral

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTE (HTTP)                            │
│              Browser / Postman / Aplicação Externa              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    HTTP Request/Response
                             │
        ┌────────────────────▼────────────────────┐
        │        FastAPI Application              │
        │    (src/main.py)                        │
        │                                         │
        │  ├─ GET  /question                      │
        │  ├─ POST /questoes/gerar                │
        │  ├─ GET  /questoes                      │
        │  └─ GET  /                              │
        └────────────────────┬────────────────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌──────────────┐  ┌─────────────┐  ┌──────────────┐
    │  Generator   │  │  Database   │  │ Static Files │
    │ (src/        │  │  (src/db.py)│  │ (src/static/)│
    │ generator.py)│  │             │  │              │
    └──────┬───────┘  └─────────────┘  └──────────────┘
           │
           │ API Call (REST)
           ▼
    ┌─────────────────────────────────────────┐
    │   Hugging Face Inference API            │
    │                                         │
    │  - chat_completion()                    │
    │  - Modelo: Meta-Llama-3-8B-Instruct    │
    └─────────────────────────────────────────┘
```

### Camadas da Aplicação

```
┌─────────────────────────────────────────┐
│     CAMADA DE APRESENTAÇÃO              │
│  - Rotas HTTP (FastAPI)                 │
│  - Validação de input                   │
│  - Formatação de resposta               │
│     (src/main.py)                       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│     CAMADA DE LÓGICA DE NEGÓCIO        │
│  - Geração de prompt                    │
│  - Chamada ao LLM                       │
│  - Parse de JSON                        │
│  - Validação de questão                 │
│     (src/generator.py)                  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│     CAMADA DE PERSISTÊNCIA              │
│  - Models SQLAlchemy                    │
│  - Operações CRUD                       │
│  - Pool de conexões                     │
│     (src/db.py)                         │
└──────────────┬──────────────────────────┘
               │
               ▼
        PostgreSQL Database
```

---

## Fluxo de Dados

### Fluxo 1: Gerar Questão Única (GET /question)

```
1. Cliente HTTP
   └─> GET /question?topic=variaveis&model=llama
   
2. FastAPI Route (main.py)
   └─> question(topic, model)
   
3. Generator (generator.py)
   └─> generate_question(topic, model="llama")
       ├─ Valida se modelo existe em AVAILABLE_MODELS
       ├─ Cria prompt estruturado
       └─> call_huggingface_api(prompt, model)
   
4. Hugging Face API
   └─> client.chat_completion(
       model="meta-llama/Meta-Llama-3-8B-Instruct",
       messages=[{"role": "user", "content": prompt}]
   )
   
5. Resposta do LLM
   └─> {"choices": [{"message": {"content": "{JSON questão}"}}]}
   
6. Parse e Formatação (generator.py)
   ├─> _find_json() → extrai JSON válido
   ├─> format_question() → adiciona letras (A, B, C, D, E)
   └─> Retorna Dict com questão formatada
   
7. Salvar no Banco (main.py)
   ├─> Cria objeto Questao
   ├─> db.add(obj) + db.commit()
   └─> Retorna com ID da questão
   
8. Resposta ao Cliente
   └─> JSON com questão + id
```

### Fluxo 2: Gerar Múltiplas Questões (POST /questoes/gerar)

```
1. Cliente HTTP
   └─> POST /questoes/gerar
       Body: {"topic": "variaveis", "quantidade": 5, "model": "llama"}
   
2. FastAPI Route (main.py)
   └─> gerar_questoes(topic, quantidade, model)
   
3. Generator (generator.py)
   └─> generate_questions(topic, quantidade=5, model)
       └─> Loop 5x: generate_question()
           └─> Mesmo fluxo da questão única
   
4. Validação de Erros
   ├─> Se alguma questão falhou, retorna 400 com detalhes
   └─> Else: continua
   
5. Salvar em Lote no Banco (main.py)
   ├─> Abre transação
   ├─> Para cada questão:
   │   ├─> Cria objeto Questao
   │   ├─> db.add(obj)
   │   └─> Extrai ID
   ├─> db.commit() (tudo ou nada)
   └─> Se erro: db.rollback()
   
6. Resposta ao Cliente
   └─> {"saved": [{"id": 1, "enunciado": "...", "correta": "C"}, ...]}
```

### Fluxo 3: Listar Questões (GET /questoes)

```
1. Cliente HTTP
   └─> GET /questoes?limit=20
   
2. FastAPI Route (main.py)
   └─> listar_questoes(limit=20)
   
3. Banco de Dados (db.py)
   └─> db.query(Questao)
       .order_by(Questao.id.desc())
       .limit(20)
       .all()
   
4. Processamento
   ├─> Para cada linha do banco:
   │   ├─> Parse JSON: alternativas
   │   ├─> Parse JSON: explicacoes_erradas
   │   └─> Monta dicionário com todos os campos
   └─> Lista final
   
5. Resposta ao Cliente
   └─> {"count": 20, "items": [...]}
```

---

## Estrutura do Banco de Dados

### Tabela: `questoes`

```sql
CREATE TABLE questoes (
    id SERIAL PRIMARY KEY,
    categoria VARCHAR,                 -- Tipo de questão (Geral, Lógica, etc)
    topico VARCHAR,                    -- Tópico (variáveis, loops, etc)
    enunciado TEXT NOT NULL,           -- Pergunta completa
    alternativas TEXT NOT NULL,        -- JSON array com 4-5 alternativas
    correta VARCHAR NOT NULL,          -- Letra correta (A, B, C, D, E)
    feedback TEXT,                     -- Explicação da resposta
    explicacoes_erradas TEXT           -- JSON array com explicações
);
```

### Exemplo de Dados

```json
{
  "id": 1,
  "categoria": "Geral",
  "topico": "variaveis",
  "enunciado": "Em Python, como você declara uma variável?",
  "alternativas": [
    "A) A) price = 19.99",
    "B) B) var price = 19.99",
    "C) C) let price = 19.99",
    "D) D) const price = 19.99",
    "E) E) price: float = 19.99"
  ],
  "correta": "A",
  "feedback": "Em Python, as variáveis são declaradas sem palavras-chave...",
  "explicacoes_erradas": [
    "B) var é sintaxe de JavaScript",
    "C) let é sintaxe de JavaScript",
    "D) const é sintaxe de JavaScript",
    "E) Type hint opcional, não obrigatório"
  ]
}
```

---

## Decisões de Design

### 1. Por que FastAPI?
- **Rápido:** Uma das frameworks Python mais rápidas
- **Moderno:** Suporta async/await nativa
- **Documentação automática:** Swagger UI + ReDoc
- **Validação:** Pydantic integrado
- **Type hints:** Code completion melhor

### 2. Por que PostgreSQL?
- **Relacional:** Estrutura clara para dados estruturados
- **Confiável:** ACID compliance
- **Escalável:** Suporta bilhões de registros
- **JSON:** Suporte nativo para armazenar JSON

### 3. Por que Hugging Face API?
- **Gratuito:** Modelo open-source
- **Rápido:** Inferência otimizada
- **Múltiplos modelos:** Fácil trocar modelo
- **Sem GPU:** Não precisa de hardware caro

### 4. Por que Docker?
- **Portabilidade:** Mesmo ambiente em qualquer PC
- **Isolamento:** App + DB separados
- **Reprodutibilidade:** Sempre o mesmo resultado
- **Scaling:** Fácil fazer load balancing

### 5. Estrutura de Arquivos

```
tutor-programacao/
├── src/
│   ├── __init__.py              # Marca como package Python
│   ├── main.py                  # Rotas HTTP (entrada da app)
│   ├── generator.py             # Lógica de geração de questões
│   ├── db.py                    # Modelos e conexão com DB
│   └── static/
│       └── index.html           # UI (se houver)
├── tests/
│   ├── test_generator.py        # Testes unitários
│   └── __pycache__/
├── docker-compose.yml           # Config multi-container
├── Dockerfile                   # Config da imagem
├── requirements.txt             # Dependências Python
├── .env                         # Variáveis de ambiente (local)
├── .gitignore                   # O que não commitir
├── README.md                    # Instrções rápidas
├── DEPLOY.md                    # Guia de deployment
└── TECNICO.md                   # Este arquivo
```

---

## Como Funciona Passo a Passo

### Passo 1: Cliente faz requisição

```bash
curl "http://localhost:8000/question?topic=variaveis&model=llama"
```

### Passo 2: FastAPI valida e roteia

```python
@app.get("/question")
def question(topic: str = Query(...), model: str = Query("llama")):
    # topic = "variaveis"
    # model = "llama"
    out = generate_question(topic, model=model)
    # ... salva e retorna
```

### Passo 3: Generator cria prompt

```python
prompt = f"""
Você é um gerador de questões da Olimpíada Nacional de Inteligência Artificial (ONIA)...
Tópico específico: variaveis

Siga esta metodologia...

Responda SOMENTE com um JSON válido...
"""
```

### Passo 4: Chama Hugging Face

```python
client = InferenceClient(api_key=HF_API_KEY)
r = client.chat_completion(
    model="meta-llama/Meta-Llama-3-8B-Instruct",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=400,
)
text = r["choices"][0]["message"]["content"]
# text = '{"categoria": "Geral", "topico": "variaveis", ...}'
```

### Passo 5: Parse a resposta

```python
parsed = _find_json(text)
# parsed = {...questão em dict}

formatted = format_question(parsed, num_alts=5, letters=["A", "B", "C", "D", "E"])
# formatted = {...com alternativas formatadas}
```

### Passo 6: Salva no banco

```python
obj = Questao(
    categoria=formatted["categoria"],
    topico=formatted["topico"],
    enunciado=formatted["pergunta"],
    alternativas=json.dumps(formatted["alternativas"]),
    correta=formatted["resposta_correta"],
    feedback=formatted["explicacao"],
    explicacoes_erradas=json.dumps(formatted["explicacoes_erradas"])
)
db.add(obj)
db.commit()
# obj.id = 42
```

### Passo 7: Retorna para cliente

```json
{
  "id": 42,
  "categoria": "Geral",
  "topico": "variaveis",
  "pergunta": "Em Python, como você declara uma variável?",
  "alternativas": ["A) A) price = 19.99", "B) B) var price = 19.99", ...],
  "resposta_correta": "A",
  "explicacao": "Em Python, as variáveis são declaradas sem palavras-chave...",
  "explicacoes_erradas": [...]
}
```

---

## Possíveis Evoluções

### Curto Prazo (1-2 sprints)
1. **Autenticação:**
   - JWT tokens
   - Usuários por escola/turma

2. **Relatórios:**
   - GET `/stats` → questões por tópico
   - Gráficos de distribuição

3. **Cache:**
   - Redis para questões geradas recentemente
   - Reduz chamadas ao LLM

### Médio Prazo (2-4 sprints)
1. **Versionamento:**
   - Histórico de alterações
   - Comparar versões

2. **Aprovação de Questões:**
   - Workflow: Gerada → Revisão → Aprovada
   - Rating de qualidade

3. **Templates:**
   - Salvar padrões de prompt
   - Reusar para próximas gerações

4. **Exports:**
   - PDF com questões formatadas
   - CSV para planilhas
   - XML para LMS

### Longo Prazo (4+ sprints)
1. **Machine Learning:**
   - Treinar modelo customizado
   - Fine-tuning com histórico

2. **Múltiplas Linguagens:**
   - Gerar questões em JS, Java, C++
   - Tradução automática

3. **Integração com Plataformas:**
   - Canvas, Moodle, Blackboard
   - Sincronizar automaticamente

4. **Mobile:**
   - App React Native
   - Resolver questões offline

5. **Análise de Dados:**
   - Dashboard de performance
   - Predição de dificuldade

---

## Problemas Conhecidos e Soluções

### Problema 1: Modelos "não-chat" retornam 400

**Sintoma:**
```json
{"error": "The requested model 'xxx' is not a chat model"}
```

**Causa:** Modelo não suporta `chat_completion` no endpoint da HF

**Solução:**
- Use apenas modelos `-Instruct` ou `-Chat`
- Exemplos: `Meta-Llama-3-8B-Instruct`, `Mistral-7B-Instruct-v0.2`

### Problema 2: Timeout ao gerar questão

**Sintoma:** Requisição demora > 60 segundos

**Causa:**
- Modelo carregando (primeira vez)
- Rede lenta
- HF API congestionada

**Solução:**
- Aumentar `timeout` em `call_huggingface_api()`
- Usar modelo menor (7B em vez de 13B)
- Adicionar cache

### Problema 3: Resposta não é JSON válido

**Sintoma:**
```json
{"error": "Resposta inválida do modelo: <texto aleatório>"}
```

**Causa:** LLM não seguiu instrução de retornar JSON

**Solução:**
- Melhorar prompt (mais específico)
- Adicionar exemplos de output esperado
- Tentar modelo maior

### Problema 4: Banco cheio / Performance ruim

**Sintoma:** Queries lentas após 100k questões

**Causa:** Sem índices, sem particionamento

**Solução:**
```sql
-- Adicionar índices
CREATE INDEX idx_questoes_topico ON questoes(topico);
CREATE INDEX idx_questoes_categoria ON questoes(categoria);

-- Particionamento (futuro)
-- PARTITION BY RANGE (id)
```

---

## Checklist de Manutenção

### Diária
- [ ] Verificar logs: `docker compose logs -f api`
- [ ] Monitorar uso de memória/CPU

### Semanal
- [ ] Backup do banco: `docker compose exec db pg_dump > backup.sql`
- [ ] Limpar containers antigos: `docker system prune -a`

### Mensal
- [ ] Review de questões com erro
- [ ] Atualizar dependências: `pip install --upgrade -r requirements.txt`
- [ ] Análise de performance

### Trimestral
- [ ] Revisar modelo de IA (verificar se há versão mais nova)
- [ ] Refatorar código se necessário
- [ ] Documentação atualizada

---

## Contato e Escalação

Para problemas não resolvidos aqui:

1. **Logs:** `docker compose logs --tail=100 api`
2. **Status do DB:** `docker compose ps`
3. **Testar manualmente:** Use Swagger em `/docs`
4. **API Status:** https://status.huggingface.co

---

**Próxima Leitura:** [ARQUIVOS.md](ARQUIVOS.md) - Explicação detalhada de cada arquivo
