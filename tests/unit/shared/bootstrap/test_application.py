from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_create_app_expone_endpoint_raiz_con_cabeceras_de_seguridad():
    with (
        patch("shared.infrastructure.persistence.mongo.database.mongo_manager.connect"),
        patch("shared.infrastructure.persistence.mongo.database.mongo_manager.close"),
        patch("shared.bootstrap.application.crear_indices_usuarios", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_areas", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_categorias", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_condiciones", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_sedes", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_lugares", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_activos", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_activos_historial", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_solicitudes", AsyncMock()),
    ):
        from shared.bootstrap.application import create_app

        with TestClient(create_app()) as cliente:
            respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"


from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.tareas.domain.entities import Tarea
from modules.tareas.infrastructure.api.dependencies import (
    get_crear_tarea_service,
    get_listar_tareas_service,
)
from modules.tareas.application.services.crear_tarea import CrearTareaService
from modules.tareas.application.services.listar_tareas import ListarTareasService


class _RepositorioEnMemoria(TareaRepositoryPort):
    def __init__(self):
        self._tareas: list[Tarea] = []

    async def guardar(self, tarea: Tarea) -> Tarea:
        tarea_con_id = Tarea(
            id=str(len(self._tareas) + 1),
            titulo=tarea.titulo,
            completada=tarea.completada,
            fecha_creacion=tarea.fecha_creacion,
        )
        self._tareas.append(tarea_con_id)
        return tarea_con_id

    async def listar(self) -> list[Tarea]:
        return list(self._tareas)


def test_create_app_registra_el_modulo_tareas():
    with (
        patch("shared.infrastructure.persistence.mongo.database.mongo_manager.connect"),
        patch("shared.infrastructure.persistence.mongo.database.mongo_manager.close"),
        patch("shared.bootstrap.application.crear_indices_usuarios", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_areas", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_categorias", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_condiciones", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_sedes", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_lugares", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_activos", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_activos_historial", AsyncMock()),
        patch("shared.bootstrap.application.crear_indices_solicitudes", AsyncMock()),
    ):
        from shared.bootstrap.application import create_app

        app = create_app()
        repositorio = _RepositorioEnMemoria()
        app.dependency_overrides[get_crear_tarea_service] = lambda: CrearTareaService(repositorio)
        app.dependency_overrides[get_listar_tareas_service] = lambda: ListarTareasService(repositorio)

        with TestClient(app) as cliente:
            respuesta_crear = cliente.post("/api/tareas", json={"titulo": "Probar wiring"})
            respuesta_listar = cliente.get("/api/tareas")

    assert respuesta_crear.status_code == 201
    assert respuesta_crear.json()["status"] == "success"
    assert respuesta_listar.status_code == 200
    assert respuesta_listar.json()["status"] == "success"
    assert len(respuesta_listar.json()["data"]) == 1
