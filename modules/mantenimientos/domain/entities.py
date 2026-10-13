from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from shared.domain.entities.audit import AuditPersona


class TipoMantenimiento(str, Enum):
    PREVENTIVO = "preventivo"
    CORRECTIVO = "correctivo"
    LOCATIVO = "locativo"


class EstadoMantenimiento(str, Enum):
    PROGRAMADO = "programado"
    EN_PROCESO = "en_proceso"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"


@dataclass(frozen=True, kw_only=True)
class ArchivoMantenimiento:
    archivo_id: str
    nombre: str


@dataclass(frozen=True, kw_only=True)
class Mantenimiento:
    id: str | None
    activo_id: str
    solicitud_id: str | None
    tipo: TipoMantenimiento
    tecnico_responsable_id: str
    fecha: datetime
    observaciones: str | None
    costo: Decimal | None
    documentos: list[ArchivoMantenimiento]
    evidencias: list[ArchivoMantenimiento]
    estado: EstadoMantenimiento
    frecuencia_dias: int | None
    proxima_fecha_sugerida: datetime | None
    alerta_enviada: bool
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None
