from modules.permisos.application.dto.cambio_permiso_dto import CambioPermisoDTO, cambio_a_dto
from modules.permisos.application.ports.permisos_repository import PermisosRolRepositoryPort
from modules.permisos.domain.reglas import validar_rol_existente


class ListarHistorialPermisosService:
    def __init__(self, permisos_repository: PermisosRolRepositoryPort):
        self._permisos_repository = permisos_repository

    async def ejecutar(self, rol: str | None, skip: int, limit: int) -> list[CambioPermisoDTO]:
        if rol is not None:
            validar_rol_existente(rol)

        cambios = await self._permisos_repository.listar_historial(rol, skip, limit)
        return [cambio_a_dto(cambio) for cambio in cambios]
