from dataclasses import replace
from datetime import UTC, datetime

from modules.catalogos.application.dto.actualizar_sede_dto import ActualizarSedeDTO
from modules.catalogos.application.dto.sede_dto import SedeDTO, sede_a_dto
from modules.catalogos.application.ports.sede_repository import SedeRepositoryPort
from modules.catalogos.domain.errors import SedeNoEncontradaError, SedeNombreDuplicadoError
from shared.domain.entities.audit import AuditPersona


class ActualizarSedeService:
    def __init__(self, sede_repository: SedeRepositoryPort):
        self._sede_repository = sede_repository

    async def ejecutar(self, dto: ActualizarSedeDTO) -> SedeDTO:
        sede = await self._sede_repository.obtener_por_id(dto.id_sede)
        if sede is None:
            raise SedeNoEncontradaError(dto.id_sede)

        nombre_nuevo = dto.nombre.strip() if dto.nombre is not None else sede.nombre
        if nombre_nuevo != sede.nombre:
            existente = await self._sede_repository.obtener_por_nombre(nombre_nuevo)
            if existente is not None and existente.id != sede.id:
                raise SedeNombreDuplicadoError(nombre_nuevo)

        sede_actualizada = replace(
            sede,
            nombre=nombre_nuevo,
            descripcion=dto.descripcion if dto.descripcion is not None else sede.descripcion,
            actualizado_por=AuditPersona(
                id_persona=dto.actualizado_por_id,
                nombre=dto.actualizado_por_nombre,
                fecha=datetime.now(UTC),
            ),
        )

        sede_guardada = await self._sede_repository.guardar(sede_actualizada)
        return sede_a_dto(sede_guardada)
