from datetime import datetime

from pydantic import BaseModel, Field

from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    EtapaRechazo,
    SentidoPrestamo,
    TipoMovimiento,
)

# Tope de activos por movimiento: evita solicitudes desmedidas (OWASP A04).
_MAXIMO_ACTIVOS = 200
_MAXIMO_TEXTO = 1000


class SolicitarMovimientoRequest(BaseModel):
    tipo: TipoMovimiento
    activo_ids: list[str] = Field(max_length=_MAXIMO_ACTIVOS)
    descripcion: str = Field(max_length=_MAXIMO_TEXTO)
    sentido: SentidoPrestamo | None = None
    usuario_destino_id: str | None = None
    evento_nombre: str | None = Field(default=None, max_length=200)
    fecha_salida_estimada: datetime | None = None
    fecha_retorno_estimada: datetime | None = None


class AccionSobreActivosRequest(BaseModel):
    """Sobre que activos del movimiento se actua; sin lista, sobre todos los que el usuario pueda."""

    activo_ids: list[str] | None = Field(default=None, max_length=_MAXIMO_ACTIVOS)


class RechazarMovimientoRequest(AccionSobreActivosRequest):
    motivo_rechazo: str = Field(max_length=_MAXIMO_TEXTO)


class ConfirmarSalidaRequest(AccionSobreActivosRequest):
    motivo_no_incluidos: str | None = Field(default=None, max_length=_MAXIMO_TEXTO)


class ReciboActivoRequest(BaseModel):
    activo_id: str
    con_novedad: bool = False
    observacion: str | None = Field(default=None, max_length=_MAXIMO_TEXTO)


class ConfirmarDevolucionRequest(BaseModel):
    """Como se recibe cada activo; sin lista, se reciben todos los que estan fuera, sin novedad."""

    recibos: list[ReciboActivoRequest] | None = Field(default=None, max_length=_MAXIMO_ACTIVOS)


class ItemMovimientoResponse(BaseModel):
    activo_id: str
    estado: EstadoItemMovimiento
    responsable_original_id: str | None
    aprobado_por_responsable_nombre: str | None
    aprobado_por_responsable_fecha: datetime | None
    rechazado_por_nombre: str | None
    etapa_rechazo: EtapaRechazo | None
    motivo_rechazo: str | None
    devolucion_solicitada_por_nombre: str | None
    recibido_por_nombre: str | None
    fecha_devolucion_real: datetime | None
    novedad_devolucion: str | None

    # Solo en el listado y el detalle.
    activo_nombre: str | None = None
    activo_numero_inventario: str | None = None
    responsable_original_nombre: str | None = None

    # Lo que el usuario con sesion puede hacer con este activo (lo decide el backend).
    acciones_permitidas: list[str] = []


class MovimientoResponse(BaseModel):
    id: str
    tipo: TipoMovimiento
    sentido: SentidoPrestamo | None
    items: list[ItemMovimientoResponse]
    usuario_destino_id: str | None
    descripcion: str
    evento_nombre: str | None
    fecha_salida_estimada: datetime | None
    fecha_retorno_estimada: datetime | None
    fecha_entrega_real: datetime | None
    fecha_devolucion_real: datetime | None
    estado: EstadoMovimiento
    aprobado_por_admin_nombre: str | None
    aprobado_por_admin_fecha: datetime | None
    comprobante_archivo_id: str | None
    creado_por_id: str
    creado_por_nombre: str
    fecha_creacion: datetime

    # Solo en el listado y el detalle.
    usuario_destino_nombre: str | None = None

    # Acciones que el usuario con sesion puede ejecutar ahora sobre algun activo (las decide el backend).
    acciones_permitidas: list[str] = []
