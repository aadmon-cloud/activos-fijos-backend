from dataclasses import replace

from modules.movimientos.application.dto.chequeo_movimiento_dto import ChequearItemDTO
from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO, movimiento_a_dto
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.seleccion_activos import (
    ahora_audit,
    cargar_movimiento_visible,
    reemplazar_items,
)
from modules.movimientos.domain.entities import ChequeoItem, ResultadoChequeo
from modules.movimientos.domain.errors import (
    ActivoNoPerteneceAlMovimientoError,
    ChequeoNoDisponibleError,
    ObservacionDeNovedadObligatoriaError,
)
from modules.movimientos.domain.permisos import AccionMovimiento, acciones_de_item


class ChequearItemMovimientoService:
    """Administracion marca como encontrado, con novedad o no encontrado un activo de la salida o del ingreso.

    Cada marca queda guardada al instante y se puede corregir hasta cerrar el chequeo. La fase (salida o ingreso)
    la define el estado del activo: el que espera la confirmacion de administracion se chequea para la salida; el
    que esta fuera, para el ingreso."""

    def __init__(self, movimiento_repository: MovimientoRepositoryPort, activo_movimiento: ActivoMovimientoPort):
        self._movimiento_repository = movimiento_repository
        self._activo_movimiento = activo_movimiento

    async def ejecutar(self, dto: ChequearItemDTO) -> MovimientoDTO:
        movimiento, resumenes = await cargar_movimiento_visible(
            self._movimiento_repository,
            self._activo_movimiento,
            dto.id_movimiento,
            dto.actor_id,
            dto.actor_rol,
        )

        item = movimiento.item(dto.activo_id)
        if item is None:
            raise ActivoNoPerteneceAlMovimientoError(dto.activo_id)

        resumen = resumenes.get(dto.activo_id)
        acciones = acciones_de_item(
            movimiento, item, dto.actor_id, dto.actor_rol, resumen.responsable_id if resumen else None
        )

        observacion = (dto.observacion or "").strip() or None
        if dto.resultado == ResultadoChequeo.CON_NOVEDAD and observacion is None:
            raise ObservacionDeNovedadObligatoriaError(dto.activo_id)

        chequeo = ChequeoItem(
            resultado=dto.resultado, observacion=observacion, por=ahora_audit(dto.actor_id, dto.actor_nombre)
        )

        if AccionMovimiento.CONFIRMAR_SALIDA in acciones:
            marcado = replace(item, chequeo_salida=chequeo)
        elif AccionMovimiento.CONFIRMAR_DEVOLUCION in acciones:
            marcado = replace(item, chequeo_ingreso=chequeo)
        else:
            raise ChequeoNoDisponibleError(dto.activo_id)

        guardado = await self._movimiento_repository.guardar(
            replace(
                movimiento,
                items=reemplazar_items(movimiento, {item.activo_id: marcado}),
                actualizado_por=chequeo.por,
            )
        )

        return movimiento_a_dto(guardado)
