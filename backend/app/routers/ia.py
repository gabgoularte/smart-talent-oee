from fastapi import APIRouter, HTTPException, Request, status

from app.schemas import (
    BatchPredictionItem,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ModelInfoResponse,
    PredictionResponse,
    ReadingInput,
)

router = APIRouter(prefix="/ia", tags=["IA"])


def _service(request: Request):
    service = request.app.state.model
    if not service.loaded:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="modelo_indisponivel")
    return service


@router.get("/modelo", response_model=ModelInfoResponse)
def model_info(request: Request) -> ModelInfoResponse:
    return ModelInfoResponse(**request.app.state.model.info())


@router.post("/prever", response_model=PredictionResponse)
def predict(reading: ReadingInput, request: Request) -> PredictionResponse:
    service = _service(request)
    return PredictionResponse(**service.prediction(reading, service.probabilities([reading])[0]))


@router.post("/prever-lote", response_model=BatchPredictionResponse)
def predict_batch(payload: BatchPredictionRequest, request: Request) -> BatchPredictionResponse:
    service = _service(request)
    probabilities = service.probabilities(payload.leituras)
    results = [BatchPredictionItem(
        indice=index, **service.prediction(reading, probability),
    ) for index, (reading, probability) in enumerate(zip(payload.leituras, probabilities))]
    return BatchPredictionResponse(total=len(results), resultados=results)
