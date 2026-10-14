from typing import Annotated

from fastapi import APIRouter, Depends, status

from modules.catalogos.application.dto.actualizar_area_dto import ActualizarAreaDTO
from modules.catalogos.application.dto.crear_area_dto import CrearAreaDTO
from modules.catalogos.application.services.actualizar_area import ActualizarAreaService
from modules.catalogos.application.services.crear_area import CrearAreaService
from modules.catalogos.application.services.eliminar_area import EliminarAreaService
from modules.catalogos.application.services.listar_areas import ListarAreasService
from modules.catalogos.application.services.obtener_area import ObtenerAreaService
from modules.catalogos.infrastructure.api.dependencies import (
    get_actualizar_area_service,
    get_crear_area_service,
    get_eliminar_area_service,
    get_listar_areas_service,
    get_obtener_area_service,
)
from modules.catalogos.infrastructure.api.schemas import (
    ActualizarAreaRequest,
    AreaResponse,
    CrearAreaRequest,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_permiso,
    requiere_usuario_autenticado,
)


router = APIRouter(prefix="/api/areas", tags=["areas"])

_requiere_catalogos_crear = requiere_permiso("catalogos-crear")
_requiere_catalogos_editar = requiere_permiso("catalogos-editar")
_requiere_catalogos_eliminar = requiere_permiso("catalogos-eliminar")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva area",
    responses={409: {"description": "Ya existe un area con ese nombre"}},
)
async def crear_area(
    body: CrearAreaRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_catalogos_crear)
    ],
    service: Annotated[CrearAreaService, Depends(get_crear_area_service)],
):
    area = await service.ejecutar(
        CrearAreaDTO(
            nombre=body.nombre,
            descripcion=body.descripcion,
            creado_por_id=identidad.id_usuario,
            creado_por_nombre=identidad.nombre,
        )
    )
    return {
        "status": "success",
        "message": "Area creada exitosamente.",
        "data": {"id": area.id},
    }


@router.get(
    "",
    summary="Lista las areas existentes",
)
async def listar_areas(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ListarAreasService, Depends(get_listar_areas_service)],
):
    areas = await service.ejecutar()
    return {
        "status": "success",
        "data": [AreaResponse(**area.__dict__).model_dump() for area in areas],
    }


@router.get(
    "/{id_area}",
    summary="Obtiene un area por id",
    responses={404: {"description": "El area no existe"}},
)
async def obtener_area(
    id_area: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ObtenerAreaService, Depends(get_obtener_area_service)],
):
    area = await service.ejecutar(id_area)
    return {"status": "success", "data": AreaResponse(**area.__dict__).model_dump()}


@router.put(
    "/{id_area}",
    summary="Actualiza los datos de un area",
    responses={
        404: {"description": "El area no existe"},
        409: {"description": "Ya existe un area con ese nombre"},
    },
)
async def actualizar_area(
    id_area: str,
    body: ActualizarAreaRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_catalogos_editar)
    ],
    service: Annotated[ActualizarAreaService, Depends(get_actualizar_area_service)],
):
    area = await service.ejecutar(
        ActualizarAreaDTO(
            id_area=id_area,
            nombre=body.nombre,
            descripcion=body.descripcion,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "data": AreaResponse(**area.__dict__).model_dump()}


@router.delete(
    "/{id_area}",
    summary="Elimina un area",
    responses={404: {"description": "El area no existe"}},
)
async def eliminar_area(
    id_area: str,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_catalogos_eliminar)
    ],
    service: Annotated[EliminarAreaService, Depends(get_eliminar_area_service)],
):
    await service.ejecutar(id_area)
    return {"status": "success", "message": "Area eliminada exitosamente."}
