# PowerOfData - Star Wars API Challenge

Projeto de avaliação para vaga de Back End Python na PowerOfData.

Quickstart

- criar virtualenv e instalar dependências:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

- rodar testes:

```bash
pytest -q
```

Arquitetura e deploy

- A função HTTP `starwars_function` em `function.py` é a entrada prevista para o Cloud Functions.
- Exemplo de deploy (Cloud Functions):

```bash
gcloud functions deploy starwars_function \\
  --runtime python39 \\
  --trigger-http \\
  --allow-unauthenticated \\
  --entry-point starwars_function
```

- Para expor via API Gateway: criar um API config que roteie `/v1/*` para a Cloud Function.
