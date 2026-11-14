import math
import random
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class QueryService:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, Any]] = {}

    def _cached(self, key: str, query: Callable[[], Any]) -> Any:
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < 300:
            return cached[1]
        value = query()
        self._cache[key] = (time.monotonic(), value)
        return value

    @staticmethod
    def _rows(db: Session, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [dict(row) for row in db.execute(text(sql), params or {}).mappings().all()]

    def summary(self, db: Session, machine_counts: dict[str, int]) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            row = self._rows(db, """
                SELECT MIN(data_hora) AS inicio, MAX(data_hora) AS fim, COUNT(*) AS total,
                       AVG((id_status = 1)::int)::float AS disponibilidade,
                       AVG((id_status = 0)::int)::float AS ociosa,
                       AVG((id_status = 2)::int)::float AS falha,
                       AVG(manutencao_necessaria)::float AS taxa,
                       COUNT(*) FILTER (WHERE vibracao < 0) AS invalidas,
                       COUNT(DISTINCT id_maquina) AS maquinas
                FROM fato_leitura
            """)[0]
            return {
                "periodo_inicio": row["inicio"], "periodo_fim": row["fim"], "total_leituras": row["total"],
                "disponibilidade": row["disponibilidade"] or 0, "participacao_status": {
                    "operando": row["disponibilidade"] or 0, "ociosa": row["ociosa"] or 0, "falha": row["falha"] or 0,
                }, "taxa_manutencao": row["taxa"] or 0, "leituras_vibracao_invalida": row["invalidas"],
                "total_maquinas": row["maquinas"], **machine_counts,
            }
        return self._cached("summary", run)

    def sensor_bands(self, db: Session, sensor: str) -> dict[str, Any]:
        column = "temperatura" if sensor == "temperatura" else "vibracao"
        limit = 90 if sensor == "temperatura" else 80
        bounds = [70, 80, 90, 100] if sensor == "temperatura" else [40, 60, 80, 100]
        rows = self._rows(db, f"""
            SELECT bucket, COUNT(*) AS leituras, SUM(manutencao_necessaria) AS manutencoes
            FROM (
                SELECT CASE
                    WHEN {column} <= :b1 THEN 0 WHEN {column} <= :b2 THEN 1
                    WHEN {column} <= :b3 THEN 2 WHEN {column} <= :b4 THEN 3 ELSE 4 END AS bucket,
                    manutencao_necessaria
                FROM fato_leitura WHERE (:sensor <> 'vibracao' OR vibracao >= 0)
            ) x GROUP BY bucket ORDER BY bucket
        """, {"b1": bounds[0], "b2": bounds[1], "b3": bounds[2], "b4": bounds[3], "sensor": sensor})
        total = self._rows(db, "SELECT AVG(manutencao_necessaria)::float AS taxa FROM fato_leitura")[0]["taxa"] or 0
        labels = [f"Até {bounds[0]}", f"{bounds[0]} a {bounds[1]}", f"{bounds[1]} a {bounds[2]}", f"{bounds[2]} a {bounds[3]}", f"Acima de {bounds[3]}"]
        bands = []
        for index, label in enumerate(labels):
            row = next((item for item in rows if item["bucket"] == index), {"leituras": 0, "manutencoes": 0})
            bands.append({"rotulo": label, "de": None if index == 0 else bounds[index - 1], "ate": bounds[index] if index < 4 else None,
                          "leituras": row["leituras"], "manutencoes": row["manutencoes"] or 0,
                          "taxa_manutencao": (row["manutencoes"] or 0) / row["leituras"] if row["leituras"] else 0,
                          "acima_do_limite": (bounds[index - 1] if index else bounds[0]) >= limit})
        return {"sensor": sensor, "limite_alerta": limit, "taxa_geral": total, "faixas": bands}

    def coverage(self, db: Session) -> dict[str, Any]:
        row = self._rows(db, """
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE manutencao_necessaria = 1 AND (temperatura > 90 OR vibracao > 80)) AS com_alerta,
                   COUNT(*) FILTER (WHERE temperatura > 90 OR vibracao > 80) AS alertas,
                   COUNT(*) FILTER (WHERE manutencao_necessaria = 1 AND NOT (temperatura > 90 OR vibracao > 80)) AS sem_alerta,
                   AVG(manutencao_necessaria)::float AS taxa
            FROM fato_leitura
        """)[0]
        total, hit, alerts = row["total"], row["com_alerta"], row["alertas"]
        precision = hit / alerts if alerts else 0
        maintenance_total = round(row["taxa"] * total)
        p = hit / maintenance_total if maintenance_total else 0
        sample_size = maintenance_total
        z = 1.96
        denominator = 1 + z * z / sample_size if sample_size else 1
        center = (p + z * z / (2 * sample_size)) / denominator if sample_size else 0
        margin = z * math.sqrt(p * (1 - p) / sample_size + z * z / (4 * sample_size ** 2)) / denominator if sample_size else 0
        return {"regra": {"temperatura_acima": 90, "vibracao_acima": 80}, "total_manutencoes": maintenance_total,
                "com_alerta": hit, "sem_alerta": row["sem_alerta"], "cobertura": hit / (row["taxa"] * total) if row["taxa"] else 0,
                "cobertura_ic95": [max(0, center - margin), min(1, center + margin)],
                "leituras_com_alerta": alerts, "precisao": precision,
                "taxa_sem_alerta": row["sem_alerta"] / total if total else 0, "taxa_base": row["taxa"] or 0}

    def origins(self, db: Session) -> dict[str, Any]:
        rows = self._rows(db, """
            SELECT origem, COUNT(*) AS leituras FROM (
              SELECT CASE WHEN temperatura > 90 OR vibracao > 80 THEN 'alerta_sensor'
                          WHEN id_status = 2 THEN 'maquina_em_falha'
                          WHEN vida_restante_prevista < 20 THEN 'vida_restante_baixa'
                          ELSE 'outros' END AS origem
              FROM fato_leitura WHERE manutencao_necessaria = 1
            ) x GROUP BY origem
        """)
        labels = {"alerta_sensor": "Alerta de sensor", "maquina_em_falha": "Máquina já em falha",
                  "vida_restante_baixa": "Vida restante baixa", "outros": "Outros"}
        total = sum(row["leituras"] for row in rows)
        return {"total_manutencoes": total, "origens": [{"origem": key, "rotulo": labels[key], "leituras": next((r["leituras"] for r in rows if r["origem"] == key), 0),
                    "proporcao": next((r["leituras"] for r in rows if r["origem"] == key), 0) / total if total else 0} for key in labels]}

    def scenarios(self, db: Session) -> dict[str, Any]:
        rows = self._rows(db, """
            SELECT manutencao_necessaria, temperatura, vibracao FROM fato_leitura
        """)
        total = len(rows)
        maintenance = sum(row["manutencao_necessaria"] for row in rows)
        thresholds = [(90, 80), (85, 75), (80, 70), (75, 65), (70, 60)]
        scenarios = []
        for order, (temperature, vibration) in enumerate(thresholds, 1):
            selected = [row for row in rows if row["temperatura"] > temperature or row["vibracao"] > vibration]
            hits = sum(row["manutencao_necessaria"] for row in selected)
            scenarios.append({"cenario": f"T>{temperature} ou V>{vibration}", "ordem": order,
                              "limite_temperatura": temperature, "limite_vibracao": vibration,
                              "cobertura": hits / maintenance if maintenance else 0, "precisao": hits / len(selected) if selected else 0,
                              "leituras_sinalizadas": len(selected), "proporcao_sinalizadas": len(selected) / total if total else 0})
        return {"taxa_base": maintenance / total if total else 0, "cenarios": scenarios}

    def monthly(self, db: Session) -> dict[str, Any]:
        rows = self._rows(db, """
            SELECT TO_CHAR(data_hora, 'YYYY-MM') AS mes, COUNT(*) AS leituras, SUM(manutencao_necessaria) AS manutencoes,
                   COUNT(*) FILTER (WHERE manutencao_necessaria = 1 AND (temperatura > 90 OR vibracao > 80)) AS hits,
                   COUNT(*) FILTER (WHERE temperatura > 90 OR vibracao > 80) AS alertas
            FROM fato_leitura GROUP BY 1 ORDER BY 1
        """)
        return {"meses": [{"mes": row["mes"], "leituras": row["leituras"], "manutencoes": row["manutencoes"],
                           "taxa_manutencao": row["manutencoes"] / row["leituras"], "cobertura": row["hits"] / row["manutencoes"] if row["manutencoes"] else 0,
                           "precisao": row["hits"] / row["alertas"] if row["alertas"] else 0} for row in rows]}

    def sample(self, db: Session, limit: int, seed: int) -> dict[str, Any]:
        rows = self._rows(db, """
            SELECT id_leitura, temperatura, vibracao, manutencao_necessaria
            FROM fato_leitura WHERE vibracao >= 0 ORDER BY id_leitura
        """)
        random.Random(seed).shuffle(rows)
        points = rows[:limit]
        return {"total_amostrado": len(points), "limites": {"temperatura": 90, "vibracao": 80}, "pontos": points}

    def failures(self, db: Session) -> dict[str, Any]:
        rows = self._rows(db, """
            SELECT CASE WHEN f.id_status = 2 AND t.nome_original = 'Normal' THEN 'Não classificada' ELSE t.nome_original END AS tipo,
                   CASE WHEN f.id_status = 2 AND t.nome_original = 'Normal' THEN 'Não classificada' ELSE t.descricao END AS rotulo,
                   COUNT(*) AS leituras
            FROM fato_leitura f JOIN dim_tipo_falha t USING (id_tipo_falha)
            WHERE f.id_status = 2 GROUP BY 1, 2 ORDER BY leituras DESC
        """)
        total = sum(row["leituras"] for row in rows)
        return {"total_falhas": total, "tipos": [{**row, "proporcao": row["leituras"] / total if total else 0,
                                                   "nao_classificada": row["tipo"] == "Não classificada"} for row in rows]}

    def weekly(self, db: Session) -> dict[str, Any]:
        rows = self._rows(db, """
            SELECT date_trunc('week', data_hora)::date AS semana_inicio, COUNT(*) AS leituras,
                   AVG(manutencao_necessaria)::float AS taxa_manutencao, AVG((id_status = 1)::int)::float AS disponibilidade
            FROM fato_leitura GROUP BY 1 ORDER BY 1
        """)
        return {"semanas": rows}

    def latest(self, db: Session) -> list[dict[str, Any]]:
        return self._rows(db, """
            SELECT DISTINCT ON (id_maquina) id_maquina, data_hora, temperatura, vibracao, umidade, pressao, consumo_energia,
                   id_status FROM fato_leitura ORDER BY id_maquina, data_hora DESC
        """)

    def series(self, db: Session, machine_id: int, hours: int) -> list[dict[str, Any]]:
        return self._rows(db, """
            WITH ultima AS (SELECT MAX(data_hora) AS data_hora FROM fato_leitura)
            SELECT data_hora, temperatura, vibracao, umidade, pressao, consumo_energia FROM fato_leitura
            WHERE id_maquina = :machine_id
              AND data_hora >= (SELECT data_hora FROM ultima) - (:hours * INTERVAL '1 hour')
              AND data_hora <= (SELECT data_hora FROM ultima)
            ORDER BY data_hora
        """, {"machine_id": machine_id, "hours": hours})

    def machine_exists(self, db: Session, machine_id: int) -> bool:
        return bool(self._rows(db, "SELECT 1 FROM dim_maquina WHERE id_maquina = :machine_id", {"machine_id": machine_id}))


queries = QueryService()
