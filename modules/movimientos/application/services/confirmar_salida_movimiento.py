from dataclasses import replace
from datetime import UTC, datetime

from modules.movimientos.application.avisos import EventoMovimiento, avisar
from modules.movimientos.application.dto.acciones_movimiento_dto import ConfirmarSalidaDTO
from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO, movimiento_a_dto
from modules.movimientos.application.emisor_actas import EmisorActas
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.seleccion_activos import (
    aplicar_a_activos,
    ahora_audit,
    reemplazar_items,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EtapaRechazo,
    ItemMovimiento,
    LineaActa,
    ResultadoChequeo,
    SelloActa,
    TipoActa,
    TipoMovimiento,
)
from modules.movimientos.domain.errors import (
    MovimientoNoEncontradoError,
    NingunActivoChequeadoError,
    OperacionSobreActivoFallidaError,
    TransicionEstadoMovimientoInvalidaError,
)
from modules.movimientos.domain.transiciones import calcular_estado
from shared.application.notifications.ports import NotificadorPort

_ESTADO_PRESTADO = "prestado"
_ESTADO_DISPONIBLE = "disponible"
_MOTIVO_POR_DEFECTO = "No autorizado por administracion en la salida."


class ConfirmarSalidaMovimientoService:
    """Cierra el chequeo de salida de un prestamo o salida a evento.

    Salen los activos chequeados como encontrados (o con novedad): pasan a `prestado` y a cargo del destinatario.
    Los demas (no encontrados o sin chequear) quedan rechazados. Se genera el acta de salida con el sello de
    administracion; el del responsable queda pendiente hasta que la acepte."""

    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        activo_movimiento: ActivoMovimientoPort,
        emisor_actas: EmisorActas,
        notificador: NotificadorPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._activo_movimiento = activo_movimiento
        self._emisor_actas = emisor_actas
        self._notificador = notificador

    async def ejecutar(self, dto: ConfirmarSalidaDTO) -> MovimientoDTO:
        movimiento = await self._movimiento_repository.obtener_por_id(dto.id_movimiento)
        if movimiento is None:
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        pendientes = [i for i in movimiento.items if i.estado == EstadoItemMovimiento.PENDIENTE_ADMIN]
        if movimiento.tipo == TipoMovimiento.BAJA or not pendientes:
            raise TransicionEstadoMovimientoInvalidaError(movimiento.estado.value, "en_curso")

        salen = [i for i in pendientes if _sale(i)]
        if not salen:
            raise NingunActivoChequeadoError()

        no_salen = [i for i in pendientes if not _sale(i)]
        audit = ahora_audit(dto.actor_id, dto.actor_nombre)

        await aplicar_a_activos(
            salen,
            aplicar=lambda item: self._sacar(item, movimiento.usuario_destino_id, dto),
            deshacer=lambda item: self._deshacer_salida(item, dto),
            error=OperacionSobreActivoFallidaError,
        )

        cambios: dict[str, ItemMovimiento] = {
            item.activo_id: replace(item, estado=EstadoItemMovimiento.EN_CURSO) for item in salen
        }
        motivos: dict[str, str] = {}
        for item in no_salen:
            motivos[item.activo_id] = _motivo(item, dto)
            cambios[item.activo_id] = replace(
                item,
                estado=EstadoItemMovimiento.RECHAZADO,
                rechazado_por=audit,
                etapa_rechazo=EtapaRechazo.ADMINISTRACION,
                motivo_rechazo=motivos[item.activo_id],
            )

        items = reemplazar_items(movimiento, cambios)
        confirmado = replace(
            movimiento,
            items=items,
            estado=calcular_estado(movimiento.tipo, items, movimiento.estado),
            aprobado_por_admin=audit,
            fecha_entrega_real=datetime.now(UTC),
            actualizado_por=audit,
        )

        lineas = [
            LineaActa(
                activo_id=item.activo_id,
                resultado=item.chequeo_salida.resultado,
                observacion=item.chequeo_salida.observacion,
            )
            for item in salen
        ] + [
            LineaActa(activo_id=item.activo_id, resultado=ResultadoChequeo.NO_ENCONTRADO, observacion=motivos[item.activo_id])
            for item in no_salen
        ]
        acta = await self._emisor_actas.emitir(
            confirmado,
            TipoActa.SALIDA,
            lineas,
            SelloActa(id_persona=dto.actor_id, nombre=dto.actor_nombre, correo=dto.actor_correo, fecha=audit.fecha),
        )
        confirmado = replace(confirmado, actas=[*confirmado.actas, acta], comprobante_archivo_id=acta.archivo_id)

        guardado = await self._movimiento_repository.guardar(confirmado)
        resumenes = await self._activo_movimiento.obtener_resumenes(movimiento.activo_ids)
        await avisar(self._notificador, EventoMovimiento.SALIDA_CONFIRMADA, guardado, resumenes)

        return movimiento_a_dto(guardado)

    async def _sacar(self, item: ItemMovimiento, destino_id: str | None, dto: ConfirmarSalidaDTO) -> bool:
        # Dos cambios sobre el activo sin transaccion: si el segundo falla se deshace el primero, para no
        # dejarlo "prestado" con el responsable de antes.
        if not await self._activo_movimiento.cambiar_estado(
            item.activo_id, _ESTADO_PRESTADO, dto.actor_id, dto.actor_nombre
        ):
            return False

        if not await self._activo_movimiento.cambiar_responsable(
            item.activo_id, destino_id, dto.actor_id, dto.actor_nombre
        ):
            await self._activo_movimiento.cambiar_estado(
                item.activo_id, _ESTADO_DISPONIBLE, dto.actor_id, dto.actor_nombre
            )
            return False

        return True

    async def _deshacer_salida(self, item: ItemMovimiento, dto: ConfirmarSalidaDTO) -> None:
        await self._activo_movimiento.cambiar_responsable(
            item.activo_id, item.responsable_original_id, dto.actor_id, dto.actor_nombre
        )
        await self._activo_movimiento.cambiar_estado(
            item.activo_id, _ESTADO_DISPONIBLE, dto.actor_id, dto.actor_nombre
        )


def _sale(item: ItemMovimiento) -> bool:
    return item.chequeo_salida is not None and item.chequeo_salida.resultado != ResultadoChequeo.NO_ENCONTRADO


def _motivo(item: ItemMovimiento, dto: ConfirmarSalidaDTO) -> str:
    """Por que no sale: lo que anoto quien lo chequeo, o el motivo general, o uno por defecto."""
    propio = item.chequeo_salida.observacion if item.chequeo_salida else None

    return propio or (dto.motivo_no_incluidos or "").strip() or _MOTIVO_POR_DEFECTO
