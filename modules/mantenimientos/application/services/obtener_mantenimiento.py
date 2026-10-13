from modules.mantenimientos.application.dto.mantenimiento_con_nombres_dto import (
    MantenimientoConNombresDTO,
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
from modules.mantenimientos.domain.errors import MantenimientoNoEncontradoError


class ObtenerMantenimientoService:
    def __init__(
        self,
        mantenimiento_repository: MantenimientoRepositoryPort,
        resolutor_nombres: ResolutorNombresMantenimientoPort,
    ):
        self._mantenimiento_repository = mantenimiento_repository
        self._resolutor_nombres = resolutor_nombres

    async def ejecutar(self, id_mantenimiento: str) -> MantenimientoConNombresDTO:
        mantenimiento = await self._mantenimiento_repository.obtener_por_id(id_mantenimiento)
        if mantenimiento is None:
            raise MantenimientoNoEncontradoError(id_mantenimiento)

        nombres = await self._resolutor_nombres.resolver(
            ReferenciasMantenimiento(
                activo_ids={mantenimiento.activo_id},
                tecnico_ids={mantenimiento.tecnico_responsable_id},
            )
        )

        return mantenimiento_con_nombres_a_dto(mantenimiento_a_dto(mantenimiento), nombres)
