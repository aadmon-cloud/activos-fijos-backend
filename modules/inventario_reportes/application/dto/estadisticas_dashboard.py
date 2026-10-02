from pydantic import BaseModel

from modules.movimientos.domain.entities.movimiento import Movimiento


class EstadisticasDashboardOutput(BaseModel):
    total_productos: int
    productos_bajo_stock_conteo: int
    ultimos_movimientos: list[Movimiento]
    movimientos_hoy: int
