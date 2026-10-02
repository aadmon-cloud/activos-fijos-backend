from datetime import UTC, datetime

from modules.inventario_reportes.application.dto.estadisticas_dashboard import (
    EstadisticasDashboardOutput,
)
from modules.movimientos.application.dto.listar_movimientos import ListarMovimientosInput
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort


class ObtenerEstadisticasDashboardService:
    def __init__(
        self,
        producto_repository: ProductoRepositoryPort,
        movimiento_repository: MovimientoRepositoryPort,
    ):
        self._producto_repository = producto_repository
        self._movimiento_repository = movimiento_repository

    async def ejecutar(self) -> EstadisticasDashboardOutput:
        _, total_productos = await self._producto_repository.listar_paginado(pagina=1, limite=1)
        productos_bajo_stock = await self._producto_repository.listar_bajo_stock()
        ultimos_movimientos, _ = await self._movimiento_repository.listar(
            ListarMovimientosInput(pagina=1, limite=10)
        )
        hoy_inicio = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        _, movimientos_hoy = await self._movimiento_repository.listar(
            ListarMovimientosInput(fecha_desde=hoy_inicio, pagina=1, limite=1)
        )
        return EstadisticasDashboardOutput(
            total_productos=total_productos,
            productos_bajo_stock_conteo=len(productos_bajo_stock),
            ultimos_movimientos=ultimos_movimientos,
            movimientos_hoy=movimientos_hoy,
        )
