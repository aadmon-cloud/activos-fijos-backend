from shared.application.dto.pagination import RespuestaPaginada

from modules.productos.application.dto.listar_productos import ListarProductosInput
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.entities.producto import Producto


class ListarProductosService:
    def __init__(self, producto_repository: ProductoRepositoryPort):
        self._producto_repository = producto_repository

    async def ejecutar(self, entrada: ListarProductosInput) -> RespuestaPaginada[Producto]:
        productos, total = await self._producto_repository.listar_paginado(
            pagina=entrada.pagina, limite=entrada.limite
        )
        return RespuestaPaginada.crear(
            items=productos, page=entrada.pagina, limit=entrada.limite, total=total
        )
