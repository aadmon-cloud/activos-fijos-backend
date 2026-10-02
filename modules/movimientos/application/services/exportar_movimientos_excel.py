from modules.movimientos.application.dto.exportar_movimientos_excel import (
    ExportarMovimientosExcelInput,
)
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.domain.entities.movimiento import Movimiento


class ExportarMovimientosExcelService:
    """Devuelve los movimientos filtrados, sin paginar. La construcción del
    archivo `.xlsx` (pandas/openpyxl) es un adaptador de infraestructura
    (`infrastructure/excel/movimientos_excel_exporter.py`), no responsabilidad
    de este servicio — mismo criterio que `ComprobantePort` para el PDF."""

    def __init__(self, movimiento_repository: MovimientoRepositoryPort):
        self._movimiento_repository = movimiento_repository

    async def ejecutar(self, entrada: ExportarMovimientosExcelInput) -> list[Movimiento]:
        return await self._movimiento_repository.listar_para_exportar(entrada)
