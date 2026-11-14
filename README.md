# Smart Talent John Deere 🚜

Projeto do tema **Manufatura — Eficiência (OEE)**, desenvolvido em grupo durante o treinamento de computação aplicada à indústria (SQL, Python e Docker).

O repositório sobe um banco Postgres em Docker, cria o modelo de dados e carrega o dataset com migrations do Alembic. O back-end FastAPI disponibiliza os indicadores para o dashboard e uma API de classificação de necessidade de manutenção.

## Dataset

- **Fonte:** [Smart Manufacturing IoT-Cloud Monitoring (Kaggle)](https://www.kaggle.com/datasets/ziya07/smart-manufacturing-iot-cloud-monitoring-dataset)
- **Arquivo:** `smart_manufacturing_data.csv`
- **Volume:** 100.000 leituras e 13 colunas (~7 MB)
- **Estrutura:** 50 máquinas, cerca de 2.000 leituras cada
- **Conteúdo:** temperatura, vibração, umidade, pressão, consumo de energia, status da máquina (0, 1 ou 2), flag de anomalia, vida restante prevista, tipo de falha, risco de downtime e maintenance_required
- **Qualidade:** sem valores nulos e sem linhas duplicadas

## Estrutura do projeto

```text
smart-talent-oee/
├── data/
│   └── smart_manufacturing_data.csv
├── migrations/
│   ├── versions/
│   │   ├── 0001_cria_modelo_estrela.py
│   │   └── 0002_carrega_csv.py
│   ├── env.py
│   └── script.py.mako
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   └── services/
│   └── Dockerfile
├── ml-model/
│   └── models/modelo_manutencao.joblib
├── .env.example
├── .gitignore
├── .python-version
├── alembic.ini
├── docker-compose.yml
├── pyproject.toml
├── README.md
└── uv.lock
```

## Como rodar

**Pré-requisitos:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) e [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
uv sync
docker compose up -d --wait db
uv run alembic upgrade head
docker compose up -d --build backend
```

O back-end fica em `http://localhost:8000` e o banco em `localhost:5432`. Para
parar os serviços:

```bash
docker compose down
```

Se a porta `5432` estiver ocupada, altere o mapeamento no
`docker-compose.yml` para `5433:5432` e ajuste o `DATABASE_URL` usado pelo
Alembic para apontar para `localhost:5433`.

## API

A documentação interativa fica em `http://localhost:8000/docs`. A raiz
`http://localhost:8000/` redireciona para a documentação.

### Saúde

```bash
curl http://localhost:8000/api/v1/saude
```

O resultado esperado contém `status: "ok"`, `banco_de_dados: "ok"` e
`modelo_carregado: true`.

### Endpoints

Todos os endpoints da aplicação usam a base `/api/v1`:

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/saude` | Estado da API, banco e modelo |
| GET | `/resumo` | KPIs da frota |
| GET | `/manutencao/por-faixa` | Taxa de manutenção por faixa de sensor |
| GET | `/manutencao/cobertura-alertas` | Cobertura e precisão dos alertas |
| GET | `/manutencao/origem` | Origem das manutenções |
| GET | `/manutencao/cenarios-limiar` | Cenários de limiar |
| GET | `/manutencao/por-mes` | Indicadores mensais |
| GET | `/leituras/amostra` | Amostra de leituras |
| GET | `/falhas/por-tipo` | Falhas agrupadas por tipo |
| GET | `/tendencia/semanal` | Tendência semanal |
| GET | `/maquinas` | Estado atual das máquinas |
| GET | `/maquinas/{id_maquina}/serie` | Série histórica de uma máquina |
| GET | `/ia/modelo` | Metadados do modelo |
| POST | `/ia/prever` | Previsão para uma leitura |
| POST | `/ia/prever-lote` | Previsões para até 1.000 leituras |

Exemplo de previsão:

```bash
curl -X POST http://localhost:8000/api/v1/ia/prever \
  -H 'Content-Type: application/json' \
  -d '{
    "temperatura": 95,
    "vibracao": 50,
    "umidade": 55,
    "pressao": 3,
    "consumo_energia": 2.7
  }'
```

O modelo é carregado a partir de `ml-model/models/modelo_manutencao.joblib`
localmente e por volume somente leitura no container. O caminho pode ser
alterado com `MODEL_PATH`; as origens permitidas pelo CORS são configuradas em
`CORS_ORIGINS`.

## Validação

```bash
uv run ruff check backend/app
PYTHONPATH=backend uv run python -m compileall -q backend/app
uv run pytest -q
```
