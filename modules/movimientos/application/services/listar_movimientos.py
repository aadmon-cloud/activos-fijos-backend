from modules.movimientos.application.dto.listar_movimientos_dto import ListarMovimientosDTO
from modules.movimientos.application.dto.movimiento_con_nombres_dto import (
    ListadoMovimientosDTO,
    movimiento_con_nombres_a_dto,
)
from modules.movimientos.application.dto.movimiento_dto import movimiento_a_dto
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import (
    MovimientoRepositoryPort,
    ParaMiMovimiento,
    VisibilidadMovimiento,
)
from modules.movimientos.application.ports.resolutor_nombres_port import (
    ReferenciasMovimiento,
    ResolutorNombresMovimientoPort,
)
from modules.movimientos.domain.permisos import (
    acciones_de_item,
    acciones_permitidas,
    es_administrador,
)

_LIMITE_MAXIMO = 1000


class ListarMovimientosService:
    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        resolutor_nombres: ResolutorNombresMovimientoPort,
        activo_movimiento: ActivoMovimientoPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._resolutor_nombres = resolutor_nombres
        self._activo_movimiento = activo_movimiento

    async def ejecutar(self, dto: ListarMovimientosDTO) -> ListadoMovimientosDTO:
        limit = min(dto.limit, _LIMITE_MAXIMO)
        es_admin = es_administrador(dto.actor_rol)

        # Los activos que el usuario tiene a su cargo no se guardan en el movimiento: se consultan aparte.
        activo_ids = frozenset()
        if not es_admin or dto.para_mi:
            activo_ids = frozenset(await self._activo_movimiento.listar_ids_por_responsable(dto.actor_id))

        # El administrador ve todo; el resto, solo lo que tiene que ver con el.
        visible_para = None if es_admin else VisibilidadMovimiento(dto.actor_id, activo_ids)
        para_mi = ParaMiMovimiento(dto.actor_id, activo_ids, es_admin) if dto.para_mi else None

        kwargs = dict(
            tipo=dto.tipo,
            estado=dto.estado,
            activo_id=dto.activo_id,
            usuario_destino_id=dto.usuario_destino_id,
            creado_por_id=dto.creado_por_id,
            visible_para=visible_para,
            para_mi=para_mi,
        )
        movimientos = await self._movimiento_repository.listar(**kwargs, skip=dto.skip, limit=limit)
        total = await self._movimiento_repository.contar(**kwargs)

        if not movimientos:
            return ListadoMovimientosDTO(items=[], total=total, skip=dto.skip, limit=limit)

        nombres = await self._resolutor_nombres.resolver(
            ReferenciasMovimiento(
                activo_ids={a for m in movimientos for a in m.activo_ids},
                usuario_ids={
                    u
                    for m in movimientos
                    for u in (m.usuario_destino_id, *(i.responsable_original_id for i in m.items))
                    if u
                },
            )
        )
        responsables = nombres.responsables_actuales()

        items = []
        for movimiento in movimientos:
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
            items.append(
                movimiento_con_nombres_a_dto(
                    movimiento_a_dto(movimiento), nombres, [a.value for a in acciones], por_activo
                )
            )

        return ListadoMovimientosDTO(items=items, total=total, skip=dto.skip, limit=limit)
