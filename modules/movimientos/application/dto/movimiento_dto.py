from dataclasses import dataclass, field
from datetime import datetime

from modules.movimientos.domain.entities import (
    ActaMovimiento,
    ChequeoItem,
    EstadoItemMovimiento,
    EstadoMovimiento,
    EtapaRechazo,
    ItemMovimiento,
    LineaActa,
    Movimiento,
    ResultadoChequeo,
    SentidoPrestamo,
    TipoActa,
    TipoMovimiento,
)
from shared.domain.entities.audit import AuditPersona


@dataclass
class ChequeoItemDTO:
    resultado: ResultadoChequeo
    observacion: str | None
    por_nombre: str
    fecha: datetime


@dataclass
class LineaActaDTO:
    activo_id: str
    resultado: ResultadoChequeo
    observacion: str | None

    # Solo en las consultas: nombre e inventario vigentes del activo.
    activo_nombre: str | None = None
    activo_numero_inventario: str | None = None


@dataclass
class ActaDTO:
    id: str
    tipo: TipoActa
    numero: int
    fecha_cierre: datetime
    cerrada_por_nombre: str
    cerrada_por_correo: str
    aceptada_por_nombre: str | None
    aceptada_por_correo: str | None
    fecha_aceptacion: datetime | None
    lineas: list[LineaActaDTO]

    # Solo en el detalle: si el usuario con sesion puede aceptarla ahora.
    puede_aceptar: bool = False


@dataclass
class ItemMovimientoDTO:
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
    chequeo_salida: ChequeoItemDTO | None = None
    chequeo_ingreso: ChequeoItemDTO | None = None

    # Solo en las consultas (listado y detalle): nombres vigentes y lo que el usuario puede hacer con este activo.
    activo_nombre: str | None = None
    activo_numero_inventario: str | None = None
    responsable_original_nombre: str | None = None
    acciones_permitidas: list[str] = field(default_factory=list)


@dataclass
class MovimientoDTO:
    id: str
    tipo: TipoMovimiento
    sentido: SentidoPrestamo | None
    items: list[ItemMovimientoDTO]
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
    actas: list[ActaDTO] = field(default_factory=list)

    # Solo en las consultas (listado y detalle).
    usuario_destino_nombre: str | None = None
    acciones_permitidas: list[str] = field(default_factory=list)


def _nombre(audit: AuditPersona | None) -> str | None:
    return audit.nombre if audit else None


def _fecha(audit: AuditPersona | None) -> datetime | None:
    return audit.fecha if audit else None


def _chequeo_a_dto(chequeo: ChequeoItem | None) -> ChequeoItemDTO | None:
    if chequeo is None:
        return None

    return ChequeoItemDTO(
        resultado=chequeo.resultado,
        observacion=chequeo.observacion,
        por_nombre=chequeo.por.nombre,
        fecha=chequeo.por.fecha,
    )


def _linea_a_dto(linea: LineaActa) -> LineaActaDTO:
    return LineaActaDTO(activo_id=linea.activo_id, resultado=linea.resultado, observacion=linea.observacion)


def acta_a_dto(acta: ActaMovimiento) -> ActaDTO:
    aceptada = acta.aceptada_por

    return ActaDTO(
        id=acta.id,
        tipo=acta.tipo,
        numero=acta.numero,
        fecha_cierre=acta.cerrada_por.fecha,
        cerrada_por_nombre=acta.cerrada_por.nombre,
        cerrada_por_correo=acta.cerrada_por.correo,
        aceptada_por_nombre=aceptada.nombre if aceptada else None,
        aceptada_por_correo=aceptada.correo if aceptada else None,
        fecha_aceptacion=aceptada.fecha if aceptada else None,
        lineas=[_linea_a_dto(linea) for linea in acta.lineas],
    )


def item_a_dto(item: ItemMovimiento) -> ItemMovimientoDTO:
    return ItemMovimientoDTO(
        activo_id=item.activo_id,
        estado=item.estado,
        responsable_original_id=item.responsable_original_id,
        aprobado_por_responsable_nombre=_nombre(item.aprobado_por_responsable),
        aprobado_por_responsable_fecha=_fecha(item.aprobado_por_responsable),
        rechazado_por_nombre=_nombre(item.rechazado_por),
        etapa_rechazo=item.etapa_rechazo,
        motivo_rechazo=item.motivo_rechazo,
        devolucion_solicitada_por_nombre=_nombre(item.devolucion_solicitada_por),
        recibido_por_nombre=_nombre(item.recibido_por),
        fecha_devolucion_real=item.fecha_devolucion_real,
        novedad_devolucion=item.novedad_devolucion,
        chequeo_salida=_chequeo_a_dto(item.chequeo_salida),
        chequeo_ingreso=_chequeo_a_dto(item.chequeo_ingreso),
    )


def movimiento_a_dto(movimiento: Movimiento) -> MovimientoDTO:
    return MovimientoDTO(
        id=movimiento.id,
        tipo=movimiento.tipo,
        sentido=movimiento.sentido,
        items=[item_a_dto(item) for item in movimiento.items],
        usuario_destino_id=movimiento.usuario_destino_id,
        descripcion=movimiento.descripcion,
        evento_nombre=movimiento.evento_nombre,
        fecha_salida_estimada=movimiento.fecha_salida_estimada,
        fecha_retorno_estimada=movimiento.fecha_retorno_estimada,
        fecha_entrega_real=movimiento.fecha_entrega_real,
        fecha_devolucion_real=movimiento.fecha_devolucion_real,
        estado=movimiento.estado,
        aprobado_por_admin_nombre=_nombre(movimiento.aprobado_por_admin),
        aprobado_por_admin_fecha=_fecha(movimiento.aprobado_por_admin),
        comprobante_archivo_id=movimiento.comprobante_archivo_id,
        creado_por_id=movimiento.creado_por.id_persona,
        creado_por_nombre=movimiento.creado_por.nombre,
        fecha_creacion=movimiento.creado_por.fecha,
        actas=[acta_a_dto(acta) for acta in movimiento.actas],
    )
