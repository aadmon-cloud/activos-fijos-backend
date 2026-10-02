from typing import Annotated

from fastapi import APIRouter, Depends, status

from modules.ejemplo_tareas.application.dto.crear_tarea import CrearTareaInput
from modules.ejemplo_tareas.application.dto.listar_tareas import ListarTareasInput
from modules.ejemplo_tareas.application.services.completar_tarea import (
    CompletarTareaService,
)
from modules.ejemplo_tareas.application.services.crear_tarea import CrearTareaService
from modules.ejemplo_tareas.application.services.listar_tareas import ListarTareasService
from modules.ejemplo_tareas.application.services.obtener_tarea import ObtenerTareaService
from modules.ejemplo_tareas.infrastructure.api.dependencies import (
    get_completar_tarea_service,
    get_crear_tarea_service,
    get_listar_tareas_input,
    get_listar_tareas_service,
    get_obtener_tarea_service,
)
from modules.ejemplo_tareas.infrastructure.api.schemas import (
    CrearTareaRequest,
    TareaResponse,
    TareasPaginadasResponse,
)

router = APIRouter(
    prefix="/api/ejemplo/tareas",
    tags=["Ejemplo Tareas"],
)


# Rutas de coleccion


@router.post(
    "",
    response_model=TareaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crea una tarea de ejemplo",
    responses={
        422: {"description": "Titulo vacio o invalido"},
    },
)
async def crear_tarea(
    payload: CrearTareaRequest,
    service: Annotated[CrearTareaService, Depends(get_crear_tarea_service)],
):
    entrada = CrearTareaInput(**payload.model_dump())
    tarea = await service.ejecutar(entrada)
    return TareaResponse.model_validate(tarea.model_dump())


@router.get(
    "",
    response_model=TareasPaginadasResponse,
    summary="Lista tareas de ejemplo paginadas",
)
async def listar_tareas(
    entrada: Annotated[ListarTareasInput, Depends(get_listar_tareas_input)],
    service: Annotated[ListarTareasService, Depends(get_listar_tareas_service)],
):
    resultado = await service.ejecutar(entrada)
    return TareasPaginadasResponse(
        resultado=[
            TareaResponse.model_validate(tarea.model_dump())
            for tarea in resultado.resultado
        ],
        pagina_actual=resultado.pagina_actual,
        elementos_por_pagina=resultado.elementos_por_pagina,
        total_elementos=resultado.total_elementos,
        total_paginas=resultado.total_paginas,
    )


# Rutas de recurso


@router.get(
    "/{tarea_id}",
    response_model=TareaResponse,
    summary="Obtiene una tarea de ejemplo por ID",
    responses={
        404: {"description": "Tarea no encontrada"},
    },
)
async def obtener_tarea(
    tarea_id: str,
    service: Annotated[ObtenerTareaService, Depends(get_obtener_tarea_service)],
):
    tarea = await service.ejecutar(tarea_id)
    return TareaResponse.model_validate(tarea.model_dump())


# Acciones de negocio


@router.patch(
    "/{tarea_id}/completar",
    response_model=TareaResponse,
    summary="Marca una tarea como completada",
    responses={
        404: {"description": "Tarea no encontrada"},
        409: {"description": "La tarea ya estaba completada"},
    },
)
async def completar_tarea(
    tarea_id: str,
    service: Annotated[CompletarTareaService, Depends(get_completar_tarea_service)],
):
    tarea = await service.ejecutar(tarea_id)
    return TareaResponse.model_validate(tarea.model_dump())
