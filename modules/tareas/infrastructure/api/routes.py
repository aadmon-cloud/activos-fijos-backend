from typing import Annotated

from fastapi import APIRouter, Depends, status

from modules.tareas.application.dto.crear_tarea_dto import CrearTareaDTO
from modules.tareas.application.services.crear_tarea import CrearTareaService
from modules.tareas.application.services.listar_tareas import ListarTareasService
from modules.tareas.infrastructure.api.dependencies import (
    get_crear_tarea_service,
    get_listar_tareas_service,
)
from modules.tareas.infrastructure.api.schemas import CrearTareaRequest, TareaResponse

router = APIRouter(prefix="/api/tareas", tags=["tareas"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva tarea",
    responses={422: {"description": "El titulo de la tarea es invalido"}},
)
async def crear_tarea(
    body: CrearTareaRequest,
    service: Annotated[CrearTareaService, Depends(get_crear_tarea_service)],
):
    tarea = await service.ejecutar(CrearTareaDTO(titulo=body.titulo))
    return {
        "status": "success",
        "message": "Tarea creada exitosamente.",
        "data": TareaResponse(**tarea.__dict__).model_dump(),
    }


@router.get(
    "",
    summary="Lista las tareas existentes",
)
async def listar_tareas(
    service: Annotated[ListarTareasService, Depends(get_listar_tareas_service)],
):
    tareas = await service.ejecutar()
    return {
        "status": "success",
        "data": [TareaResponse(**tarea.__dict__).model_dump() for tarea in tareas],
    }
