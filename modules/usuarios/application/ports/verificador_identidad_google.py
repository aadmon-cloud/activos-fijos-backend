from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class IdentidadGoogle:
    """Lo unico que el sistema toma de Google: un correo que Google ya verifico."""

    email: str


class VerificadorIdentidadGooglePort(ABC):
    @abstractmethod
    async def verificar(self, credencial: str, nonce: str) -> IdentidadGoogle:
        """Valida el token de identidad de Google (firma, audiencia, vigencia, correo verificado y nonce).

        Raises:
            TokenGoogleInvalidoError: si el token no es valido.
            IngresoConGoogleNoConfiguradoError: si falta el ID de cliente.
        """
