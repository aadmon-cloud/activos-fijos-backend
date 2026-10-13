from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from shared.domain.entities.audit import AuditPersona


class TipoMovimiento(str, Enum):
    PRESTAMO = "prestamo"
    SALIDA_EVENTO = "salida_evento"
    BAJA = "baja"


class SentidoPrestamo(str, Enum):
    """Quien monta el prestamo: `prestar` (entrega algo que tiene a su cargo) o `solicitar` (pide algo de otro)."""

    PRESTAR = "prestar"
    SOLICITAR = "solicitar"


class EstadoMovimiento(str, Enum):
    SOLICITADO = "solicitado"
    APROBADO_RESPONSABLE = "aprobado_responsable"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    EN_CURSO = "en_curso"
    DEVUELTO = "devuelto"
    EJECUTADO = "ejecutado"


class EstadoItemMovimiento(str, Enum):
    PENDIENTE_RESPONSABLE = "pendiente_responsable"
    PENDIENTE_ADMIN = "pendiente_admin"
    RECHAZADO = "rechazado"
    EN_CURSO = "en_curso"
    DEVOLUCION_SOLICITADA = "devolucion_solicitada"
    DEVUELTO = "devuelto"
    EJECUTADO = "ejecutado"


class EtapaRechazo(str, Enum):
    RESPONSABLE = "responsable"
    ADMINISTRACION = "administracion"


@dataclass(frozen=True, kw_only=True)
class ItemMovimiento:
    """Un activo dentro de un movimiento, con su propio recorrido (aprobaciones, salida y devolucion)."""

    activo_id: str

    # Responsable del activo cuando se pidio el movimiento: a quien vuelve al devolverse.
    responsable_original_id: str | None
    estado: EstadoItemMovimiento
    aprobado_por_responsable: AuditPersona | None = None
    rechazado_por: AuditPersona | None = None
    etapa_rechazo: EtapaRechazo | None = None
    motivo_rechazo: str | None = None
    devolucion_solicitada_por: AuditPersona | None = None
    recibido_por: AuditPersona | None = None
    fecha_devolucion_real: datetime | None = None

    # Hallazgo al recibirlo de vuelta; queda ademas como nota en el historial del activo.
    novedad_devolucion: str | None = None


@dataclass(frozen=True, kw_only=True)
class Movimiento:
    id: str | None
    tipo: TipoMovimiento
    items: list[ItemMovimiento]
    usuario_destino_id: str | None
    descripcion: str
    evento_nombre: str | None
    fecha_salida_estimada: datetime | None
    fecha_retorno_estimada: datetime | None
    fecha_entrega_real: datetime | None
    fecha_devolucion_real: datetime | None
    estado: EstadoMovimiento
    aprobado_por_admin: AuditPersona | None
    comprobante_archivo_id: str | None
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None
    sentido: SentidoPrestamo | None = None

    # Para recordar la devolucion una sola vez.
    recordatorio_devolucion_enviado: bool = False

    @property
    def activo_ids(self) -> list[str]:
        return [item.activo_id for item in self.items]

    def item(self, activo_id: str) -> ItemMovimiento | None:
        return next((item for item in self.items if item.activo_id == activo_id), None)


# Estados de un item que ocupan el activo: mientras esten asi, el activo no puede entrar a otro movimiento.
ESTADOS_ITEM_ACTIVOS = frozenset(
    {
        EstadoItemMovimiento.PENDIENTE_RESPONSABLE,
        EstadoItemMovimiento.PENDIENTE_ADMIN,
        EstadoItemMovimiento.EN_CURSO,
        EstadoItemMovimiento.DEVOLUCION_SOLICITADA,
    }
)
