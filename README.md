# GenAI Platform POC

Microservico em FastAPI para receber prompts, persistir em banco, consultar LLM (Gemini) e retornar resposta padronizada.

## Objetivo desta POC

Atender o desafio tecnico com foco em:
- simplicidade
- qualidade minima
- observabilidade basica
- tratamento de erro amigavel

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Poetry
- Docker / Docker Compose
- Gemini API (Google)

## Como rodar localmente

1. Instale o Poetry (se necessario)

```bash
pip3 install poetry
```

2. Instale dependencias

```bash
poetry install
```

3. Configure variaveis de ambiente (`.env`)

```env
APP_NAME=GenAI Platform
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash
GEMINI_URL=https://generativelanguage.googleapis.com/v1beta/interactions
# Rodando a API localmente (fora do Docker)
DATABASE_URL=postgresql://user:password@localhost:5432/database_name

# Rodando a API no Docker Compose (host = nome do servico)
# DATABASE_URL=postgresql://user:password@postgres:5432/database_name
```

4. Rode a API

```bash
poetry run python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

5. Teste health check

```bash
curl http://127.0.0.1:8000/health
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Endpoint principal

### POST /v1/chat

Payload de entrada:

```json
{
  "userId": "12345",
  "prompt": "Como esta a cotacao do dolar hoje?"
}
```

Regras de validacao:
- `userId` obrigatorio e nao pode ser vazio
- `prompt` obrigatorio e nao pode ser vazio

Exemplo de resposta de sucesso:

```json
{
  "id": 1,
  "userId": "12345",
  "prompt": "Como esta a cotacao do dolar hoje?",
  "response": "...",
  "model": "gemini-3.5-flash",
  "timestamp": "2026-07-09T12:00:00Z"
}
```

Exemplo de teste com curl:

```bash
curl --location --request POST 'http://127.0.0.1:8000/v1/chat' \
--header 'Content-Type: application/json' \
--data-raw '{
  "userId": "12345",
  "prompt": "Como esta a cotacao do dolar hoje?"
}'
```

## Diagrama de sequencia

Fluxo de execucao do `POST /v1/chat` na implementacao atual da POC.

```mermaid
sequenceDiagram
  autonumber
  participant C as Cliente
  participant A as API /v1/chat
  participant D as PostgreSQL
  participant L as LLM Service
  participant G as Gemini API

  C->>A: POST /v1/chat (userId, prompt)
  A->>A: Valida payload
  A->>D: INSERT prompt_history (status=PENDING)

  A->>L: generate(prompt)
  L->>G: Request para Gemini

  alt Sucesso na LLM
    G-->>L: Response (texto)
    L-->>A: Texto gerado
    A->>D: UPDATE status=SUCCESS + response + processing_time_ms
    A-->>C: 200 OK (id, userId, prompt, response, model, timestamp)
  else Falha na LLM
    G-->>L: Erro/timeout/5xx
    L-->>A: Excecao
    A->>D: UPDATE status=FAILED
    A-->>C: Erro padronizado (422/502/503/500)
  end
```

## Erros e observabilidade

A API usa exception handlers globais para padronizar respostas de erro.

