from abc import ABC, abstractmethod


class ResolutorDestinatariosPort(ABC):
    @abstractmethod
    async def resolver(self, destinatarios: list[str]) -> list[str]:
        """Correos de los destinatarios pedidos ("usuario:<id>", "rol:<rol>", "area:<id>" o un correo).

        Solo usuarios activos; sin repetidos. Un destinatario que no se entiende se ignora.
        """
