from functools import lru_cache

from modules.permisos.application.ports.permisos_repository import PermisosRolRepositoryPort
from modules.permisos.application.services.actualizar_permisos_rol import ActualizarPermisosRolService
from modules.permisos.application.services.asegurar_permisos_por_defecto import (
    AsegurarPermisosPorDefectoService,
)
from modules.permisos.application.services.listar_historial import ListarHistorialPermisosService
from modules.permisos.application.services.obtener_matriz import ObtenerMatrizPermisosService
from modules.permisos.application.services.restablecer_permisos_rol import RestablecerPermisosRolService
from modules.permisos.infrastructure.persistence.mongo.permisos_repository import (
    MongoPermisosRolRepository,
)


@lru_cache(maxsize=1)
def get_permisos_repository() -> PermisosRolRepositoryPort:
    return MongoPermisosRolRepository()


def get_obtener_matriz_service() -> ObtenerMatrizPermisosService:
    return ObtenerMatrizPermisosService(permisos_repository=get_permisos_repository())


def get_actualizar_permisos_rol_service() -> ActualizarPermisosRolService:
    return ActualizarPermisosRolService(permisos_repository=get_permisos_repository())


def get_restablecer_permisos_rol_service() -> RestablecerPermisosRolService:
    return RestablecerPermisosRolService(actualizar_service=get_actualizar_permisos_rol_service())


def get_listar_historial_service() -> ListarHistorialPermisosService:
    return ListarHistorialPermisosService(permisos_repository=get_permisos_repository())


def get_asegurar_permisos_por_defecto_service() -> AsegurarPermisosPorDefectoService:
    return AsegurarPermisosPorDefectoService(permisos_repository=get_permisos_repository())
