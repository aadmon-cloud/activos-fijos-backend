import logging
from dataclasses import replace
from datetime import UTC, datetime

from modules.movimientos.application.avisos import EventoMovimiento, avisar
from modules.movimientos.application.dto.acciones_movimiento_dto import (
    ConfirmarDevolucionDTO,
    ReciboActivoDTO,
)
from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO, movimiento_a_dto
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.seleccion_activos import (
    aplicar_a_activos,
    ahora_audit,
    elegir_activos,
    reemplazar_items,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    ItemMovimiento,
    Movimiento,
)
from modules.movimientos.domain.errors import (
    MovimientoNoEncontradoError,
    ObservacionDeNovedadObligatoriaError,
    OperacionSobreActivoFallidaError,
    TransicionEstadoMovimientoInvalidaError,
)
from modules.movimientos.domain.transiciones import ESTADOS_ITEM_DEVOLVIBLES, calcular_estado
from shared.application.notifications.ports import NotificadorPort

logger = logging.getLogger(__name__)

_ESTADO_DISPONIBLE = "disponible"
_ESTADO_PRESTADO = "prestado"


class ConfirmarDevolucionMovimientoService:
    """Administracion recibe de vuelta los activos (todos o algunos), cada uno bien o con una novedad. El activo
    vuelve a `disponible` y a su responsable original; una novedad queda en el historial del activo."""

    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        activo_movimiento: ActivoMovimientoPort,
        notificador: NotificadorPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._activo_movimiento = activo_movimiento
        self._notificador = notificador

    async def ejecutar(self, dto: ConfirmarDevolucionDTO) -> MovimientoDTO:
        movimiento = await self._movimiento_repository.obtener_por_id(dto.id_movimiento)
        if movimiento is None:
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        invalido = TransicionEstadoMovimientoInvalidaError(movimiento.estado.value, "devuelto")
        devolvibles = [i for i in movimiento.items if i.estado in ESTADOS_ITEM_DEVOLVIBLES]
        if not devolvibles:
            raise invalido

        recibos = self._recibos(dto, devolvibles)
        recibidos = elegir_activos(movimiento, devolvibles, [r.activo_id for r in recibos], invalido)
        por_activo = {recibo.activo_id: recibo for recibo in recibos}

        for recibo in recibos:
            if recibo.con_novedad and not (recibo.observacion or "").strip():
                raise ObservacionDeNovedadObligatoriaError(recibo.activo_id)

        audit = ahora_audit(dto.actor_id, dto.actor_nombre)
        ahora = datetime.now(UTC)

        await aplicar_a_activos(
            recibidos,
            aplicar=lambda item: self._devolver(item, movimiento, dto),
            deshacer=lambda item: self._deshacer_devolucion(item, movimiento, dto),
            error=OperacionSobreActivoFallidaError,
        )

        cambios: dict[str, ItemMovimiento] = {}
        for item in recibidos:
            recibo = por_activo[item.activo_id]
            cambios[item.activo_id] = replace(
                item,
                estado=EstadoItemMovimiento.DEVUELTO,
                recibido_por=audit,
                fecha_devolucion_real=ahora,
                novedad_devolucion=(recibo.observacion or "").strip() if recibo.con_novedad else None,
            )

        items = reemplazar_items(movimiento, cambios)
        estado = calcular_estado(movimiento.tipo, items, movimiento.estado)
        devuelto = replace(
            movimiento,
            items=items,
            estado=estado,
            fecha_devolucion_real=ahora if estado == EstadoMovimiento.DEVUELTO else None,
            actualizado_por=audit,
        )

        guardado = await self._movimiento_repository.guardar(devuelto)
        await self._dejar_novedades_en_el_historial(guardado, cambios.values(), dto)

        resumenes = await self._activo_movimiento.obtener_resumenes(movimiento.activo_ids)
        await avisar(self._notificador, EventoMovimiento.DEVOLUCION_CONFIRMADA, guardado, resumenes)

        return movimiento_a_dto(guardado)

    @staticmethod
    def _recibos(dto: ConfirmarDevolucionDTO, devolvibles: list[ItemMovimiento]) -> list[ReciboActivoDTO]:
        """Sin recibos explicitos se reciben todos los activos que estan fuera, sin novedad."""
        if dto.recibos is None:
            return [ReciboActivoDTO(activo_id=item.activo_id) for item in devolvibles]

        return list({recibo.activo_id: recibo for recibo in dto.recibos}.values())

    async def _devolver(
        self, item: ItemMovimiento, movimiento: Movimiento, dto: ConfirmarDevolucionDTO
    ) -> bool:
        # Dos cambios sobre el activo sin transaccion: si el segundo falla se deshace el primero.
        if not await self._activo_movimiento.cambiar_estado(
            item.activo_id, _ESTADO_DISPONIBLE, dto.actor_id, dto.actor_nombre
        ):
            return False

        if not await self._activo_movimiento.cambiar_responsable(
            item.activo_id, item.responsable_original_id, dto.actor_id, dto.actor_nombre
        ):
            await self._activo_movimiento.cambiar_estado(
                item.activo_id, _ESTADO_PRESTADO, dto.actor_id, dto.actor_nombre
            )
            return False

        return True

    async def _deshacer_devolucion(
        self, item: ItemMovimiento, movimiento: Movimiento, dto: ConfirmarDevolucionDTO
    ) -> None:
        await self._activo_movimiento.cambiar_responsable(
            item.activo_id, movimiento.usuario_destino_id, dto.actor_id, dto.actor_nombre
        )
        await self._activo_movimiento.cambiar_estado(
            item.activo_id, _ESTADO_PRESTADO, dto.actor_id, dto.actor_nombre
        )

    async def _dejar_novedades_en_el_historial(
        self, movimiento: Movimiento, items, dto: ConfirmarDevolucionDTO
    ) -> None:
        # La novedad tambien queda guardada en el movimiento: si dejar la nota falla, la devolucion ya hecha
        # no se revierte; se registra el fallo para repararlo.
        for item in items:
            if not item.novedad_devolucion:
                continue
            try:
                await self._activo_movimiento.registrar_nota(
                    item.activo_id,
                    f"Novedad al recibirlo de vuelta ({_descripcion(movimiento)}): {item.novedad_devolucion}",
                    movimiento.id,
                    dto.actor_id,
                    dto.actor_nombre,
                )
            except Exception:
                logger.exception(
                    "No se pudo registrar la novedad de devolucion en el historial del activo %s", item.activo_id
                )


def _descripcion(movimiento: Movimiento) -> str:
    if movimiento.evento_nombre:
        return f"salida al evento '{movimiento.evento_nombre}'"

    return "prestamo"
