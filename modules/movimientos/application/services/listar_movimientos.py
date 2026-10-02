from shared.application.dto.pagination import RespuestaPaginada

from modules.movimientos.application.dto.listar_movimientos import ListarMovimientosInput
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.domain.entities.movimiento import Movimiento


class ListarMovimientosService:
    def __init__(self, movimiento_repository: MovimientoRepositoryPort):
        self._movimiento_repository = movimiento_repository

    async def ejecutar(self, entrada: ListarMovimientosInput) -> RespuestaPaginada[Movimiento]:
        movimientos, total = await self._movimiento_repository.listar(entrada)
        return RespuestaPaginada.crear(
            items=movimientos, page=entrada.pagina, limit=entrada.limite, total=total
        )
