from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from modules.catalogos.application.dto.actualizar_lugar_dto import ActualizarLugarDTO
from modules.catalogos.application.dto.crear_lugar_dto import CrearLugarDTO
from modules.catalogos.application.dto.listar_lugares_dto import ListarLugaresDTO
from modules.catalogos.application.services.actualizar_lugar import ActualizarLugarService
from modules.catalogos.application.services.crear_lugar import CrearLugarService
from modules.catalogos.application.services.eliminar_lugar import EliminarLugarService
from modules.catalogos.application.services.listar_lugares import ListarLugaresService
from modules.catalogos.application.services.obtener_lugar import ObtenerLugarService
from modules.catalogos.infrastructure.api.dependencies import (
    get_actualizar_lugar_service,
    get_crear_lugar_service,
    get_eliminar_lugar_service,
    get_listar_lugares_service,
    get_obtener_lugar_service,
)
from modules.catalogos.infrastructure.api.schemas import (
    ActualizarLugarRequest,
    CrearLugarRequest,
    LugarResponse,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_permiso,
    requiere_usuario_autenticado,
)


router = APIRouter(prefix="/api/lugares", tags=["lugares"])

_requiere_catalogos_crear = requiere_permiso("catalogos-crear")
_requiere_catalogos_editar = requiere_permiso("catalogos-editar")
_requiere_catalogos_eliminar = requiere_permiso("catalogos-eliminar")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crea un nuevo lugar",
    responses={
        404: {"description": "La sede no existe"},
        409: {"description": "Ya existe un lugar con ese nombre en esa sede"},
    },
)
async def crear_lugar(
    body: CrearLugarRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_catalogos_crear)
    ],
    service: Annotated[CrearLugarService, Depends(get_crear_lugar_service)],
):
    lugar = await service.ejecutar(
        CrearLugarDTO(
            nombre=body.nombre,
            tipo=body.tipo,
            sede_id=body.sede_id,
            creado_por_id=identidad.id_usuario,
            creado_por_nombre=identidad.nombre,
        )
    )
    return {
        "status": "success",
        "message": "Lugar creado exitosamente.",
        "data": {"id": lugar.id},
    }


@router.get(
    "",
    summary="Lista los lugares existentes",
)
async def listar_lugares(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ListarLugaresService, Depends(get_listar_lugares_service)],
    sede_id: str | None = Query(default=None),
):
    lugares = await service.ejecutar(ListarLugaresDTO(sede_id=sede_id))
    return {
        "status": "success",
        "data": [LugarResponse(**lugar.__dict__).model_dump() for lugar in lugares],
    }


@router.get(
    "/{id_lugar}",
    summary="Obtiene un lugar por id",
    responses={404: {"description": "El lugar no existe"}},
)
async def obtener_lugar(
    id_lugar: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ObtenerLugarService, Depends(get_obtener_lugar_service)],
):
    lugar = await service.ejecutar(id_lugar)
    return {"status": "success", "data": LugarResponse(**lugar.__dict__).model_dump()}


@router.put(
    "/{id_lugar}",
    summary="Actualiza los datos de un lugar",
    responses={
        404: {"description": "El lugar no existe"},
        409: {"description": "Ya existe un lugar con ese nombre en esa sede"},
    },
)
async def actualizar_lugar(
    id_lugar: str,
    body: ActualizarLugarRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_catalogos_editar)
    ],
    service: Annotated[ActualizarLugarService, Depends(get_actualizar_lugar_service)],
):
    lugar = await service.ejecutar(
        ActualizarLugarDTO(
            id_lugar=id_lugar,
            nombre=body.nombre,
            tipo=body.tipo,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "data": LugarResponse(**lugar.__dict__).model_dump()}


@router.delete(
    "/{id_lugar}",
    summary="Elimina un lugar",
    responses={404: {"description": "El lugar no existe"}},
)
async def eliminar_lugar(
    id_lugar: str,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_catalogos_eliminar)
    ],
    service: Annotated[EliminarLugarService, Depends(get_eliminar_lugar_service)],
):
    await service.ejecutar(id_lugar)
    return {"status": "success", "message": "Lugar eliminado exitosamente."}
