from datetime import datetime

from pydantic import BaseModel

from modules.movimientos.domain.entities.movimiento import TipoMovimiento


class ExportarMovimientosExcelInput(BaseModel):
    fecha_desde: datetime | None = None
    fecha_hasta: datetime | None = None
    tipo: TipoMovimiento | None = None
