from abc import ABC, abstractmethod


class VerificadorTecnicoPort(ABC):
    @abstractmethod
    async def tiene_rol_mantenimiento(self, usuario_id: str) -> bool: ...
