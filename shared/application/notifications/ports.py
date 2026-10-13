from abc import ABC, abstractmethod
from dataclasses import dataclass


class NotificadorPort(ABC):
    @abstractmethod
    async def notificar(self, destinatarios: list[str], asunto: str, cuerpo: str) -> None: ...


@dataclass(frozen=True)
class AdjuntoCorreo:
    nombre: str
    contenido: bytes
    tipo_mime: str


class NotificadorConAdjuntoPort(ABC):
    """Separado de NotificadorPort para no ensanchar su contrato (ningun adaptador existente
    necesita adjuntos todavia). Pensado para correos reales con archivos, ej. el PDF de una
    auditoria."""

    @abstractmethod
    async def enviar(
        self,
        destinatarios: list[str],
        asunto: str,
        cuerpo: str,
        adjuntos: list[AdjuntoCorreo],
    ) -> None: ...
