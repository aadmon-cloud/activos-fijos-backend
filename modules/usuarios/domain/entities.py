from dataclasses import dataclass
from enum import Enum

from shared.domain.entities.audit import AuditPersona


class RolUsuario(str, Enum):
    SUPER_ADMINISTRADOR = "super_administrador"
    ADMINISTRADOR_GENERAL = "administrador_general"
    TECNOLOGIA = "tecnologia"
    MANTENIMIENTO = "mantenimiento"
    ADMINISTRATIVO = "administrativo"
    JEFE_AREA = "jefe_area"
    EMPLEADO = "empleado"


@dataclass(frozen=True, kw_only=True)
class Usuario:
    id: str | None
    email: str
    nombre: str
    apellido: str
    password_hash: str
    rol: RolUsuario
    area_id: str | None
    telefono: str | None
    identificacion: str | None
    activo: bool
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None
