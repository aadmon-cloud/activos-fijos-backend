from datetime import UTC, datetime

from modules.catalogos.application.dto.crear_sede_dto import CrearSedeDTO
from modules.catalogos.application.dto.sede_dto import SedeDTO, sede_a_dto
from modules.catalogos.application.ports.sede_repository import SedeRepositoryPort
from modules.catalogos.domain.entities import Sede
from modules.catalogos.domain.errors import SedeNombreDuplicadoError
from shared.domain.entities.audit import AuditPersona


class CrearSedeService:
    def __init__(self, sede_repository: SedeRepositoryPort):
        self._sede_repository = sede_repository

    async def ejecutar(self, dto: CrearSedeDTO) -> SedeDTO:
        nombre = dto.nombre.strip()

        if await self._sede_repository.obtener_por_nombre(nombre) is not None:
            raise SedeNombreDuplicadoError(nombre)

        sede = Sede(
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

        sede_guardada = await self._sede_repository.guardar(sede)
        return sede_a_dto(sede_guardada)
