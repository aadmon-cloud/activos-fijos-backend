from dataclasses import dataclass, field
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


class ResultadoChequeo(str, Enum):
    """Como se encontro un activo al chequearlo en la salida o en el ingreso."""

    ENCONTRADO = "encontrado"
    CON_NOVEDAD = "con_novedad"
    NO_ENCONTRADO = "no_encontrado"


class TipoActa(str, Enum):
    SALIDA = "salida"
    INGRESO = "ingreso"


@dataclass(frozen=True, kw_only=True)
class ChequeoItem:
    """Resultado del chequeo de un activo; se guarda al marcarlo y se puede corregir hasta cerrar el chequeo."""

    resultado: ResultadoChequeo
    observacion: str | None
    por: AuditPersona


@dataclass(frozen=True, kw_only=True)
class SelloActa:
    """Quien firma un acta: nombre y correo (sin documento de identidad) y cuando."""

    id_persona: str
    nombre: str
    correo: str
    fecha: datetime


@dataclass(frozen=True, kw_only=True)
class LineaActa:
    """Un activo tal como quedo en el acta (con el resultado de su chequeo)."""

    activo_id: str
    resultado: ResultadoChequeo
    observacion: str | None = None


@dataclass(frozen=True, kw_only=True)
class ActaMovimiento:
    """Constancia de una salida o de un ingreso: la cierra administracion y la acepta quien retira o devuelve.

    Con los dos sellos puestos el acta queda completa; mientras falte el del responsable esta pendiente."""

    id: str
    tipo: TipoActa

    # Consecutivo dentro del movimiento y del tipo (acta de salida 1, 2...).
    numero: int
    lineas: list[LineaActa]
    cerrada_por: SelloActa
    archivo_id: str | None = None
    aceptada_por: SelloActa | None = None


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

    # Chequeo guardado de la fase en curso (salida o ingreso); se limpia al cerrarla si el activo sigue pendiente.
    chequeo_salida: ChequeoItem | None = None
    chequeo_ingreso: ChequeoItem | None = None


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

    # Actas de salida y de ingreso, en el orden en que se cerraron.
    actas: list[ActaMovimiento] = field(default_factory=list)

    @property
    def activo_ids(self) -> list[str]:
        return [item.activo_id for item in self.items]

    def acta(self, acta_id: str) -> ActaMovimiento | None:
        return next((acta for acta in self.actas if acta.id == acta_id), None)

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
