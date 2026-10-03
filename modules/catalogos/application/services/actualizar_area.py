from dataclasses import replace
from datetime import UTC, datetime

from modules.catalogos.application.dto.actualizar_area_dto import ActualizarAreaDTO
from modules.catalogos.application.dto.area_dto import AreaDTO, area_a_dto
from modules.catalogos.application.ports.area_repository import AreaRepositoryPort
from modules.catalogos.domain.errors import AreaNoEncontradaError, AreaNombreDuplicadoError
from shared.domain.entities.audit import AuditPersona


class ActualizarAreaService:
    def __init__(self, area_repository: AreaRepositoryPort):
        self._area_repository = area_repository

    async def ejecutar(self, dto: ActualizarAreaDTO) -> AreaDTO:
        area = await self._area_repository.obtener_por_id(dto.id_area)
        if area is None:
            raise AreaNoEncontradaError(dto.id_area)

        nombre_nuevo = dto.nombre.strip() if dto.nombre is not None else area.nombre
        if nombre_nuevo != area.nombre:
            existente = await self._area_repository.obtener_por_nombre(nombre_nuevo)
            if existente is not None and existente.id != area.id:
                raise AreaNombreDuplicadoError(nombre_nuevo)

        area_actualizada = replace(
            area,
            nombre=nombre_nuevo,
            descripcion=dto.descripcion if dto.descripcion is not None else area.descripcion,
            actualizado_por=AuditPersona(
                id_persona=dto.actualizado_por_id,
                nombre=dto.actualizado_por_nombre,
                fecha=datetime.now(UTC),
            ),
        )

        area_guardada = await self._area_repository.guardar(area_actualizada)
        return area_a_dto(area_guardada)
