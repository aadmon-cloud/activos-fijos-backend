from modules.catalogos.application.dto.categoria_dto import CategoriaDTO, categoria_a_dto
from modules.catalogos.application.ports.categoria_repository import CategoriaRepositoryPort
from modules.catalogos.domain.errors import CategoriaNoEncontradaError


class ObtenerCategoriaService:
    def __init__(self, categoria_repository: CategoriaRepositoryPort):
        self._categoria_repository = categoria_repository

    async def ejecutar(self, id_categoria: str) -> CategoriaDTO:
        categoria = await self._categoria_repository.obtener_por_id(id_categoria)
        if categoria is None:
            raise CategoriaNoEncontradaError(id_categoria)
        return categoria_a_dto(categoria)
