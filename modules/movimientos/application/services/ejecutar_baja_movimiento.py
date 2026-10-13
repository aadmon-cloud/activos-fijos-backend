from dataclasses import replace

from modules.movimientos.application.avisos import EventoMovimiento, avisar
from modules.movimientos.application.dto.actor_movimiento_dto import ActorMovimientoDTO
from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO, movimiento_a_dto
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.seleccion_activos import ahora_audit
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    TipoMovimiento,
)
from modules.movimientos.domain.errors import (
    MovimientoNoEncontradoError,
    OperacionSobreActivoFallidaError,
    TransicionEstadoMovimientoInvalidaError,
)
from modules.movimientos.domain.transiciones import calcular_estado
from shared.application.notifications.ports import NotificadorPort

_ESTADO_DADO_DE_BAJA = "dado_de_baja"


class EjecutarBajaMovimientoService:
    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        activo_movimiento: ActivoMovimientoPort,
        notificador: NotificadorPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._activo_movimiento = activo_movimiento
        self._notificador = notificador

    async def ejecutar(self, dto: ActorMovimientoDTO) -> MovimientoDTO:
        movimiento = await self._movimiento_repository.obtener_por_id(dto.id_movimiento)
        if movimiento is None:
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        if movimiento.tipo != TipoMovimiento.BAJA or movimiento.estado != EstadoMovimiento.APROBADO:
            raise TransicionEstadoMovimientoInvalidaError(movimiento.estado.value, "ejecutado")

        activo_id = movimiento.items[0].activo_id
        if not await self._activo_movimiento.cambiar_estado(
            activo_id, _ESTADO_DADO_DE_BAJA, dto.actor_id, dto.actor_nombre
        ):
            raise OperacionSobreActivoFallidaError(activo_id)

        audit = ahora_audit(dto.actor_id, dto.actor_nombre)
        items = [replace(item, estado=EstadoItemMovimiento.EJECUTADO) for item in movimiento.items]
        ejecutado = replace(
            movimiento,
            items=items,
            estado=calcular_estado(movimiento.tipo, items, movimiento.estado),
            actualizado_por=audit,
        )

        guardado = await self._movimiento_repository.guardar(ejecutado)
        resumenes = await self._activo_movimiento.obtener_resumenes(movimiento.activo_ids)
        await avisar(self._notificador, EventoMovimiento.BAJA_EJECUTADA, guardado, resumenes)

        return movimiento_a_dto(guardado)
