from typing import Annotated

from fastapi import Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.ejemplo_tareas.application.dto.listar_tareas import ListarTareasInput
from modules.ejemplo_tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.ejemplo_tareas.application.services.completar_tarea import CompletarTareaService
from modules.ejemplo_tareas.application.services.crear_tarea import CrearTareaService
from modules.ejemplo_tareas.application.services.listar_tareas import ListarTareasService
from modules.ejemplo_tareas.application.services.obtener_tarea import ObtenerTareaService
from modules.ejemplo_tareas.infrastructure.persistence.mongo.tarea_repository import (
    MongoTareaRepository,
)
from shared.infrastructure.api.dependencies.mongo import get_mongo_db


def get_tarea_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> TareaRepositoryPort:
    return MongoTareaRepository(db)


def get_crear_tarea_service(
    repo: Annotated[TareaRepositoryPort, Depends(get_tarea_repository)],
) -> CrearTareaService:
    return CrearTareaService(tarea_repository=repo)


def get_obtener_tarea_service(
    repo: Annotated[TareaRepositoryPort, Depends(get_tarea_repository)],
) -> ObtenerTareaService:
    return ObtenerTareaService(tarea_repository=repo)


def get_listar_tareas_service(
    repo: Annotated[TareaRepositoryPort, Depends(get_tarea_repository)],
) -> ListarTareasService:
    return ListarTareasService(tarea_repository=repo)


def get_completar_tarea_service(
    repo: Annotated[TareaRepositoryPort, Depends(get_tarea_repository)],
) -> CompletarTareaService:
    return CompletarTareaService(tarea_repository=repo)


def get_listar_tareas_input(
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=10, ge=1, le=100),
) -> ListarTareasInput:
    return ListarTareasInput(pagina=pagina, limite=limite)
