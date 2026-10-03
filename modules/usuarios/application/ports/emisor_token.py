from abc import ABC, abstractmethod

from modules.usuarios.domain.entities import Usuario


class EmisorTokenPort(ABC):
    @abstractmethod
    def emitir(self, usuario: Usuario) -> str: ...
