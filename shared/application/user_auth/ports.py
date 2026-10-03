from abc import ABC, abstractmethod

from shared.application.user_auth.dto import IdentidadUsuarioAutenticada


class VerificadorTokenUsuarioPort(ABC):
    @abstractmethod
    def verificar(self, token: str) -> IdentidadUsuarioAutenticada: ...
