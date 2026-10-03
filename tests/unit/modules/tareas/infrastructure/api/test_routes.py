from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.tareas.application.services.crear_tarea import CrearTareaService
from modules.tareas.application.services.listar_tareas import ListarTareasService
from modules.tareas.domain.entities import Tarea
from modules.tareas.infrastructure.api.dependencies import (
    get_crear_tarea_service,
    get_listar_tareas_service,
)
from modules.tareas.infrastructure.api.routes import router
from shared.infrastructure.api.error_handlers import register_error_handlers


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


def _crear_cliente_de_prueba() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    repositorio = _RepositorioEnMemoria()
    app.dependency_overrides[get_crear_tarea_service] = lambda: CrearTareaService(repositorio)
    app.dependency_overrides[get_listar_tareas_service] = lambda: ListarTareasService(repositorio)

    return TestClient(app)


def test_crear_y_listar_tareas_de_punta_a_punta():
    cliente = _crear_cliente_de_prueba()

    respuesta_crear = cliente.post("/api/tareas", json={"titulo": "Escribir el plan"})
    assert respuesta_crear.status_code == 201
    assert respuesta_crear.json()["status"] == "success"
    assert respuesta_crear.json()["data"]["titulo"] == "Escribir el plan"

    respuesta_listar = cliente.get("/api/tareas")
    assert respuesta_listar.status_code == 200
    assert respuesta_listar.json()["status"] == "success"
    assert len(respuesta_listar.json()["data"]) == 1


def test_crear_tarea_con_titulo_vacio_retorna_422_con_code_tar_001():
    cliente = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/tareas", json={"titulo": "   "})

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "TAR-001"
    assert respuesta.json()["category"] == "business_rule"
