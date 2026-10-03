from dataclasses import dataclass
from enum import Enum

from shared.domain.entities.audit import AuditPersona


@dataclass(frozen=True, kw_only=True)
class Area:
    id: str | None
    nombre: str
    descripcion: str | None
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None


@dataclass(frozen=True, kw_only=True)
class Categoria:
    id: str | None
    nombre: str
    descripcion: str | None
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None


@dataclass(frozen=True, kw_only=True)
class Condicion:
    id: str | None
    nombre: str
    color: str
    descripcion: str | None
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None


@dataclass(frozen=True, kw_only=True)
class Sede:
    id: str | None
    nombre: str
    descripcion: str | None
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None


class TipoLugar(str, Enum):
    BODEGA = "bodega"
    BANO = "bano"
    ESPACIO_COMUN = "espacio_comun"
    OFICINA = "oficina"
    EXTERIOR = "exterior"


@dataclass(frozen=True, kw_only=True)
class Lugar:
    id: str | None
    nombre: str
    tipo: TipoLugar
    sede_id: str
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None
