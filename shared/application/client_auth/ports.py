from abc import ABC, abstractmethod

from shared.application.client_auth.dto import IdentidadAutenticada


class VerificadorTokenIdentidadPort(ABC):
    @abstractmethod
    def verificar(self, token: str) -> IdentidadAutenticada: ...
