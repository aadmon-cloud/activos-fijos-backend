from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from shared.domain.entities.audit import AuditPersona


class TipoActivo(str, Enum):
    ACTIVO_FIJO = "activo_fijo"
    ELEMENTO = "elemento"


class EstadoCicloVida(str, Enum):
    DISPONIBLE = "disponible"
    PRESTADO = "prestado"
    EN_MANTENIMIENTO = "en_mantenimiento"
    DADO_DE_BAJA = "dado_de_baja"
    PERDIDO = "perdido"
    DANADO = "danado"


@dataclass(frozen=True, kw_only=True)
class Complemento:
    nombre: str
    descripcion: str | None
    cantidad: int
    serie: str | None


@dataclass(frozen=True, kw_only=True)
class Activo:
    id: str | None
    nombre: str
    numero_inventario: str
    tipo: TipoActivo
    marca: str | None
    modelo: str | None
    serie: str | None
    descripcion: str | None
    categoria_id: str
    area_id: str
    responsable_id: str
    condicion_id: str
    estado_ciclo_vida: EstadoCicloVida
    sede_id: str
    lugar_id: str
    valor: Decimal
    fecha_adquisicion: datetime
    complementos: list[Complemento]
    observaciones: str | None
    foto_url: str | None
    ficha_tecnica_url: str | None
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None


@dataclass(frozen=True, kw_only=True)
class EntradaHistorialActivo:
    id: str | None
    activo_id: str
    campo: str
    valor_anterior: str
    valor_nuevo: str
    modificado_por: AuditPersona
