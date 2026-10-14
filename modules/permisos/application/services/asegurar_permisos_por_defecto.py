from datetime import UTC, datetime

from modules.permisos.application.ports.permisos_repository import PermisosRolRepositoryPort
from modules.permisos.domain.entities import PermisosRol
from shared.domain.entities.audit import AuditPersona
from shared.domain.permisos import permisos_por_defecto
from shared.domain.roles import ROLES_EDITABLES

_ID_SISTEMA = "sistema-permisos"
_NOMBRE_SISTEMA = "Carga inicial de permisos"


class AsegurarPermisosPorDefectoService:
    """Crea la matriz de fabrica de los roles que aun no tienen documento. Nunca pisa lo que ya se edito."""

    def __init__(self, permisos_repository: PermisosRolRepositoryPort):
        self._permisos_repository = permisos_repository

    async def ejecutar(self) -> list[str]:
        """Devuelve los roles que se crearon."""
        creados: list[str] = []

        for rol in ROLES_EDITABLES:
            if await self._permisos_repository.obtener(rol) is not None:
                continue

            await self._permisos_repository.guardar(
                PermisosRol(
                    id=None,
                    rol=rol,
                    permisos=tuple(sorted(permisos_por_defecto(rol))),
                    creado_por=AuditPersona(
                        id_persona=_ID_SISTEMA, nombre=_NOMBRE_SISTEMA, fecha=datetime.now(UTC)
                    ),
                    actualizado_por=None,
                )
            )
            creados.append(rol)

        return creados
