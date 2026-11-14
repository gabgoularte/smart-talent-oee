import json
import logging
import warnings
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.exceptions import InconsistentVersionWarning

from app.config import Settings
from app.schemas import ReadingInput

logger = logging.getLogger(__name__)

DEFAULT_FEATURES = ["temperature", "vibration", "humidity", "pressure", "energy_consumption"]
API_TO_MODEL = {
    "temperatura": "temperature",
    "vibracao": "vibration",
    "umidade": "humidity",
    "pressao": "pressure",
    "consumo_energia": "energy_consumption",
}


class ModelService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.estimator: Any = None
        self.loaded = False
        self.features: list[str] | None = None
        self.threshold: float | None = None
        self.metrics: dict[str, float] | None = None
        self.train_version: str | None = None
        self.cutoff: str | None = None
        self.algorithm: str | None = None

    def load(self) -> None:
        path = Path(self.settings.model_path)
        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always", InconsistentVersionWarning)
                artifact = joblib.load(path)
            for warning in captured:
                logger.warning("Inconsistência de versão do scikit-learn: %s", warning.message)
            metadata = artifact if isinstance(artifact, dict) else {}
            self.estimator = self._find_estimator(artifact)
            if self.estimator is None:
                raise ValueError("nenhum estimador com predict_proba encontrado")
            self.features = list(metadata.get("features") or getattr(self.estimator, "feature_names_in_", DEFAULT_FEATURES))
            self.threshold = metadata.get("limiar_operacional", metadata.get("limiar"))
            if self.threshold is None:
                self.threshold = 0.5
                logger.warning("Limiar operacional ausente; usando 0.5")
            self.metrics = self._load_metrics(metadata, path)
            self.train_version = metadata.get("versao_sklearn_treino")
            self.cutoff = metadata.get("data_corte_treino")
            self.algorithm = type(self.estimator).__name__
            self.loaded = True
            logger.info("Modelo carregado; scikit-learn treino=%s execução=%s", self.train_version, sklearn.__version__)
        except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
            logger.error("Não foi possível carregar o modelo: %s", exc)
            self.loaded = False

    @staticmethod
    def _find_estimator(artifact: Any) -> Any:
        if hasattr(artifact, "predict_proba"):
            return artifact
        if isinstance(artifact, dict):
            for key in ("pipeline", "modelo", "model", "estimador"):
                if hasattr(artifact.get(key), "predict_proba"):
                    return artifact[key]
            return next((value for value in artifact.values() if hasattr(value, "predict_proba")), None)
        return None

    @staticmethod
    def _load_metrics(metadata: dict[str, Any], path: Path) -> dict[str, float] | None:
        metrics = metadata.get("metricas_teste")
        if metrics is None:
            metrics_path = path.with_name("metricas.json")
            if metrics_path.exists():
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if not isinstance(metrics, dict):
            return None
        aliases = {"precision": "precisao", "precisão": "precisao"}
        return {aliases.get(str(key), str(key)): float(value) for key, value in metrics.items() if isinstance(value, (int, float))}

    def info(self) -> dict[str, Any]:
        return {
            "carregado": self.loaded,
            "algoritmo": self.algorithm,
            "features": self.features,
            "limiar_operacional": self.threshold,
            "versao_sklearn_treino": self.train_version,
            "versao_sklearn_execucao": sklearn.__version__,
            "data_corte_treino": self.cutoff,
            "metricas_teste": self.metrics,
            "preliminar": True,
            "aviso": "O modelo usa apenas sensores e classifica a leitura atual; não prevê o futuro.",
        }

    def probabilities(self, readings: list[ReadingInput]) -> list[float]:
        if not self.loaded or self.estimator is None or self.features is None:
            raise RuntimeError("modelo_indisponivel")
        values = [{API_TO_MODEL[key]: getattr(reading, key) for key in API_TO_MODEL} for reading in readings]
        frame = pd.DataFrame(values, columns=self.features)
        if "vibration" in frame:
            frame["vibration"] = frame["vibration"].mask(frame["vibration"] < 0, np.nan)
        probabilities = self.estimator.predict_proba(frame)
        classes = list(getattr(self.estimator, "classes_", [0, 1]))
        class_index = classes.index(1) if 1 in classes else -1
        return [float(value) for value in probabilities[:, class_index]]

    def prediction(self, reading: ReadingInput, probability: float) -> dict[str, Any]:
        threshold = self.threshold or 0.5
        alert = reading.temperatura > 90 or (reading.vibracao is not None and reading.vibracao > 80)
        status = "critica" if probability >= threshold else "atencao" if probability >= self.settings.limiar_atencao else "saudavel"
        warning = "Vibração negativa tratada como ausente." if reading.vibracao is not None and reading.vibracao < 0 else None
        return {
            "probabilidade_manutencao": probability,
            "manutencao_necessaria": probability >= threshold,
            "limiar_operacional": threshold,
            "em_alerta_regra": alert,
            "status_saude": status,
            "aviso": warning,
        }
