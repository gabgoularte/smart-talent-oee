from fastapi import APIRouter, Request

from app.db import check_database
from app.schemas import HealthResponse

router = APIRouter(tags=["Saúde"])


@router.get("/saude", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    database = check_database()
    return HealthResponse(
        status="ok", banco_de_dados=database,
        modelo_carregado=request.app.state.model.loaded, versao_api="1.0.0",
    )
