from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorBody(BaseModel):
    codigo: str
    mensagem: str
    detalhes: Any = None


class ErrorResponse(BaseModel):
    erro: ErrorBody


class HealthResponse(BaseModel):
    status: str
    banco_de_dados: Literal["ok", "indisponivel", "sem_tabelas"]
    modelo_carregado: bool
    versao_api: str


class SummaryResponse(BaseModel):
    periodo_inicio: datetime | None
    periodo_fim: datetime | None
    total_leituras: int
    disponibilidade: float
    participacao_status: dict[str, float]
    taxa_manutencao: float
    leituras_vibracao_invalida: int
    total_maquinas: int
    maquinas_saudaveis: int
    maquinas_atencao: int
    maquinas_criticas: int


class SensorBand(BaseModel):
    rotulo: str
    de: float | None
    ate: float | None
    leituras: int
    manutencoes: int
    taxa_manutencao: float
    acima_do_limite: bool


class SensorBandsResponse(BaseModel):
    sensor: Literal["temperatura", "vibracao"]
    limite_alerta: float
    taxa_geral: float
    faixas: list[SensorBand]


class AlertCoverageResponse(BaseModel):
    regra: dict[str, float]
    total_manutencoes: int
    com_alerta: int
    sem_alerta: int
    cobertura: float
    cobertura_ic95: list[float]
    leituras_com_alerta: int
    precisao: float
    taxa_sem_alerta: float
    taxa_base: float


class MaintenanceOrigin(BaseModel):
    origem: str
    rotulo: str
    leituras: int
    proporcao: float


class MaintenanceOriginResponse(BaseModel):
    total_manutencoes: int
    origens: list[MaintenanceOrigin]


class ThresholdScenario(BaseModel):
    cenario: str
    ordem: int
    limite_temperatura: float
    limite_vibracao: float
    cobertura: float
    precisao: float
    leituras_sinalizadas: int
    proporcao_sinalizadas: float


class ThresholdScenariosResponse(BaseModel):
    taxa_base: float
    cenarios: list[ThresholdScenario]


class MonthlyMaintenance(BaseModel):
    mes: str
    leituras: int
    manutencoes: int
    taxa_manutencao: float
    cobertura: float
    precisao: float


class MonthlyMaintenanceResponse(BaseModel):
    meses: list[MonthlyMaintenance]


class SamplePoint(BaseModel):
    id_leitura: int
    temperatura: float
    vibracao: float
    manutencao_necessaria: int


class ReadingSampleResponse(BaseModel):
    total_amostrado: int
    limites: dict[str, float]
    pontos: list[SamplePoint]


class FailureType(BaseModel):
    tipo: str
    rotulo: str
    leituras: int
    proporcao: float
    nao_classificada: bool


class FailureTypesResponse(BaseModel):
    total_falhas: int
    tipos: list[FailureType]


class WeeklyTrend(BaseModel):
    semana_inicio: date
    leituras: int
    taxa_manutencao: float
    disponibilidade: float


class WeeklyTrendResponse(BaseModel):
    semanas: list[WeeklyTrend]


class ReadingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperatura: float = Field(ge=-50, le=300)
    vibracao: float | None = Field(default=None, ge=-100, le=500)
    umidade: float = Field(ge=0, le=100)
    pressao: float = Field(ge=0, le=50)
    consumo_energia: float = Field(ge=0, le=100)


class MachineReading(BaseModel):
    data_hora: datetime
    temperatura: float
    vibracao: float | None
    umidade: float
    pressao: float
    consumo_energia: float


class MachineSummary(BaseModel):
    id_maquina: int
    nome: str
    ultima_leitura: MachineReading
    em_alerta: bool
    probabilidade_manutencao: float | None
    status_saude: Literal["critica", "atencao", "saudavel"]
    acao_recomendada: str


class MachineSeriesPoint(BaseModel):
    data_hora: datetime
    temperatura: float
    vibracao: float | None
    probabilidade_manutencao: float | None


class MachineSeriesResponse(BaseModel):
    id_maquina: int
    nome: str
    horas: int
    limites: dict[str, float]
    pontos: list[MachineSeriesPoint]


class ModelInfoResponse(BaseModel):
    carregado: bool
    algoritmo: str | None
    features: list[str] | None
    limiar_operacional: float | None
    versao_sklearn_treino: str | None
    versao_sklearn_execucao: str
    data_corte_treino: str | None
    metricas_teste: dict[str, float] | None
    preliminar: bool
    aviso: str


class PredictionResponse(BaseModel):
    probabilidade_manutencao: float
    manutencao_necessaria: bool
    limiar_operacional: float
    em_alerta_regra: bool
    status_saude: Literal["critica", "atencao", "saudavel"]
    aviso: str | None


class BatchPredictionRequest(BaseModel):
    leituras: list[ReadingInput] = Field(min_length=1, max_length=1000)


class BatchPredictionItem(PredictionResponse):
    indice: int


class BatchPredictionResponse(BaseModel):
    total: int
    resultados: list[BatchPredictionItem]
