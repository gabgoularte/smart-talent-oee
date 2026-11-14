# Smart Talent John Deere 🚜

Projeto do tema **Manufatura — Eficiência (OEE)**, desenvolvido em grupo durante o treinamento de computação aplicada à indústria (SQL, Python e Docker).

O repositório sobe um banco Postgres em Docker, cria o modelo de dados e carrega o dataset com migrations do Alembic. Sobre essa base o grupo constrói o dashboard web e um modelo de classificação.

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
├── src/
│   └── main.py
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
cp .env.example .env          # ajuste os valores se quiser
uv sync                       # instala as dependências
docker compose up -d --wait   # sobe o Postgres e espera ficar pronto
uv run alembic upgrade head   # cria as tabelas e carrega o CSV
```

## API

Copie o `.env.example` para `.env` e, após aplicar as migrations, inicie o back-end:

```bash
docker compose up -d --build backend
```

A documentação interativa fica em `http://localhost:8000/docs`. A API usa o modelo
em `ml-model/models/modelo_manutencao.joblib` por padrão no ambiente local e aceita
as origens do Vite configuradas em `CORS_ORIGINS`.
