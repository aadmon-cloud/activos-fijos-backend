from dataclasses import dataclass
from enum import Enum

from shared.domain.entities.audit import AuditPersona


class AccionPermiso(str, Enum):
    HABILITADO = "habilitado"
    DESHABILITADO = "deshabilitado"


@dataclass(frozen=True, kw_only=True)
class PermisosRol:
    """Funciones habilitadas para un rol. Hay un documento por rol editable."""

    id: str | None
    rol: str
    permisos: tuple[str, ...]
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None


@dataclass(frozen=True, kw_only=True)
class CambioPermiso:
    """Una funcion que se habilito o deshabilito para un rol. Es el historial de la matriz."""

    id: str | None
    rol: str
    permiso: str
    accion: AccionPermiso
    por: AuditPersona