Formato padrao de erro:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dados de entrada invalidos.",
    "path": "/v1/chat",
    "correlationId": "4e32b4b5-2a11-4e07-a5dc-92f9f01f741d",
    "details": [
      {
        "field": "userId",
        "message": "Campo userId e obrigatorio e nao pode ser vazio."
      }
    ]
  }
}
```

Codigos tratados:
- `422` validacao de entrada
- `502` erro no provedor LLM
- `503` indisponibilidade temporaria no provedor LLM (ex.: circuit breaker aberto)
- `500` erro interno inesperado

### Correlation ID

- O middleware gera (ou reaproveita) `X-Correlation-Id` por requisicao
- O header `X-Correlation-Id` volta na resposta
- Em respostas de erro, `correlationId` tambem aparece no payload

## Resiliencia

O servico de LLM usa retry com `tenacity` para falhas transitorias.

Tambem foi adicionado circuit breaker assincrono com `aiobreaker` para evitar sobrecarga durante indisponibilidade prolongada do provedor.

Politica atual:
- ate 3 tentativas
- backoff exponencial (1s ate 8s)
- retry apenas para erros transitorios
- circuit breaker abre apos 3 falhas consecutivas
- quando aberto, retorna erro amigavel e falha rapido (sem chamar o provedor)
- tentativa de recuperacao apos 60s

Erros elegiveis para retry:
- falhas de rede/timeout (`ConnectError`, `ConnectTimeout`, `ReadTimeout`, `WriteTimeout`, `PoolTimeout`, `RemoteProtocolError`)
- HTTP `408`, `409`, `425`, `429` e `5xx`

Erros que **nao** fazem retry:
- erros funcionais de requisicao (ex.: `400`, `401`, `403`, `404`)

Essa abordagem melhora a disponibilidade sem mascarar erros de configuracao ou contrato.

## Persistencia

Para cada prompt recebido:
- cria registro inicial com status `PENDING`
- chama Gemini em tempo real
- atualiza para `SUCCESS` com `response` e `processing_time_ms`
- em caso de falha, atualiza para `FAILED`

## Arquitetura alvo

Diagrama de referencia para deploy em AWS, mantendo o fluxo implementado na POC.

```mermaid
flowchart TD
  Client["Cliente"]

  subgraph AWS["AWS Cloud"]
    APIGW["API Gateway"]
    ALB["Application Load Balancer"]
    ECS["ECS Fargate<br/>FastAPI"]
    RDS["Amazon RDS<br/>PostgreSQL"]
    ECR["Amazon ECR"]
    SM["Secrets Manager / SSM"]
    CW["CloudWatch Logs + Metrics"]

    APIGW --> ALB
    ALB --> ECS
    ECR --> ECS
    SM --> ECS
    ECS --> RDS
    ECS --> CW
  end

  GEMINI["Gemini API"]

  Client -->|HTTPS| APIGW
  ECS -->|HTTPS| GEMINI
```

Observacao:
- a implementacao atual da POC roda localmente via Docker Compose
- o desenho acima representa a arquitetura alvo

## Estrutura de pastas

```text
src/
  main.py
  api/
    chat_controller.py
  infra/
    database.py
    settings.py
    exceptions.py
    exception_handlers.py
  middlewares/
    correlation_id.py
  models/
    base.py
    prompt_history.py
  repositories/
    prompt_repository.py
  schemas/
    chat_request.py
    chat_response.py
  services/
    chat_service.py
    llm_service.py
```

## Docker

Subir API + banco:

```bash
docker compose up -d --build
```

Logs:

```bash
docker compose logs -f api
```

Parar:

```bash
docker compose down
```

### Quando mudar dependencias (libs)

Sempre que adicionar/remover/atualizar libs no ambiente local, atualize tambem o artefato usado no Docker.

Fluxo recomendado:

```bash
# 1) Alterar dependencias
poetry add <pacote>
# ou
poetry remove <pacote>

# 2) Atualizar lock
poetry lock

# 3) Exportar requirements para o build da imagem
poetry run pip freeze > requirements.txt

# 4) Rebuild da imagem e subir novamente
docker compose up -d --build
```

Observacao:
- se quiser garantir rebuild completo sem cache: `docker compose build --no-cache api`
- commite `pyproject.toml`, `poetry.lock` e `requirements.txt` apos mudancas de dependencia

## Comandos uteis

```bash
# conferir dependencias
poetry show

# validar consistencia do projeto
poetry check

# compilar arquivos python (sanidade)
python3 -m compileall src
```

## Testes

Foram implementados testes essenciais para demonstrar qualidade de engenharia na POC.

Estrutura:

```text
tests/
  conftest.py
  unit/
    test_chat_service.py
    test_llm_service.py
  integration/
    test_health.py
    test_chat_endpoint.py
```

Como executar:

```bash
poetry run pytest -q
```

Escopo dos testes:
- Unitarios (`tests/unit`): validam comportamento isolado dos servicos com `unittest.mock` e `AsyncMock`.
- Integracao (`tests/integration`): validam contrato HTTP com `FastAPI TestClient`.

Premissas de isolamento:
- sem chamadas reais para Gemini (HTTP externo mockado)
- sem chamadas reais para PostgreSQL (bootstrap e dependencias isolados para teste)

Casos cobertos:
- `ChatService.process`: chama LLM, persiste estado e retorna entidade com sucesso.
- `LLMService`: sucesso, timeout e erro externo nao-retryable.
- `GET /health`: retorna `200` e payload esperado.
- `POST /v1/chat`: retorna `200` e payload esperado com integracao Gemini mockada.

## Referencias

- FastAPI: https://fastapi.tiangolo.com/
- Poetry: https://python-poetry.org/docs/
- Gemini API: https://ai.google.dev/
