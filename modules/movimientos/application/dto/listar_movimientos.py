from datetime import datetime

from pydantic import BaseModel, Field

from modules.movimientos.domain.entities.movimiento import TipoMovimiento


class ListarMovimientosInput(BaseModel):
    producto_codigo: str | None = None
    tipo: TipoMovimiento | None = None
    fecha_desde: datetime | None = None
    fecha_hasta: datetime | None = None
    motivo: str | None = None
    remision: str | None = None
    caso: str | None = None
    origen_destino: str | None = None
    pagina: int = Field(default=1, ge=1)
    limite: int = Field(default=20, ge=1, le=200)
