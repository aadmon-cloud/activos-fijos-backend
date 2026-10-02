from modules.movimientos.application.ports.comprobante import ComprobantePort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.domain.errors import MovimientoNoEncontradoError


class GenerarComprobantePdfService:
    def __init__(
        self, movimiento_repository: MovimientoRepositoryPort, comprobante_port: ComprobantePort
    ):
        self._movimiento_repository = movimiento_repository
        self._comprobante_port = comprobante_port

    async def ejecutar(self, movimiento_id: str) -> bytes:
        """Raises:
        MovimientoNoEncontradoError: no existe una salida con ese id.
        """
        movimiento = await self._movimiento_repository.obtener_por_id(movimiento_id)
        if movimiento is None or movimiento.tipo != "salida":
            raise MovimientoNoEncontradoError(movimiento_id)

        return await self._comprobante_port.generar_comprobante_salida(movimiento)
