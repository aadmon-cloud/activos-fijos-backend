from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

_FUNCIONES_DE_INDICES = [
    "crear_indices_usuarios",
    "crear_indices_areas",
    "crear_indices_categorias",
    "crear_indices_condiciones",
    "crear_indices_sedes",
    "crear_indices_lugares",
    "crear_indices_activos",
    "crear_indices_activos_historial",
    "crear_indices_solicitudes",
    "crear_indices_mantenimientos",
    "crear_indices_notificaciones",
    "crear_indices_auditorias",
    "crear_indices_movimientos",
]


def _preflight(origen: str):
    with ExitStack() as stack:
        stack.enter_context(
            patch("shared.infrastructure.persistence.mongo.database.mongo_manager.connect")
        )
        stack.enter_context(
            patch("shared.infrastructure.persistence.mongo.database.mongo_manager.close")
        )
        for nombre in _FUNCIONES_DE_INDICES:
            stack.enter_context(patch(f"shared.bootstrap.application.{nombre}", AsyncMock()))
        settings_mock = stack.enter_context(patch("shared.bootstrap.application.settings"))
        settings_mock.CORS_ORIGINS = ["http://localhost:3000"]

        from shared.bootstrap.application import create_app

        with TestClient(create_app()) as cliente:
            return cliente.options(
                "/",
                headers={
                    "Origin": origen,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "x-requested-with",
                },
            )


def test_cors_permite_el_origen_configurado_con_credenciales():
    respuesta = _preflight("http://localhost:3000")

    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert respuesta.headers["access-control-allow-credentials"] == "true"


def test_cors_rechaza_un_origen_no_configurado():
    respuesta = _preflight("http://evil.example")

    assert "access-control-allow-origin" not in respuesta.headers
