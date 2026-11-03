"""carrega o CSV nas dimensoes e na fato

Le o CSV do repositorio (no seu computador) e envia ao Postgres com COPY,
passando por uma tabela temporaria de staging.

Revision ID: 0002
Revises: 0001
"""
import os
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

RAIZ = Path(__file__).resolve().parents[2]


def caminho_csv() -> Path:
    caminho = Path(os.getenv("CSV_PATH") or "data/smart_manufacturing_data.csv")
    return caminho if caminho.is_absolute() else RAIZ / caminho


def upgrade() -> None:
    csv = caminho_csv()
    if not csv.exists():
        raise FileNotFoundError(f"CSV nao encontrado: {csv}")

    bind = op.get_bind()

    # Mesma ordem de colunas do CSV (o cabecalho e ignorado pelo COPY)
    bind.execute(sa.text("""
        CREATE TEMP TABLE stg_leitura (
            ts                       timestamp,
            machine_id               integer,
            temperature              double precision,
            vibration                double precision,
            humidity                 double precision,
            pressure                 double precision,
            energy_consumption       double precision,
            machine_status           integer,
            anomaly_flag             integer,
            predicted_remaining_life integer,
            failure_type             text,
            downtime_risk            double precision,
            maintenance_required     integer
        ) ON COMMIT DROP
    """))

    cursor = bind.connection.cursor()
    with cursor.copy("COPY stg_leitura FROM STDIN WITH (FORMAT csv, HEADER true)") as copy:
        with open(csv, "rb") as arquivo:
            while bloco := arquivo.read(1024 * 1024):
                copy.write(bloco)

    bind.execute(sa.text("""
        INSERT INTO dim_maquina (id_maquina)
        SELECT DISTINCT machine_id FROM stg_leitura ORDER BY 1
    """))

    bind.execute(sa.text("""
        INSERT INTO dim_calendario (data_leitura, ano, mes, dia, dia_semana)
        SELECT d,
               EXTRACT(YEAR  FROM d)::int,
               EXTRACT(MONTH FROM d)::int,
               EXTRACT(DAY   FROM d)::int,
               EXTRACT(DOW   FROM d)::int
        FROM (SELECT DISTINCT ts::date AS d FROM stg_leitura) t
        ORDER BY d
    """))

    bind.execute(sa.text("""
        INSERT INTO fato_leitura (
            data_hora, data_leitura, hora, id_maquina, id_status, id_tipo_falha,
            temperatura, vibracao, umidade, pressao, consumo_energia,
            anomalia, risco_downtime, vida_restante_prevista, manutencao_necessaria
        )
        SELECT s.ts, s.ts::date, EXTRACT(HOUR FROM s.ts)::int,
               s.machine_id, s.machine_status, t.id_tipo_falha,
               s.temperature, s.vibration, s.humidity, s.pressure, s.energy_consumption,
               s.anomaly_flag, s.downtime_risk, s.predicted_remaining_life, s.maintenance_required
        FROM stg_leitura s
        JOIN dim_tipo_falha t ON t.nome_original = s.failure_type
        ORDER BY s.ts
    """))

    total_csv = bind.execute(sa.text("SELECT COUNT(*) FROM stg_leitura")).scalar()
    total_fato = bind.execute(sa.text("SELECT COUNT(*) FROM fato_leitura")).scalar()
    if total_csv != total_fato:
        raise RuntimeError(f"Linhas perdidas na carga: CSV={total_csv}, fato={total_fato}")


def downgrade() -> None:
    op.execute("DELETE FROM fato_leitura")
    op.execute("DELETE FROM dim_calendario")
    op.execute("DELETE FROM dim_maquina")