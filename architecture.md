**Arquitetura (resumo)**

- Front door: API Gateway (ou Apigee) expondo endpoints `https://api.example.com/v1/*`.
- Backend: Cloud Function `starwars_function` (HTTP) que consulta a API pública `swapi.dev`.
- Autenticação: recomendar OAuth2 / API Key no API Gateway.
- Caching: usar Cloud Memorystore (Redis) ou Cloud CDN para resultados pesados.
- Observabilidade: Stackdriver Logging/Tracing, e alertas por erro/latência.

Fluxo:

1. Cliente chama API Gateway -> aplica autenticação e rate-limit.
2. Gateway encaminha para Cloud Function.
3. Cloud Function consulta `swapi.dev`, aplica filtros/ordenação,
   e retorna ao cliente.

Notas de implementação

- Para produção, adicionar cache com TTL e retry/backoff ao chamar a API externa.
- Considerar migração para Cloud Run se múltiplos endpoints ou consumo maior for necessário.
