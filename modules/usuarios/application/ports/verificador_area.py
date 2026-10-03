from abc import ABC, abstractmethod


class VerificadorAreaPort(ABC):
    @abstractmethod
    async def existe(self, area_id: str) -> bool: ...
