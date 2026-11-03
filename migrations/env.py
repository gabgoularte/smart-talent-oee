import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Sem autogenerate: as migrations sao escritas a mao.
target_metadata = None


def obter_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Defina DATABASE_URL no arquivo .env (veja .env.example).")
    return url


def run_migrations_offline() -> None:
    context.configure(url=obter_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(obter_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()