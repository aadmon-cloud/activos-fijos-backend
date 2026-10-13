from abc import ABC, abstractmethod

from modules.movimientos.domain.entities import Movimiento


class GeneradorComprobantePort(ABC):
    @abstractmethod
    async def generar_pdf(
        self, movimiento: Movimiento, activos: list[str], usuario_destino_nombre: str
    ) -> bytes:
        """`activos`: una linea por cada activo que salio (nombre e inventario)."""
