from pydantic import BaseModel


class StockDisponibleResultado(BaseModel):
    producto_codigo: str
    ubicacion: str
    stock_fisico: int
    reservado_otros: int
    reservado_actual: int
    disponible: int
