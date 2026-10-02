from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.ports.storage_repository import StorageRepositoryPort
from modules.movimientos.domain.errors import (
    MovimientoNoEncontradoError,
    PdfFirmadoNoEncontradoError,
)


class ObtenerPdfFirmadoService:
    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        storage_repository: StorageRepositoryPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._storage_repository = storage_repository

    async def ejecutar(self, movimiento_id: str) -> tuple[bytes, str]:
        """Raises:
        MovimientoNoEncontradoError: no existe una salida con ese id.
        PdfFirmadoNoEncontradoError: la salida no tiene un PDF firmado subido todavía.
        """
        movimiento = await self._movimiento_repository.obtener_por_id(movimiento_id)
        if movimiento is None or movimiento.tipo != "salida":
            raise MovimientoNoEncontradoError(movimiento_id)
        if not movimiento.pdf_firmado:
            raise PdfFirmadoNoEncontradoError(movimiento_id)

        contenido = await self._storage_repository.leer(movimiento.pdf_firmado)
        return contenido, movimiento.pdf_nombre or "comprobante.pdf"
