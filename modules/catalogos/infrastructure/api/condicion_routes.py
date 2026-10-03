from typing import Annotated

from fastapi import APIRouter, Depends, status

from modules.catalogos.application.dto.actualizar_condicion_dto import ActualizarCondicionDTO
from modules.catalogos.application.dto.crear_condicion_dto import CrearCondicionDTO
from modules.catalogos.application.services.actualizar_condicion import (
    ActualizarCondicionService,
)
from modules.catalogos.application.services.crear_condicion import CrearCondicionService
from modules.catalogos.application.services.eliminar_condicion import EliminarCondicionService
from modules.catalogos.application.services.listar_condiciones import ListarCondicionesService
from modules.catalogos.application.services.obtener_condicion import ObtenerCondicionService
from modules.catalogos.infrastructure.api.dependencies import (
    get_actualizar_condicion_service,
    get_crear_condicion_service,
    get_eliminar_condicion_service,
    get_listar_condiciones_service,
    get_obtener_condicion_service,
)
from modules.catalogos.infrastructure.api.schemas import (
    ActualizarCondicionRequest,
    CondicionResponse,
    CrearCondicionRequest,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_rol,
    requiere_usuario_autenticado,
)

_ROL_ADMINISTRADOR_GENERAL = "administrador_general"

router = APIRouter(prefix="/api/condiciones", tags=["condiciones"])

_requiere_administrador_general = requiere_rol(_ROL_ADMINISTRADOR_GENERAL)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva condicion",
    responses={
        409: {"description": "Ya existe una condicion con ese nombre"},
        422: {"description": "El color no tiene un formato hexadecimal valido"},
    },
)
async def crear_condicion(
    body: CrearCondicionRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[CrearCondicionService, Depends(get_crear_condicion_service)],
):
    condicion = await service.ejecutar(
        CrearCondicionDTO(
            nombre=body.nombre,
            color=body.color,
            descripcion=body.descripcion,
            creado_por_id=identidad.id_usuario,
            creado_por_nombre=identidad.nombre,
        )
    )
    return {
        "status": "success",
        "message": "Condicion creada exitosamente.",
        "data": {"id": condicion.id},
    }


@router.get(
    "",
    summary="Lista las condiciones existentes",
)
async def listar_condiciones(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ListarCondicionesService, Depends(get_listar_condiciones_service)],
):
    condiciones = await service.ejecutar()
    return {
        "status": "success",
        "data": [
            CondicionResponse(**condicion.__dict__).model_dump() for condicion in condiciones
        ],
    }


@router.get(
    "/{id_condicion}",
    summary="Obtiene una condicion por id",
    responses={404: {"description": "La condicion no existe"}},
)
async def obtener_condicion(
    id_condicion: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ObtenerCondicionService, Depends(get_obtener_condicion_service)],
):
    condicion = await service.ejecutar(id_condicion)
    return {"status": "success", "data": CondicionResponse(**condicion.__dict__).model_dump()}


@router.put(
    "/{id_condicion}",
    summary="Actualiza los datos de una condicion",
    responses={
        404: {"description": "La condicion no existe"},
        409: {"description": "Ya existe una condicion con ese nombre"},
        422: {"description": "El color no tiene un formato hexadecimal valido"},
    },
)
async def actualizar_condicion(
    id_condicion: str,
    body: ActualizarCondicionRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[ActualizarCondicionService, Depends(get_actualizar_condicion_service)],
):
    condicion = await service.ejecutar(
        ActualizarCondicionDTO(
            id_condicion=id_condicion,
            nombre=body.nombre,
            color=body.color,
            descripcion=body.descripcion,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "data": CondicionResponse(**condicion.__dict__).model_dump()}


@router.delete(
    "/{id_condicion}",
    summary="Elimina una condicion",
    responses={404: {"description": "La condicion no existe"}},
)
async def eliminar_condicion(
    id_condicion: str,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[EliminarCondicionService, Depends(get_eliminar_condicion_service)],
):
    await service.ejecutar(id_condicion)
    return {"status": "success", "message": "Condicion eliminada exitosamente."}
