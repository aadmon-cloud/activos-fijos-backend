from modules.catalogos.application.dto.categoria_dto import CategoriaDTO, categoria_a_dto
from modules.catalogos.application.ports.categoria_repository import CategoriaRepositoryPort


class ListarCategoriasService:
    def __init__(self, categoria_repository: CategoriaRepositoryPort):
        self._categoria_repository = categoria_repository

    async def ejecutar(self) -> list[CategoriaDTO]:
        categorias = await self._categoria_repository.listar()
        return [categoria_a_dto(categoria) for categoria in categorias]
