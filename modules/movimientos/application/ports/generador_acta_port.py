from abc import ABC, abstractmethod
from dataclasses import dataclass

from modules.movimientos.domain.entities import ActaMovimiento, Movimiento, ResultadoChequeo


@dataclass(frozen=True)
class LineaActaPdf:
    """Un activo del acta tal como se imprime: nombre e inventario, resultado del chequeo y observacion."""

    descripcion: str
    resultado: ResultadoChequeo
    observacion: str | None = None


@dataclass(frozen=True)
class DatosActaPdf:
    movimiento: Movimiento
    acta: ActaMovimiento
    lineas: list[LineaActaPdf]

    # Quien retira o devuelve: su sello se imprime pendiente hasta que acepte el acta.
    responsable_nombre: str
    responsable_correo: str


class GeneradorActaPort(ABC):
    @abstractmethod
    async def generar_pdf(self, datos: DatosActaPdf) -> bytes:
        """PDF del acta: datos del movimiento, activos con su resultado y los dos sellos (nombre y correo)."""
