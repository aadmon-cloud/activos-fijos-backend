from typing import Annotated

from fastapi import Depends

from modules.inventario_reportes.application.services.listar_productos_bajo_stock import (
    ListarProductosBajoStockService,
)
from modules.inventario_reportes.application.services.obtener_estadisticas_dashboard import (
    ObtenerEstadisticasDashboardService,
)
from modules.inventario_reportes.application.services.obtener_reporte_inventario import (
    ObtenerReporteInventarioService,
)
from modules.inventario_reportes.application.services.obtener_valor_total_inventario import (
    ObtenerValorTotalInventarioService,
)
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.infrastructure.api.dependencies import get_movimiento_repository
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.infrastructure.api.dependencies import get_producto_repository


def get_obtener_estadisticas_dashboard_service(
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
) -> ObtenerEstadisticasDashboardService:
    return ObtenerEstadisticasDashboardService(producto_repository, movimiento_repository)


def get_listar_productos_bajo_stock_service(
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> ListarProductosBajoStockService:
    return ListarProductosBajoStockService(producto_repository)


def get_obtener_valor_total_inventario_service(
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> ObtenerValorTotalInventarioService:
    return ObtenerValorTotalInventarioService(producto_repository)


def get_obtener_reporte_inventario_service(
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
) -> ObtenerReporteInventarioService:
    return ObtenerReporteInventarioService(producto_repository, movimiento_repository)
