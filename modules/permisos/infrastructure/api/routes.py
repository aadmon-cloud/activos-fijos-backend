from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from modules.permisos.application.dto.actualizar_permisos_rol_dto import (
    ActualizarPermisosRolDTO,
    RestablecerPermisosRolDTO,
)
from modules.permisos.application.services.actualizar_permisos_rol import ActualizarPermisosRolService
from modules.permisos.application.services.listar_historial import ListarHistorialPermisosService
from modules.permisos.application.services.obtener_matriz import ObtenerMatrizPermisosService
from modules.permisos.application.services.restablecer_permisos_rol import RestablecerPermisosRolService
from modules.permisos.infrastructure.api.dependencies import (
    get_actualizar_permisos_rol_service,
    get_listar_historial_service,
    get_obtener_matriz_service,
    get_restablecer_permisos_rol_service,
)
from modules.permisos.infrastructure.api.schemas import (
    ActualizarPermisosRolRequest,
    CambioPermisoResponse,
    MatrizResponse,
    RolMatrizResponse,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import requiere_super_administrador

router = APIRouter(prefix="/api/permisos", tags=["permisos"])


@router.get(
    "/matriz",
    summary="Catalogo de funciones y las que tiene habilitadas cada rol",
    responses={403: {"description": "Solo el Super administrador"}},
)
async def obtener_matriz(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_super_administrador)],
    service: Annotated[ObtenerMatrizPermisosService, Depends(get_obtener_matriz_service)],
):
    matriz = await service.ejecutar()
    return {"status": "success", "data": MatrizResponse(**asdict(matriz)).model_dump()}


@router.put(
    "/roles/{rol}",
    summary="Deja las funciones habilitadas de un rol exactamente como se piden",
    responses={
        400: {"description": "Una funcion no existe"},
        403: {"description": "Solo el Super administrador"},
        404: {"description": "El rol no existe"},
        422: {"description": "El rol no es editable o se intento quitar una funcion basica"},
    },
)
async def actualizar_permisos_rol(
    rol: str,
    body: ActualizarPermisosRolRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_super_administrador)],
    service: Annotated[ActualizarPermisosRolService, Depends(get_actualizar_permisos_rol_service)],
):
    resultado = await service.ejecutar(
        ActualizarPermisosRolDTO(
            rol=rol,
            permisos=body.permisos,
            actor_id=identidad.id_usuario,
            actor_nombre=identidad.nombre,
        )
    )
    return {
        "status": "success",
        "message": "Permisos actualizados exitosamente.",
        "data": RolMatrizResponse(**asdict(resultado)).model_dump(),
    }


@router.post(
    "/roles/{rol}/restablecer",
    summary="Devuelve un rol a las funciones de fabrica",
    responses={
        403: {"description": "Solo el Super administrador"},
        404: {"description": "El rol no existe"},
        422: {"description": "El rol no es editable"},
    },
)
async def restablecer_permisos_rol(
    rol: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_super_administrador)],
    service: Annotated[RestablecerPermisosRolService, Depends(get_restablecer_permisos_rol_service)],
):
    resultado = await service.ejecutar(
        RestablecerPermisosRolDTO(rol=rol, actor_id=identidad.id_usuario, actor_nombre=identidad.nombre)
    )
    return {
        "status": "success",
        "message": "Permisos restablecidos a los valores de fabrica.",
        "data": RolMatrizResponse(**asdict(resultado)).model_dump(),
    }


@router.get(
    "/historial",
    summary="Historial de cambios de la matriz (del mas reciente al mas antiguo)",
    responses={403: {"description": "Solo el Super administrador"}, 404: {"description": "El rol no existe"}},
)
async def listar_historial(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_super_administrador)],
    service: Annotated[ListarHistorialPermisosService, Depends(get_listar_historial_service)],
    rol: str | None = Query(default=None, max_length=50),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    cambios = await service.ejecutar(rol=rol, skip=skip, limit=limit)
    return {
        "status": "success",
        "data": [CambioPermisoResponse(**asdict(cambio)).model_dump() for cambio in cambios],
    }
