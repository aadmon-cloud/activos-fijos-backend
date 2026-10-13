from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from shared.domain.entities.audit import AuditPersona


class EstadoAuditoria(str, Enum):
    EN_PROGRESO = "en_progreso"
    FINALIZADA = "finalizada"
    NOTIFICADA = "notificada"
    ERROR_NOTIFICACION = "error_notificacion"


class ResultadoVerificacion(str, Enum):
    ENCONTRADO = "encontrado"
    ENCONTRADO_CON_NOVEDAD = "encontrado_con_novedad"
    NO_ENCONTRADO = "no_encontrado"


@dataclass(frozen=True, kw_only=True)
class ItemAuditoria:
    """Fotografia de un activo/elemento al momento de iniciar la auditoria: los campos
    descriptivos quedan congelados aqui, independientes de lo que le pase despues al activo."""

    activo_id: str
    nombre: str
    numero_inventario: str
    tipo: str
    descripcion: str | None
    serie: str | None
    estado_ciclo_vida_al_inicio: str
    resultado: ResultadoVerificacion | None
    observacion: str | None
    verificado_en: datetime | None


@dataclass(frozen=True, kw_only=True)
class Auditoria:
    id: str | None
    usuario_auditado_id: str
    estado: EstadoAuditoria
    items: list[ItemAuditoria]
    fecha_cierre: datetime | None
    pdf_archivo_id: str | None
    detalle_error_notificacion: str | None
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None
