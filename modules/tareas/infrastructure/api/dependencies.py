from functools import lru_cache

from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.tareas.application.services.crear_tarea import CrearTareaService
from modules.tareas.application.services.listar_tareas import ListarTareasService
from modules.tareas.infrastructure.persistence.mongo.tarea_repository import (
    MongoTareaRepository,
)


@lru_cache(maxsize=1)
def get_tarea_repository() -> TareaRepositoryPort:
    return MongoTareaRepository()


def get_crear_tarea_service() -> CrearTareaService:
    return CrearTareaService(tarea_repository=get_tarea_repository())


def get_listar_tareas_service() -> ListarTareasService:
    return ListarTareasService(tarea_repository=get_tarea_repository())
