from dataclasses import dataclass
from enum import Enum

from shared.domain.entities.audit import AuditPersona


class TipoSolicitud(str, Enum):
    MANTENIMIENTO = "mantenimiento"
    CAMBIO = "cambio"
    AJUSTE = "ajuste"
    REPORTE_DANO = "reporte_dano"
    REPORTE_PERDIDA = "reporte_perdida"


class PrioridadSolicitud(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class EstadoSolicitud(str, Enum):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    RESUELTA = "resuelta"
    CERRADA = "cerrada"
    RECHAZADA = "rechazada"


@dataclass(frozen=True, kw_only=True)
class EntradaSeguimiento:
    autor: AuditPersona
    comentario: str
    estado_anterior: str | None
    estado_nuevo: str | None


@dataclass(frozen=True, kw_only=True)
class Solicitud:
    id: str | None
    tipo: TipoSolicitud
    activo_id: str
    descripcion: str
    prioridad: PrioridadSolicitud
    evidencias: list[str]
    estado: EstadoSolicitud
    rol_asignado: str | None
    area_id: str | None
    seguimiento: list[EntradaSeguimiento]
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None
