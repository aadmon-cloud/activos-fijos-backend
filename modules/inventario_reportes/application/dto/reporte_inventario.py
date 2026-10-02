from pydantic import BaseModel

from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.productos.domain.entities.producto import Producto


class ReporteInventarioOutput(BaseModel):
    total_productos: int
    productos_bajo_stock: list[Producto]
    valor_total_inventario: float
    ultimos_movimientos: list[Movimiento]
