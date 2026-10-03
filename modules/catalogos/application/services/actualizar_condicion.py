import re
from dataclasses import replace
from datetime import UTC, datetime

from modules.catalogos.application.dto.actualizar_condicion_dto import ActualizarCondicionDTO
from modules.catalogos.application.dto.condicion_dto import CondicionDTO, condicion_a_dto
from modules.catalogos.application.ports.condicion_repository import CondicionRepositoryPort
from modules.catalogos.domain.errors import (
    CondicionColorInvalidoError,
    CondicionNoEncontradaError,
    CondicionNombreDuplicadoError,
)
from shared.domain.entities.audit import AuditPersona

_PATRON_COLOR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class ActualizarCondicionService:
    def __init__(self, condicion_repository: CondicionRepositoryPort):
        self._condicion_repository = condicion_repository

    async def ejecutar(self, dto: ActualizarCondicionDTO) -> CondicionDTO:
        condicion = await self._condicion_repository.obtener_por_id(dto.id_condicion)
        if condicion is None:
            raise CondicionNoEncontradaError(dto.id_condicion)

        if dto.color is not None and not _PATRON_COLOR_HEX.fullmatch(dto.color):
            raise CondicionColorInvalidoError(dto.color)

        nombre_nuevo = dto.nombre.strip() if dto.nombre is not None else condicion.nombre
        if nombre_nuevo != condicion.nombre:
            existente = await self._condicion_repository.obtener_por_nombre(nombre_nuevo)
            if existente is not None and existente.id != condicion.id:
                raise CondicionNombreDuplicadoError(nombre_nuevo)

        condicion_actualizada = replace(
            condicion,
            nombre=nombre_nuevo,
            color=dto.color if dto.color is not None else condicion.color,
            descripcion=(
                dto.descripcion if dto.descripcion is not None else condicion.descripcion
            ),
            actualizado_por=AuditPersona(
                id_persona=dto.actualizado_por_id,
                nombre=dto.actualizado_por_nombre,
                fecha=datetime.now(UTC),
            ),
        )

        condicion_guardada = await self._condicion_repository.guardar(condicion_actualizada)
        return condicion_a_dto(condicion_guardada)
