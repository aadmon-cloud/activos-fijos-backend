from modules.inventario_reportes.application.dto.reporte_inventario import (
    ReporteInventarioOutput,
)
from modules.movimientos.application.dto.listar_movimientos import ListarMovimientosInput
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort


class ObtenerReporteInventarioService:
    def __init__(
        self,
        producto_repository: ProductoRepositoryPort,
        movimiento_repository: MovimientoRepositoryPort,
    ):
        self._producto_repository = producto_repository
        self._movimiento_repository = movimiento_repository

    async def ejecutar(self) -> ReporteInventarioOutput:
        _, total_productos = await self._producto_repository.listar_paginado(pagina=1, limite=1)
        productos_bajo_stock = await self._producto_repository.listar_bajo_stock()
        valor_total_inventario = await self._producto_repository.calcular_valor_total()
        ultimos_movimientos, _ = await self._movimiento_repository.listar(
            ListarMovimientosInput(pagina=1, limite=10)
        )
        return ReporteInventarioOutput(
            total_productos=total_productos,
            productos_bajo_stock=productos_bajo_stock,
            valor_total_inventario=valor_total_inventario,
            ultimos_movimientos=ultimos_movimientos,
        )
