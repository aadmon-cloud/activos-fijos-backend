from modules.mantenimientos.application.dto.listar_mantenimientos_dto import (
    ListarMantenimientosDTO,
)
from modules.mantenimientos.application.dto.mantenimiento_con_nombres_dto import (
    ListadoMantenimientosDTO,
    mantenimiento_con_nombres_a_dto,
)
from modules.mantenimientos.application.dto.mantenimiento_dto import mantenimiento_a_dto
from modules.mantenimientos.application.ports.mantenimiento_repository import (
    MantenimientoRepositoryPort,
)
from modules.mantenimientos.application.ports.resolutor_nombres_port import (
    ReferenciasMantenimiento,
    ResolutorNombresMantenimientoPort,
)

_LIMITE_MAXIMO = 1000


class ListarMantenimientosService:
    def __init__(
        self,
        mantenimiento_repository: MantenimientoRepositoryPort,
        resolutor_nombres: ResolutorNombresMantenimientoPort,
    ):
        self._mantenimiento_repository = mantenimiento_repository
        self._resolutor_nombres = resolutor_nombres

    async def ejecutar(self, dto: ListarMantenimientosDTO) -> ListadoMantenimientosDTO:
        limit = min(dto.limit, _LIMITE_MAXIMO)
        kwargs = dict(
            activo_id=dto.activo_id,
            tecnico_responsable_id=dto.tecnico_responsable_id,
            estado=dto.estado,
            tipo=dto.tipo,
            solicitud_id=dto.solicitud_id,
        )
        mantenimientos = await self._mantenimiento_repository.listar(
            **kwargs, skip=dto.skip, limit=limit
        )
        total = await self._mantenimiento_repository.contar(**kwargs)

        items_base = [mantenimiento_a_dto(m) for m in mantenimientos]

        if not items_base:
            return ListadoMantenimientosDTO(items=[], total=total, skip=dto.skip, limit=limit)

        referencias = ReferenciasMantenimiento(
            activo_ids={m.activo_id for m in items_base},
            tecnico_ids={m.tecnico_responsable_id for m in items_base},
        )
        nombres = await self._resolutor_nombres.resolver(referencias)

        items = [mantenimiento_con_nombres_a_dto(m, nombres) for m in items_base]
        return ListadoMantenimientosDTO(items=items, total=total, skip=dto.skip, limit=limit)
