from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.domain.errors import DomainError, ErrorCategory
from shared.infrastructure.api.error_handlers import register_error_handlers


def _crear_app_de_prueba() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/falla")
    async def falla():
        raise DomainError(
            "recurso duplicado",
            code="TEST-001",
            category=ErrorCategory.CONFLICT,
        )

    @app.get("/falla-no-controlada")
    async def falla_no_controlada():
        raise ValueError("boom")

    @app.get("/id-invalido/{valor}")
    async def id_invalido(valor: str):
        ObjectId(valor)

    return app


def test_domain_error_se_convierte_en_envelope_con_code_category_y_path():
    cliente = TestClient(_crear_app_de_prueba(), raise_server_exceptions=False)

    respuesta = cliente.get("/falla")

    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "status": "error",
        "code": "TEST-001",
        "message": "recurso duplicado",
        "category": "conflict",
        "path": "/falla",
        "metadata": {},
    }


def test_excepcion_no_controlada_se_convierte_en_envelope_gen_500():
    cliente = TestClient(_crear_app_de_prueba(), raise_server_exceptions=False)

    respuesta = cliente.get("/falla-no-controlada")

    assert respuesta.status_code == 500
    assert respuesta.json() == {
        "status": "error",
        "code": "GEN-500",
        "message": "Ocurrio un error interno no controlado.",
        "path": "/falla-no-controlada",
    }


def test_un_identificador_invalido_responde_400_y_no_500():
    cliente = TestClient(_crear_app_de_prueba(), raise_server_exceptions=False)

    respuesta = cliente.get("/id-invalido/esto-no-es-un-object-id")

    assert respuesta.status_code == 400
    assert respuesta.json() == {
        "status": "error",
        "code": "GEN-400",
        "message": "El identificador indicado no es valido.",
        "category": "validation",
        "path": "/id-invalido/esto-no-es-un-object-id",
        "metadata": {},
    }


def test_un_identificador_valido_no_activa_el_manejador():
    cliente = TestClient(_crear_app_de_prueba(), raise_server_exceptions=False)

    assert cliente.get(f"/id-invalido/{ObjectId()}").status_code == 200
