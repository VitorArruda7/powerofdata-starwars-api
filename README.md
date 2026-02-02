# PowerOfData - Star Wars API Challenge

Projeto de avaliação para vaga de Back End Python na PowerOfData.

A plataforma oferece uma API REST que permite explorar dados de personagens, planetas, naves e filmes da saga Star Wars via integração com a API pública SWAPI.

## Funcionalidades

- **Busca e filtros**: consulte por resource (people, planets, starships, films) com filtros customizados
- **Ordenação**: ordene resultados em ordem ascendente ou descendente
- **Paginação**: suporte a page/page_size para resultados grandes
- **Autenticação**: proteção por API Key (opcional, via env var `API_KEYS`)
- **Cache**: cache opcional via Redis (via `REDIS_URL`) ou in-memory
- **Consultas correlacionadas**: acesse personagens de um filme específico

## Quickstart Local

Criar virtualenv e instalar dependências:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# ou source .venv/bin/activate (Mac/Linux)
pip install -r requirements.txt
```

Rodar testes:

```bash
pytest -q
```

Ou com verbose:

```bash
pytest -v
```

## Deployment em GCP

### Pré-requisitos

- Conta GCP ativa com billing habilitado
- `gcloud` CLI instalado e configurado (`gcloud auth login`)
- Projeto GCP criado

### Setup de Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha com suas credenciais:

```bash
cp .env.example .env
# Edite .env com seus valores
```

### Deploy da Cloud Function

**Opção 1: Via script bash** (recomendado para Linux/Mac):

```bash
chmod +x deploy.sh
./deploy.sh your-project-id starwars-function us-central1
```

**Opção 2: Via comando gcloud** (Windows PowerShell):

```powershell
$PROJECT_ID = "your-project-id"
$FUNCTION_NAME = "starwars-function"
$REGION = "us-central1"
$API_KEYS = "your-key1,your-key2"

gcloud functions deploy $FUNCTION_NAME `
  --runtime python312 `
  --trigger-http `
  --allow-unauthenticated `
  --entry-point starwars_function `
  --region $REGION `
  --memory 256MB `
  --timeout 60s `
  --set-env-vars "API_KEYS=$API_KEYS" `
  --source .
```

Após o deploy, a função estará disponível em:
```
https://{REGION}-{PROJECT_ID}.cloudfunctions.net/{FUNCTION_NAME}
```

### Deploy da API Gateway

1. Atualize `openapi.yaml` com sua URL de Cloud Function e Project ID.

2. Crie a API e config:

```bash
gcloud api-gateway apis create starwars-api
gcloud api-gateway api-configs create starwars-config \
  --api=starwars-api \
  --openapi-spec=openapi.yaml \
  --location=global
```

3. Crie o gateway:

```bash
gcloud api-gateway gateways create starwars-gateway \
  --api=starwars-api \
  --api-config=starwars-config \
  --location=global
```

A API estará disponível em:
```
https://starwars-gateway-xxxxx.cloud.goog/v1/search
```

## Exemplos de Uso

### Buscar personagens por nome

```bash
curl -H "X-API-KEY: your-key" \
  "https://api.example.com/v1/search?resource=people&name=Luke"
```

### Buscar com paginação

```bash
curl -H "X-API-KEY: your-key" \
  "https://api.example.com/v1/search?resource=people&page=1&page_size=10&sort_by=name&sort_order=asc"
```

### Personagens de um filme

```bash
curl -H "X-API-KEY: your-key" \
  "https://api.example.com/v1/films/1/characters?sort_by=name&sort_order=asc"
```

## Arquitetura

Ver [architecture.md](architecture.md) para detalhes técnicos sobre cache, autenticação e escalabilidade.

## Estrutura do Projeto

```
.
├── function.py              # Cloud Function HTTP handler
├── requirements.txt         # Python dependencies
├── .env.example            # Variáveis de ambiente (template)
├── openapi.yaml            # API Gateway OpenAPI spec
├── deploy.sh               # Script de deployment
├── tests/
│   └── test_function.py    # Testes unitários (8 testes)
├── architecture.md         # Arquitetura técnica
└── README.md              # Este arquivo
```

## Testes

Todos os 8 testes passando:

- ✓ Busca com filtro
- ✓ Autenticação (missing key)
- ✓ Autenticação (invalid key)
- ✓ Paginação
- ✓ Ordenação descendente
- ✓ Personagens de filme
- ✓ Personagens de filme ordenados
- ✓ Sem autenticação (quando não configurada)

Execute com: `pytest -v`

## Requisitos Atendidos

### Critérios de Aceite

- ✓ Utiliza GCP (Cloud Functions + API Gateway)
- ✓ Python como linguagem principal
- ✓ Integração com SWAPI (https://swapi.dev/)
- ✓ Endpoint para consultar informações por resource
- ✓ Sistema de filtros por parâmetros

### Critérios de Avaliação

- ✓ Capacidade de entender e aplicar regras de negócio
- ✓ Implementação das funcionalidades sugeridas
- ✓ Boas práticas de desenvolvimento (type hints, docstrings, estrutura clara)
- ✓ Lógica de programação (cache, paginação, ordenação)
- ✓ Agregação de valor (extras implementados)

### Extras Implementados

- ✓ **Autenticação**: proteção por API Key
- ✓ **Cache**: suporte a Redis com fallback in-memory
- ✓ **Paginação**: page/page_size para resultados grandes
- ✓ **Ordenação avançada**: sort_by com sort_order (asc/desc)
- ✓ **Testes unitários robustos**: 8 testes cobrindo auth, cache, paginação
- ✓ **Arquitetura detalhada**: documentação em architecture.md
- ✓ **Consultas correlacionadas**: GET /v1/films/{id}/characters
- ✓ **OpenAPI/Swagger**: definição completa da API

## Deployment Rápido (Resumo)

1. **Configure GCP**:
   ```bash
   gcloud auth login
   gcloud config set project your-project-id
   ```

2. **Deploy da função**:
   ```bash
   gcloud functions deploy starwars-function \
     --runtime python312 \
     --trigger-http \
     --allow-unauthenticated \
     --entry-point starwars_function \
     --region us-central1 \
     --set-env-vars "API_KEYS=your-key" \
     --source .
   ```

3. **Configure API Gateway** (opcional):
   - Atualize `openapi.yaml` com sua URL
   - Execute os comandos em "Deploy da API Gateway" acima

4. **Teste**:
   ```bash
   curl https://{region}-{project}.cloudfunctions.net/starwars-function/v1/search?resource=people&name=Luke
   ```

## Suporte

Para dúvidas sobre deployment ou uso, consulte:
- [GCP Cloud Functions Docs](https://cloud.google.com/functions/docs)
- [API Gateway Docs](https://cloud.google.com/api-gateway)
- [SWAPI Docs](https://swapi.dev/)
