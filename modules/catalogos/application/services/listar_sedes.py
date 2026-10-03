from modules.catalogos.application.dto.sede_dto import SedeDTO, sede_a_dto
from modules.catalogos.application.ports.sede_repository import SedeRepositoryPort


class ListarSedesService:
    def __init__(self, sede_repository: SedeRepositoryPort):
        self._sede_repository = sede_repository

    async def ejecutar(self) -> list[SedeDTO]:
        sedes = await self._sede_repository.listar()
        return [sede_a_dto(sede) for sede in sedes]
