from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from modules.solicitudes.application.dto.agregar_seguimiento_solicitud_dto import (
    AgregarSeguimientoSolicitudDTO,
)
from modules.solicitudes.application.dto.cambiar_estado_solicitud_dto import (
    CambiarEstadoSolicitudDTO,
)
from modules.solicitudes.application.dto.crear_solicitud_dto import CrearSolicitudDTO
from modules.solicitudes.application.dto.listar_solicitudes_dto import ListarSolicitudesDTO
from modules.solicitudes.application.dto.solicitud_dto import SolicitudDTO
from modules.solicitudes.application.services.agregar_seguimiento_solicitud import (
    AgregarSeguimientoSolicitudService,
)
from modules.solicitudes.application.services.cambiar_estado_solicitud import (
    CambiarEstadoSolicitudService,
)
from modules.solicitudes.application.services.crear_solicitud import CrearSolicitudService
from modules.solicitudes.application.services.listar_solicitudes import ListarSolicitudesService
from modules.solicitudes.application.services.obtener_solicitud import ObtenerSolicitudService
from modules.solicitudes.domain.entities import EstadoSolicitud, TipoSolicitud
from modules.solicitudes.infrastructure.api.dependencies import (
    get_agregar_seguimiento_solicitud_service,
    get_cambiar_estado_solicitud_service,
    get_crear_solicitud_service,
    get_listar_solicitudes_service,
    get_obtener_solicitud_service,
)
from modules.solicitudes.infrastructure.api.schemas import (
    AgregarSeguimientoSolicitudRequest,
    CambiarEstadoSolicitudRequest,
    CrearSolicitudRequest,
    EntradaSeguimientoResponse,
    SolicitudResponse,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_usuario_autenticado,
)

router = APIRouter(prefix="/api/solicitudes", tags=["solicitudes"])


def _a_response(solicitud: SolicitudDTO) -> SolicitudResponse:
    return SolicitudResponse(
        id=solicitud.id,
        tipo=solicitud.tipo,
        activo_id=solicitud.activo_id,
        descripcion=solicitud.descripcion,
        prioridad=solicitud.prioridad,
        evidencias=solicitud.evidencias,
        estado=solicitud.estado,
        rol_asignado=solicitud.rol_asignado,
        area_id=solicitud.area_id,
        seguimiento=[
            EntradaSeguimientoResponse(
                autor_nombre=e.autor_nombre,
                autor_fecha=e.autor_fecha,
                comentario=e.comentario,
                estado_anterior=e.estado_anterior,
                estado_nuevo=e.estado_nuevo,
            )
            for e in solicitud.seguimiento
        ],
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva solicitud",
    responses={
        403: {"description": "El usuario no es responsable del activo"},
        404: {"description": "El activo no existe"},
        422: {"description": "Datos de entrada invalidos"},
    },
)
async def crear_solicitud(
    body: CrearSolicitudRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[CrearSolicitudService, Depends(get_crear_solicitud_service)],
):
    solicitud = await service.ejecutar(
        CrearSolicitudDTO(
            tipo=body.tipo,
            activo_id=body.activo_id,
            descripcion=body.descripcion,
            prioridad=body.prioridad,
            evidencias=body.evidencias,
            creado_por_id=identidad.id_usuario,
            creado_por_nombre=identidad.nombre,
            creado_por_rol=identidad.rol,
        )
    )
    return {
        "status": "success",
        "message": "Solicitud creada exitosamente.",
        "data": {"id": solicitud.id},
    }


@router.get(
    "",
    summary="Lista las solicitudes existentes",
)
async def listar_solicitudes(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ListarSolicitudesService, Depends(get_listar_solicitudes_service)],
    tipo: TipoSolicitud | None = Query(default=None),
    estado: EstadoSolicitud | None = Query(default=None),
    activo_id: str | None = Query(default=None),
    rol_asignado: str | None = Query(default=None),
    area_id: str | None = Query(default=None),
    creado_por_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
):
    solicitudes = await service.ejecutar(
        ListarSolicitudesDTO(
            tipo=tipo,
            estado=estado,
            activo_id=activo_id,
            rol_asignado=rol_asignado,
            area_id=area_id,
            creado_por_id=creado_por_id,
            skip=skip,
            limit=limit,
        )
    )
    return {
        "status": "success",
        "data": [_a_response(solicitud).model_dump() for solicitud in solicitudes],
    }


@router.get(
    "/{id_solicitud}",
    summary="Obtiene una solicitud por id",
    responses={404: {"description": "La solicitud no existe"}},
)
async def obtener_solicitud(
    id_solicitud: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ObtenerSolicitudService, Depends(get_obtener_solicitud_service)],
):
    solicitud = await service.ejecutar(id_solicitud)
    return {"status": "success", "data": _a_response(solicitud).model_dump()}


@router.put(
    "/{id_solicitud}/estado",
    summary="Cambia el estado de una solicitud",
    responses={
        403: {"description": "El usuario no tiene permisos sobre esta solicitud"},
        404: {"description": "La solicitud no existe"},
        422: {"description": "La transicion de estado no es valida"},
    },
)
async def cambiar_estado_solicitud(
    id_solicitud: str,
    body: CambiarEstadoSolicitudRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[
        CambiarEstadoSolicitudService, Depends(get_cambiar_estado_solicitud_service)
    ],
):
    solicitud = await service.ejecutar(
        CambiarEstadoSolicitudDTO(
            id_solicitud=id_solicitud,
            estado_nuevo=body.estado_nuevo,
            comentario=body.comentario,
            actor_id=identidad.id_usuario,
            actor_nombre=identidad.nombre,
            actor_rol=identidad.rol,
            actor_area_id=identidad.area_id,
        )
    )
    return {"status": "success", "data": _a_response(solicitud).model_dump()}


@router.post(
    "/{id_solicitud}/seguimiento",
    status_code=status.HTTP_201_CREATED,
    summary="Agrega un comentario de seguimiento a una solicitud",
    responses={
        403: {"description": "El usuario no tiene permisos sobre esta solicitud"},
        404: {"description": "La solicitud no existe"},
    },
)
async def agregar_seguimiento_solicitud(
    id_solicitud: str,
    body: AgregarSeguimientoSolicitudRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[
        AgregarSeguimientoSolicitudService, Depends(get_agregar_seguimiento_solicitud_service)
    ],
):
    solicitud = await service.ejecutar(
        AgregarSeguimientoSolicitudDTO(
            id_solicitud=id_solicitud,
            comentario=body.comentario,
            actor_id=identidad.id_usuario,
            actor_nombre=identidad.nombre,
            actor_rol=identidad.rol,
            actor_area_id=identidad.area_id,
        )
    )
    return {"status": "success", "data": _a_response(solicitud).model_dump()}
