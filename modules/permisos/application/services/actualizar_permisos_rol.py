from datetime import UTC, datetime

from modules.permisos.application.dto.actualizar_permisos_rol_dto import ActualizarPermisosRolDTO
from modules.permisos.application.dto.matriz_dto import RolMatrizDTO
from modules.permisos.application.ports.permisos_repository import PermisosRolRepositoryPort
from modules.permisos.domain.entities import AccionPermiso, CambioPermiso, PermisosRol
from modules.permisos.domain.reglas import calcular_cambios, normalizar_permisos, validar_rol_editable
from shared.domain.entities.audit import AuditPersona
from shared.domain.permisos import permisos_por_defecto
from shared.domain.roles import ETIQUETAS_ROL


class ActualizarPermisosRolService:
    """Deja exactamente la lista pedida de funciones habilitadas para un rol y registra cada cambio."""

    def __init__(self, permisos_repository: PermisosRolRepositoryPort):
        self._permisos_repository = permisos_repository

    async def ejecutar(self, dto: ActualizarPermisosRolDTO) -> RolMatrizDTO:
        validar_rol_editable(dto.rol)
        nuevos = normalizar_permisos(dto.permisos)

        actual = await self._permisos_repository.obtener(dto.rol)
        antes = frozenset(actual.permisos) if actual else permisos_por_defecto(dto.rol)
        habilitadas, deshabilitadas = calcular_cambios(antes, nuevos)

        # Sin cambios no se escribe nada: ni el documento ni el historial.
        if actual is not None and not habilitadas and not deshabilitadas:
            return _a_dto(dto.rol, nuevos)

        autor = AuditPersona(id_persona=dto.actor_id, nombre=dto.actor_nombre, fecha=datetime.now(UTC))
        guardado = await self._permisos_repository.guardar(
            PermisosRol(
                id=actual.id if actual else None,
                rol=dto.rol,
                permisos=tuple(sorted(nuevos)),
                creado_por=actual.creado_por if actual else autor,
                actualizado_por=autor,
            )
        )

        cambios = [
            CambioPermiso(id=None, rol=dto.rol, permiso=permiso, accion=AccionPermiso.HABILITADO, por=autor)
            for permiso in habilitadas
        ] + [
            CambioPermiso(id=None, rol=dto.rol, permiso=permiso, accion=AccionPermiso.DESHABILITADO, por=autor)
            for permiso in deshabilitadas
        ]
        if cambios:
            await self._permisos_repository.registrar_cambios(cambios)

        return _a_dto(dto.rol, frozenset(guardado.permisos))


def _a_dto(rol: str, permisos: frozenset[str]) -> RolMatrizDTO:
    return RolMatrizDTO(rol=rol, etiqueta=ETIQUETAS_ROL[rol], editable=True, permisos=sorted(permisos))
