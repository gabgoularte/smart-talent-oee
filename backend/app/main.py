import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.routers import dados, ia, saude
from app.services.modelo import ModelService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = ModelService(get_settings())
    service.load()
    app.state.model = service
    yield


app = FastAPI(title="Smart Talent OEE API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origin_list, allow_methods=["*"], allow_headers=["*"])
app.include_router(saude.router, prefix="/api/v1")
app.include_router(dados.router, prefix="/api/v1")
app.include_router(ia.router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"erro": {"codigo": "dados_invalidos", "mensagem": "Os dados enviados são inválidos.", "detalhes": exc.errors()}})


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    detail = str(exc.detail)
    if detail.startswith("maquina_nao_encontrada:"):
        machine_id = detail.split(":", 1)[1]
        code = "maquina_nao_encontrada"
        message = f"Não existe a máquina {machine_id}."
    elif detail == "modelo_indisponivel":
        code = detail
        message = "Modelo de manutenção indisponível."
    else:
        code = "requisicao_invalida"
        message = detail
    return JSONResponse(status_code=exc.status_code, content={"erro": {"codigo": code, "mensagem": message, "detalhes": None}})


@app.exception_handler(Exception)
async def application_error(_: Request, exc: Exception) -> JSONResponse:
    from sqlalchemy.exc import OperationalError
    if isinstance(exc, OperationalError):
        return JSONResponse(status_code=503, content={"erro": {"codigo": "banco_indisponivel", "mensagem": "Banco de dados indisponível.", "detalhes": None}})
    if str(exc) == "modelo_indisponivel":
        return JSONResponse(status_code=503, content={"erro": {"codigo": "modelo_indisponivel", "mensagem": "Modelo de manutenção indisponível.", "detalhes": None}})
    return JSONResponse(status_code=500, content={"erro": {"codigo": "erro_interno", "mensagem": "Erro interno da API.", "detalhes": None}})


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/docs")
