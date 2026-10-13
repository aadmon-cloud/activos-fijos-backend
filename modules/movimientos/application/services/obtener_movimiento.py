from modules.movimientos.application.dto.movimiento_con_nombres_dto import (
    movimiento_con_nombres_a_dto,
)
from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO, movimiento_a_dto
from modules.movimientos.application.dto.obtener_movimiento_dto import ObtenerMovimientoDTO
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.ports.resolutor_nombres_port import (
    ReferenciasMovimiento,
    ResolutorNombresMovimientoPort,
)
from modules.movimientos.domain.errors import MovimientoNoEncontradoError
from modules.movimientos.domain.permisos import acciones_de_item, acciones_permitidas, puede_ver


class ObtenerMovimientoService:
    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        resolutor_nombres: ResolutorNombresMovimientoPort,
        activo_movimiento: ActivoMovimientoPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._resolutor_nombres = resolutor_nombres
        self._activo_movimiento = activo_movimiento

    async def ejecutar(self, dto: ObtenerMovimientoDTO) -> MovimientoDTO:
        movimiento = await self._movimiento_repository.obtener_por_id(dto.id_movimiento)
        if movimiento is None:
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        nombres = await self._resolutor_nombres.resolver(
            ReferenciasMovimiento(
                activo_ids=set(movimiento.activo_ids),
                usuario_ids={
                    u
                    for u in (movimiento.usuario_destino_id, *(i.responsable_original_id for i in movimiento.items))
                    if u
                },
            )
        )
        responsables = nombres.responsables_actuales()

        # Sin acceso al movimiento: se responde como si no existiera.
        if not puede_ver(movimiento, dto.actor_id, dto.actor_rol, responsables):
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        por_activo = {
            item.activo_id: [
                a.value
                for a in acciones_de_item(
                    movimiento, item, dto.actor_id, dto.actor_rol, responsables.get(item.activo_id)
                )
            ]
            for item in movimiento.items
        }
        acciones = acciones_permitidas(movimiento, dto.actor_id, dto.actor_rol, responsables)

        return movimiento_con_nombres_a_dto(
            movimiento_a_dto(movimiento), nombres, [a.value for a in acciones], por_activo
        )
