from abc import ABC, abstractmethod


class BuscadorActivosPort(ABC):
    @abstractmethod
    async def buscar_por_codigo(self, codigos: list[str]) -> dict[str, str]:
        """Id de cada activo cuyo codigo (numero de inventario) existe; los demas no aparecen."""
