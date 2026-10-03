from datetime import UTC, datetime

from modules.catalogos.application.dto.area_dto import AreaDTO, area_a_dto
from modules.catalogos.application.dto.crear_area_dto import CrearAreaDTO
from modules.catalogos.application.ports.area_repository import AreaRepositoryPort
from modules.catalogos.domain.entities import Area
from modules.catalogos.domain.errors import AreaNombreDuplicadoError
from shared.domain.entities.audit import AuditPersona


class CrearAreaService:
    def __init__(self, area_repository: AreaRepositoryPort):
        self._area_repository = area_repository

    async def ejecutar(self, dto: CrearAreaDTO) -> AreaDTO:
        nombre = dto.nombre.strip()

        if await self._area_repository.obtener_por_nombre(nombre) is not None:
            raise AreaNombreDuplicadoError(nombre)

        area = Area(
            id=None,
            nombre=nombre,
            descripcion=dto.descripcion,
            creado_por=AuditPersona(
                id_persona=dto.creado_por_id,
                nombre=dto.creado_por_nombre,
                fecha=datetime.now(UTC),
            ),
            actualizado_por=None,
        )

        area_guardada = await self._area_repository.guardar(area)
        return area_a_dto(area_guardada)
