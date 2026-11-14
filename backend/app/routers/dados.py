from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    AlertCoverageResponse,
    FailureTypesResponse,
    MachineSeriesResponse,
    MachineSummary,
    MaintenanceOriginResponse,
    MonthlyMaintenanceResponse,
    ReadingSampleResponse,
    SensorBandsResponse,
    SummaryResponse,
    ThresholdScenariosResponse,
    WeeklyTrendResponse,
)
from app.services.consultas import queries

router = APIRouter(tags=["Dados"])


@router.get("/resumo", response_model=SummaryResponse)
def summary(request: Request, db: Session = Depends(get_db)) -> SummaryResponse:
    return SummaryResponse(**_summary_with_model(request, db))


def _summary_with_model(request: Request, db: Session) -> dict:
    machines = _machines(request, db)
    counts = {
        "maquinas_saudaveis": sum(item["status_saude"] == "saudavel" for item in machines),
        "maquinas_atencao": sum(item["status_saude"] == "atencao" for item in machines),
        "maquinas_criticas": sum(item["status_saude"] == "critica" for item in machines),
    }
    return queries.summary(db, counts)


@router.get("/manutencao/por-faixa", response_model=SensorBandsResponse)
def sensor_bands(sensor: str = Query(pattern="^(temperatura|vibracao)$"), db: Session = Depends(get_db)) -> SensorBandsResponse:
    return SensorBandsResponse(**queries.sensor_bands(db, sensor))


@router.get("/manutencao/cobertura-alertas", response_model=AlertCoverageResponse)
def coverage(db: Session = Depends(get_db)) -> AlertCoverageResponse:
    return AlertCoverageResponse(**queries.coverage(db))


@router.get("/manutencao/origem", response_model=MaintenanceOriginResponse)
def origins(db: Session = Depends(get_db)) -> MaintenanceOriginResponse:
    return MaintenanceOriginResponse(**queries.origins(db))


@router.get("/manutencao/cenarios-limiar", response_model=ThresholdScenariosResponse)
def scenarios(db: Session = Depends(get_db)) -> ThresholdScenariosResponse:
    return ThresholdScenariosResponse(**queries.scenarios(db))


@router.get("/manutencao/por-mes", response_model=MonthlyMaintenanceResponse)
def monthly(db: Session = Depends(get_db)) -> MonthlyMaintenanceResponse:
    return MonthlyMaintenanceResponse(**queries.monthly(db))


@router.get("/leituras/amostra", response_model=ReadingSampleResponse)
def sample(limit: int = Query(3000, alias="limite", ge=100, le=10000), seed: int = Query(42, alias="semente"), db: Session = Depends(get_db)) -> ReadingSampleResponse:
    return ReadingSampleResponse(**queries.sample(db, limit, seed))


@router.get("/falhas/por-tipo", response_model=FailureTypesResponse)
def failures(db: Session = Depends(get_db)) -> FailureTypesResponse:
    return FailureTypesResponse(**queries.failures(db))


@router.get("/tendencia/semanal", response_model=WeeklyTrendResponse)
def weekly(db: Session = Depends(get_db)) -> WeeklyTrendResponse:
    return WeeklyTrendResponse(**queries.weekly(db))


def _machines(request: Request, db: Session) -> list[dict]:
    model = request.app.state.model
    latest = queries.latest(db)
    readings = []
    model_inputs = []
    from app.schemas import ReadingInput
    for row in latest:
        model_inputs.append(ReadingInput(
            temperatura=row["temperatura"], vibracao=row["vibracao"], umidade=row["umidade"],
            pressao=row["pressao"], consumo_energia=row["consumo_energia"],
        ))
    probabilities = model.probabilities(model_inputs) if model.loaded else [None] * len(latest)
    for row, probability in zip(latest, probabilities):
        threshold = model.threshold or 0.5
        value = probability if probability is not None else 0
        health = "critica" if probability is not None and value >= threshold else "atencao" if probability is not None and value >= model.settings.limiar_atencao else "saudavel"
        action = {"critica": "Programar inspeção imediata: leitura acima do limite.",
                  "atencao": "Acompanhar nas próximas horas e inspecionar na próxima parada.",
                  "saudavel": "Nenhuma ação necessária."}[health]
        readings.append({"id_maquina": row["id_maquina"], "nome": f"Máquina {row['id_maquina']}",
                         "ultima_leitura": {key: row[key] for key in ("data_hora", "temperatura", "vibracao", "umidade", "pressao", "consumo_energia")},
                         "em_alerta": row["temperatura"] > 90 or (row["vibracao"] is not None and row["vibracao"] > 80),
                         "probabilidade_manutencao": probability, "status_saude": health, "acao_recomendada": action})
    return sorted(readings, key=lambda item: item["probabilidade_manutencao"] or 0, reverse=True)


@router.get("/maquinas", response_model=list[MachineSummary])
def machines(request: Request, db: Session = Depends(get_db)) -> list[MachineSummary]:
    return [MachineSummary(**item) for item in _machines(request, db)]


@router.get("/maquinas/{machine_id}/serie", response_model=MachineSeriesResponse)
def machine_series(machine_id: int, request: Request, hours: int = Query(24, ge=1, le=168), db: Session = Depends(get_db)) -> MachineSeriesResponse:
    if not queries.machine_exists(db, machine_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"maquina_nao_encontrada:{machine_id}")
    rows = queries.series(db, machine_id, hours)
    points = []
    for row in rows:
        probability = None
        if request.app.state.model.loaded:
            from app.schemas import ReadingInput
            probability = request.app.state.model.probabilities([ReadingInput(
                temperatura=row["temperatura"], vibracao=row["vibracao"], umidade=row["umidade"],
                pressao=row["pressao"], consumo_energia=row["consumo_energia"],
            )])[0]
        points.append({"data_hora": row["data_hora"], "temperatura": row["temperatura"], "vibracao": row["vibracao"], "probabilidade_manutencao": probability})
    return MachineSeriesResponse(id_maquina=machine_id, nome=f"Máquina {machine_id}", horas=hours,
                                 limites={"temperatura": 90, "vibracao": 80}, pontos=points)
