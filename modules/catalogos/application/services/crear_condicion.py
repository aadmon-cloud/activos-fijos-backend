import re
from datetime import UTC, datetime

from modules.catalogos.application.dto.condicion_dto import CondicionDTO, condicion_a_dto
from modules.catalogos.application.dto.crear_condicion_dto import CrearCondicionDTO
from modules.catalogos.application.ports.condicion_repository import CondicionRepositoryPort
from modules.catalogos.domain.entities import Condicion
from modules.catalogos.domain.errors import (
    CondicionColorInvalidoError,
    CondicionNombreDuplicadoError,
)
from shared.domain.entities.audit import AuditPersona

_PATRON_COLOR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class CrearCondicionService:
    def __init__(self, condicion_repository: CondicionRepositoryPort):
        self._condicion_repository = condicion_repository

    async def ejecutar(self, dto: CrearCondicionDTO) -> CondicionDTO:
        nombre = dto.nombre.strip()

        if not _PATRON_COLOR_HEX.fullmatch(dto.color):
            raise CondicionColorInvalidoError(dto.color)

        if await self._condicion_repository.obtener_por_nombre(nombre) is not None:
            raise CondicionNombreDuplicadoError(nombre)

        condicion = Condicion(
            id=None,
            nombre=nombre,
            color=dto.color,
            descripcion=dto.descripcion,
            creado_por=AuditPersona(
                id_persona=dto.creado_por_id,
                nombre=dto.creado_por_nombre,
                fecha=datetime.now(UTC),
            ),
            actualizado_por=None,
        )

        condicion_guardada = await self._condicion_repository.guardar(condicion)
        return condicion_a_dto(condicion_guardada)
