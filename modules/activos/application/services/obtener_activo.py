from modules.activos.application.dto.activo_con_nombres_dto import ActivoConNombresDTO
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.resolutor_nombres import ResolutorNombresPort
from modules.activos.application.services.enriquecimiento import con_nombres
from modules.activos.domain.errors import ActivoNoEncontradoError


class ObtenerActivoService:
    def __init__(
        self,
        activo_repository: ActivoRepositoryPort,
        resolutor_nombres: ResolutorNombresPort,
    ):
        self._activo_repository = activo_repository
        self._resolutor_nombres = resolutor_nombres

    async def ejecutar(self, id_activo: str) -> ActivoConNombresDTO:
        activo = await self._activo_repository.obtener_por_id(id_activo)
        if activo is None:
            raise ActivoNoEncontradoError(id_activo)

        return (await con_nombres([activo], self._resolutor_nombres))[0]
