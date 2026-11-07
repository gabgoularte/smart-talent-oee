"""cria o modelo em estrela e as dimensoes fixas

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dim_maquina",
        sa.Column("id_maquina", sa.Integer, primary_key=True, autoincrement=False),
    )
    op.create_table(
        "dim_calendario",
        sa.Column("data_leitura", sa.Date, primary_key=True),
        sa.Column("ano", sa.Integer),
        sa.Column("mes", sa.Integer),
        sa.Column("dia", sa.Integer),
        sa.Column("dia_semana", sa.Integer, comment="0 = domingo ... 6 = sabado"),
    )
    dim_status = op.create_table(
        "dim_status_maquina",
        sa.Column("id_status", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("descricao", sa.String(30), nullable=False),
    )
    dim_falha = op.create_table(
        "dim_tipo_falha",
        sa.Column("id_tipo_falha", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("nome_original", sa.String(40), nullable=False, unique=True),
        sa.Column("descricao", sa.String(60), nullable=False),
    )
    op.create_table(
        "fato_leitura",
        sa.Column("id_leitura", sa.Integer, sa.Identity(), primary_key=True),
        sa.Column("data_hora", sa.DateTime, nullable=False, unique=True),
        sa.Column("data_leitura", sa.Date, sa.ForeignKey("dim_calendario.data_leitura"), nullable=False),
        sa.Column("hora", sa.Integer),
        sa.Column("id_maquina", sa.Integer, sa.ForeignKey("dim_maquina.id_maquina"), nullable=False),
        sa.Column("id_status", sa.Integer, sa.ForeignKey("dim_status_maquina.id_status"), nullable=False),
        sa.Column("id_tipo_falha", sa.Integer, sa.ForeignKey("dim_tipo_falha.id_tipo_falha"), nullable=False),
        sa.Column("temperatura", sa.Float),
        sa.Column("vibracao", sa.Float),
        sa.Column("umidade", sa.Float),
        sa.Column("pressao", sa.Float),
        sa.Column("consumo_energia", sa.Float),
        sa.Column("anomalia", sa.Integer, comment="Vaza o alvo: nao usar como entrada do modelo"),
        sa.Column("risco_downtime", sa.Float, comment="Vaza o alvo: nao usar como entrada do modelo"),
        sa.Column("vida_restante_prevista", sa.Integer, comment="Vaza parte do alvo"),
        sa.Column("manutencao_necessaria", sa.Integer, comment="ALVO: 1 = precisa de manutencao"),
    )
    op.create_index("idx_fato_maquina_data", "fato_leitura", ["id_maquina", "data_leitura"])
    op.create_index("idx_fato_data", "fato_leitura", ["data_leitura"])
    op.create_index("idx_fato_status", "fato_leitura", ["id_status"])
    op.create_index("idx_fato_tipo_falha", "fato_leitura", ["id_tipo_falha"])

    # Dimensoes fixas (dados de referencia)
    op.bulk_insert(dim_status, [
        {"id_status": 0, "descricao": "Ociosa"},
        {"id_status": 1, "descricao": "Operando"},
        {"id_status": 2, "descricao": "Falha"},
    ])
    op.bulk_insert(dim_falha, [
        {"id_tipo_falha": 1, "nome_original": "Normal", "descricao": "Normal"},
        {"id_tipo_falha": 2, "nome_original": "Vibration Issue", "descricao": "Problema de vibracao"},
        {"id_tipo_falha": 3, "nome_original": "Overheating", "descricao": "Superaquecimento"},
        {"id_tipo_falha": 4, "nome_original": "Pressure Drop", "descricao": "Queda de pressao"},
        {"id_tipo_falha": 5, "nome_original": "Electrical Fault", "descricao": "Falha eletrica"},
    ])


def downgrade() -> None:
    op.drop_table("fato_leitura")
    op.drop_table("dim_tipo_falha")
    op.drop_table("dim_status_maquina")
    op.drop_table("dim_calendario")
    op.drop_table("dim_maquina")