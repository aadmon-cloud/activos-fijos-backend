from pydantic import BaseModel

from modules.movimientos.infrastructure.api.schemas import MovimientoResponse
from modules.productos.infrastructure.api.schemas import ProductoResponse


class EstadisticasDashboardResponse(BaseModel):
    total_productos: int
    productos_bajo_stock_conteo: int
    ultimos_movimientos: list[MovimientoResponse]
    movimientos_hoy: int


class ReporteInventarioResponse(BaseModel):
    total_productos: int
    productos_bajo_stock: list[ProductoResponse]
    valor_total_inventario: float
    ultimos_movimientos: list[MovimientoResponse]


class ValorTotalInventarioResponse(BaseModel):
    valor_total_inventario: float
