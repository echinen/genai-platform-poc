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
DATABASE_URL=postgresql://user:password@localhost:5432/database_name
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
python3 -m py_compile src/**/*.py
```

## Referencias

- FastAPI: https://fastapi.tiangolo.com/
- Poetry: https://python-poetry.org/docs/
- Gemini API: https://ai.google.dev/
