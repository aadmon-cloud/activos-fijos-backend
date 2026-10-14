from modules.permisos.application.dto.actualizar_permisos_rol_dto import (
    ActualizarPermisosRolDTO,
    RestablecerPermisosRolDTO,
)
from modules.permisos.application.dto.matriz_dto import RolMatrizDTO
from modules.permisos.application.services.actualizar_permisos_rol import ActualizarPermisosRolService
from modules.permisos.domain.reglas import validar_rol_editable
from shared.domain.permisos import permisos_por_defecto


class RestablecerPermisosRolService:
    """Devuelve un rol a la matriz de fabrica (la que tenia antes de existir la administracion de permisos)."""

    def __init__(self, actualizar_service: ActualizarPermisosRolService):
        self._actualizar_service = actualizar_service

    async def ejecutar(self, dto: RestablecerPermisosRolDTO) -> RolMatrizDTO:
        validar_rol_editable(dto.rol)

        return await self._actualizar_service.ejecutar(
            ActualizarPermisosRolDTO(
                rol=dto.rol,
                permisos=sorted(permisos_por_defecto(dto.rol)),
                actor_id=dto.actor_id,
                actor_nombre=dto.actor_nombre,
            )
        )
