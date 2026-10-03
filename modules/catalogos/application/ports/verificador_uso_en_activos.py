from abc import ABC, abstractmethod


class VerificadorUsoEnActivosPort(ABC):
    @abstractmethod
    async def area_esta_en_uso(self, area_id: str) -> bool: ...

    @abstractmethod
    async def categoria_esta_en_uso(self, categoria_id: str) -> bool: ...

    @abstractmethod
    async def condicion_esta_en_uso(self, condicion_id: str) -> bool: ...

    @abstractmethod
    async def lugar_esta_en_uso(self, lugar_id: str) -> bool: ...
