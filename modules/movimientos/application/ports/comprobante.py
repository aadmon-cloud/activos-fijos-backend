from abc import ABC, abstractmethod

from modules.movimientos.domain.entities.movimiento import Movimiento


class ComprobantePort(ABC):
    @abstractmethod
    async def generar_comprobante_salida(self, movimiento: Movimiento) -> bytes:
        """Render the PDF receipt for this movement (individual or kit) and
        return its raw bytes. `movimiento.tipo` must be "salida"."""
