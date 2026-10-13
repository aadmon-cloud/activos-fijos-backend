from dataclasses import replace

from modules.movimientos.application.avisos import EventoMovimiento, avisar
from modules.movimientos.application.dto.aprobar_movimiento_dto import AprobarMovimientoDTO
from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO, movimiento_a_dto
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.seleccion_activos import (
    ahora_audit,
    cargar_movimiento_visible,
    elegir_activos,
    items_con_accion,
    reemplazar_items,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    TipoMovimiento,
)
from modules.movimientos.domain.errors import (
    PermisoAprobacionError,
    TransicionEstadoMovimientoInvalidaError,
)
from modules.movimientos.domain.permisos import AccionMovimiento
from modules.movimientos.domain.transiciones import calcular_estado
from shared.application.notifications.ports import NotificadorPort

_ESTADOS_QUE_ESPERAN_DECISION = (
    EstadoItemMovimiento.PENDIENTE_RESPONSABLE,
    EstadoItemMovimiento.PENDIENTE_ADMIN,
)


class AprobarMovimientoService:
    """Aprobar el paso que le toca a este usuario: cada responsable aprueba sus activos y, en una baja,
    administracion aprueba la solicitud. (La aprobacion final de un prestamo o salida es `confirmar-salida`.)"""

    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        activo_movimiento: ActivoMovimientoPort,
        notificador: NotificadorPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._activo_movimiento = activo_movimiento
        self._notificador = notificador

    async def ejecutar(self, dto: AprobarMovimientoDTO) -> MovimientoDTO:
        movimiento, resumenes = await cargar_movimiento_visible(
            self._movimiento_repository,
            self._activo_movimiento,
            dto.id_movimiento,
            dto.actor_id,
            dto.actor_rol,
        )

        if not any(item.estado in _ESTADOS_QUE_ESPERAN_DECISION for item in movimiento.items) or (
            movimiento.tipo == TipoMovimiento.BAJA and movimiento.estado != EstadoMovimiento.SOLICITADO
        ):
            raise TransicionEstadoMovimientoInvalidaError(movimiento.estado.value, "aprobado")

        elegibles = items_con_accion(
            movimiento, resumenes, dto.actor_id, dto.actor_rol, AccionMovimiento.APROBAR
        )
        elegidos = elegir_activos(
            movimiento, elegibles, dto.activo_ids, PermisoAprobacionError(dto.id_movimiento)
        )
        audit = ahora_audit(dto.actor_id, dto.actor_nombre)

        if movimiento.tipo == TipoMovimiento.BAJA:
            # La baja no tiene paso de responsable: administracion la aprueba y queda lista para ejecutar.
            actualizado = replace(
                movimiento,
                estado=EstadoMovimiento.APROBADO,
                aprobado_por_admin=audit,
                actualizado_por=audit,
            )
            evento = EventoMovimiento.APROBADO
        else:
            cambios = {
                item.activo_id: replace(
                    item, estado=EstadoItemMovimiento.PENDIENTE_ADMIN, aprobado_por_responsable=audit
                )
                for item in elegidos
            }
            items = reemplazar_items(movimiento, cambios)
            actualizado = replace(
                movimiento,
                items=items,
                estado=calcular_estado(movimiento.tipo, items, movimiento.estado),
                actualizado_por=audit,
            )
            evento = EventoMovimiento.APROBADO_RESPONSABLE

        guardado = await self._movimiento_repository.guardar(actualizado)
        await avisar(self._notificador, evento, guardado, resumenes)

        return movimiento_a_dto(guardado)
