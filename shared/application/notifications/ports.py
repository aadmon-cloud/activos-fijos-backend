from abc import ABC, abstractmethod


class NotificadorPort(ABC):
    @abstractmethod
    async def notificar(self, destinatarios: list[str], asunto: str, cuerpo: str) -> None: ...
