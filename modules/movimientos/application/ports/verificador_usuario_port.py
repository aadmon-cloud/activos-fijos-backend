from abc import ABC, abstractmethod


class VerificadorUsuarioPort(ABC):
    @abstractmethod
    async def existe(self, usuario_id: str) -> bool: ...
