from typing import Annotated

from fastapi import APIRouter, Depends, status

from modules.catalogos.application.dto.actualizar_sede_dto import ActualizarSedeDTO
from modules.catalogos.application.dto.crear_sede_dto import CrearSedeDTO
from modules.catalogos.application.services.actualizar_sede import ActualizarSedeService
from modules.catalogos.application.services.crear_sede import CrearSedeService
from modules.catalogos.application.services.eliminar_sede import EliminarSedeService
from modules.catalogos.application.services.listar_sedes import ListarSedesService
from modules.catalogos.application.services.obtener_sede import ObtenerSedeService
from modules.catalogos.infrastructure.api.dependencies import (
    get_actualizar_sede_service,
    get_crear_sede_service,
    get_eliminar_sede_service,
    get_listar_sedes_service,
    get_obtener_sede_service,
)
from modules.catalogos.infrastructure.api.schemas import (
    ActualizarSedeRequest,
    CrearSedeRequest,
    SedeResponse,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_rol,
    requiere_usuario_autenticado,
)

_ROL_ADMINISTRADOR_GENERAL = "administrador_general"

router = APIRouter(prefix="/api/sedes", tags=["sedes"])

_requiere_administrador_general = requiere_rol(_ROL_ADMINISTRADOR_GENERAL)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva sede",
    responses={409: {"description": "Ya existe una sede con ese nombre"}},
)
async def crear_sede(
    body: CrearSedeRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[CrearSedeService, Depends(get_crear_sede_service)],
):
    sede = await service.ejecutar(
        CrearSedeDTO(
            nombre=body.nombre,
            descripcion=body.descripcion,
            creado_por_id=identidad.id_usuario,
            creado_por_nombre=identidad.nombre,
        )
    )
    return {
        "status": "success",
        "message": "Sede creada exitosamente.",
        "data": {"id": sede.id},
    }


@router.get(
    "",
    summary="Lista las sedes existentes",
)
async def listar_sedes(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ListarSedesService, Depends(get_listar_sedes_service)],
):
    sedes = await service.ejecutar()
    return {
        "status": "success",
        "data": [SedeResponse(**sede.__dict__).model_dump() for sede in sedes],
    }


@router.get(
    "/{id_sede}",
    summary="Obtiene una sede por id",
    responses={404: {"description": "La sede no existe"}},
)
async def obtener_sede(
    id_sede: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ObtenerSedeService, Depends(get_obtener_sede_service)],
):
    sede = await service.ejecutar(id_sede)
    return {"status": "success", "data": SedeResponse(**sede.__dict__).model_dump()}


@router.put(
    "/{id_sede}",
    summary="Actualiza los datos de una sede",
    responses={
        404: {"description": "La sede no existe"},
        409: {"description": "Ya existe una sede con ese nombre"},
    },
)
async def actualizar_sede(
    id_sede: str,
    body: ActualizarSedeRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[ActualizarSedeService, Depends(get_actualizar_sede_service)],
):
    sede = await service.ejecutar(
        ActualizarSedeDTO(
            id_sede=id_sede,
            nombre=body.nombre,
            descripcion=body.descripcion,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "data": SedeResponse(**sede.__dict__).model_dump()}


@router.delete(
    "/{id_sede}",
    summary="Elimina una sede",
    responses={
        404: {"description": "La sede no existe"},
        409: {"description": "La sede tiene lugares asociados"},
    },
)
async def eliminar_sede(
    id_sede: str,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[EliminarSedeService, Depends(get_eliminar_sede_service)],
):
    await service.ejecutar(id_sede)
    return {"status": "success", "message": "Sede eliminada exitosamente."}
