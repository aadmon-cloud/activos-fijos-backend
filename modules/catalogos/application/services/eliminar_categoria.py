from modules.catalogos.application.ports.categoria_repository import CategoriaRepositoryPort
from modules.catalogos.application.ports.verificador_uso_en_activos import (
    VerificadorUsoEnActivosPort,
)
from modules.catalogos.domain.errors import CategoriaEnUsoError, CategoriaNoEncontradaError


class EliminarCategoriaService:
    def __init__(
        self,
        categoria_repository: CategoriaRepositoryPort,
        verificador_uso: VerificadorUsoEnActivosPort,
    ):
        self._categoria_repository = categoria_repository
        self._verificador_uso = verificador_uso

    async def ejecutar(self, id_categoria: str) -> None:
        categoria = await self._categoria_repository.obtener_por_id(id_categoria)
        if categoria is None:
            raise CategoriaNoEncontradaError(id_categoria)

        if await self._verificador_uso.categoria_esta_en_uso(id_categoria):
            raise CategoriaEnUsoError(id_categoria)

        await self._categoria_repository.eliminar(id_categoria)
