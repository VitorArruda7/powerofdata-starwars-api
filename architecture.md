# Arquitetura da Plataforma Star Wars API

## Visão Geral

```
Cliente HTTP
    ↓
API Gateway (rate limit, auth, logging)
    ↓
Cloud Function (starwars-function)
    ↓
├── Cache Layer (Redis ou in-memory)
│    ↓
└── SWAPI (https://swapi.dev/)
```

## Componentes

### 1. API Gateway (Apigee/API Gateway)
- **Responsabilidade**: roteamento, autenticação, rate limiting, logging
- **Benefícios**:
  - Isolamento da Cloud Function
  - Rate limiting para evitar abuso
  - Logs centralizados e métricas
  - Versionamento de API (`/v1/`)
- **Configuração**: `openapi.yaml`

### 2. Cloud Function (HTTP)
- **Runtime**: Python 3.12
- **Trigger**: HTTP (público via API Gateway)
- **Responsabilidades**:
  - Validar requisições (resource, parâmetros)
  - Aplicar filtros, ordenação e paginação
  - Chamar cache antes de SWAPI
  - Retornar JSON estruturado

### 3. Cache Layer
- **In-memory** (padrão): simples, sem dependências externas
  - Persiste durante o ciclo de vida da função
  - TTL efetivo apenas entre invocações
- **Redis** (opcional via `REDIS_URL`):
  - Cache persistente entre invocações
  - TTL de 5 minutos por padrão
  - Escalável para múltiplas instâncias
  - Requer Cloud Memorystore para GCP

### 4. SWAPI (Star Wars API)
- **Endpoint**: https://swapi.dev/api/
- **Rate limit**: ~50 req/s (suficiente para carga normal)
- **Dados disponíveis**: people, planets, starships, films, species, vehicles
- **Resposta**: JSON com paginação automática

## Fluxo de Requisição

```
1. Cliente envia GET /v1/search?resource=people&name=Luke
   └─ Headers incluem X-API-KEY se API_KEYS está ativa

2. API Gateway:
   └─ Valida X-API-KEY (se configurado)
   └─ Aplica rate limiting
   └─ Roteia para Cloud Function

3. Cloud Function starwars_function():
   ├─ Valida parâmetros (resource, filters)
   ├─ Chama cache_get('https://swapi.dev/api/people/')
   │  └─ Se hit: retorna dados cacheados
   │  └─ Se miss:
   │     ├─ Chama fetch_url() → requests.get(url)
   │     ├─ Armazena em cache_set() com TTL 5min
   │     └─ Aplica filtros, ordenação, paginação
   └─ Retorna JSON: {count, page, page_size, results}

4. API Gateway:
   └─ Registra resposta em logs
   └─ Retorna ao cliente
```

## Segurança

### Autenticação
- **API Key**: header `X-API-KEY` ou query param `api_key`
- **Ativação**: definir env var `API_KEYS` (comma-separated)
- **Exemplo**: `API_KEYS=key1,key2,key3`
- **Desativação**: deixar `API_KEYS` em branco (default)

### Rate Limiting
- Implementado no **API Gateway** (não na Cloud Function)
- Recomendado: 1000 req/min por chave
- Fallback: SWAPI tem ~50 req/s

### Validação de Entrada
- Whitelist de resources: `['people', 'planets', 'starships', 'films']`
- Sanitização de filtros: busca case-insensitive em strings
- Paginação: limites mínimos/máximos em page e page_size

## Performance e Escalabilidade

### Cold Start
- Cloud Functions: ~1-2s na primeira invocação
- Mitigation: configurar mín 1 instância ativa no GCP

### Caching
- **Hit rate esperado**: 60-80% (dados SWAPI mudam raramente)
- **TTL**: 5 minutos (balanceamento entre atualização e hit rate)
- **Com Redis**: escalável para múltiplas instâncias e geograficamente distribuído

### Paginação
- Sem paginação: até 100+ resultados retornados
- Com paginação: page_size padrão ilimitado, recomenda-se 10-50
- Exemplos:
  - Page 1, size 20: primeiros 20 resultados
  - Page 2, size 20: resultados 21-40

### Ordenação
- Suportada por qualquer campo do JSON
- Ordenação in-memory (após fetch)
- Complexidade: O(n log n) esperada

## Escalamento Futuro

### 1. Replicação de Dados
- Cache SWAPI inteiro em Cloud Datastore ou Firestore
- Sincronização automática (via Cloud Scheduler)
- Reduz latência e dependência de SWAPI

### 2. Cloud Run
- Migrar de Cloud Functions para Cloud Run se:
  - Múltiplos endpoints complexos
  - Consumo > 100 GB/mês
  - Customizações grandes (frameworks web)

### 3. Memorystore Redis Premium
- Replicação multi-região
- Backup automático
- Failover automático

### 4. BigQuery
- Armazenar logs de requisições
- Analytics: trending characters, popular films
- Recomendações personalizadas

## Variáveis de Ambiente

| Var | Padrão | Descrição |
|-----|--------|-----------|
| `API_KEYS` | "" | Chaves de autenticação (comma-separated) |
| `REDIS_URL` | "" | URL de conexão Redis (ex: `redis://host:6379`) |

## Deployment

### Via gcloud CLI
```bash
gcloud functions deploy starwars-function \
  --runtime python312 \
  --trigger-http \
  --entry-point starwars_function \
  --region us-central1 \
  --memory 256MB \
  --timeout 60s \
  --set-env-vars "API_KEYS=key1,key2" \
  --source .
```

### Custo Estimado (GCP)
- **Cloud Functions**: $0.40/milhão de invocações + $0.0000025/GB-segundo
- **API Gateway**: $3.50 por milhão de requests
- **Total para 1M requisições**: ~$5/mês (com cache hit rate alto)

## Monitoramento

### Logs
- Cloud Logging: `gcloud functions logs read starwars-function`
- Filtros por nível (INFO, ERROR, DEBUG)

### Métricas
- Invocation count
- Execution time (p50, p95, p99)
- Error rate
- Memory usage

### Alertas Recomendados
- Error rate > 1%
- Latência p95 > 5s
- SWAPI indisponível (health check)

## Notas de Implementação

- Para produção, adicionar **retry com backoff** ao chamar SWAPI
- Considerar **circuit breaker** se SWAPI cair
- Usar **structured logging** (JSON) para melhor análise
- Considerar **rate limiting por cliente** (IP ou API key)
- **Health check endpoint** para monitoramento (GET /health)
