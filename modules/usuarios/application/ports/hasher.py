from abc import ABC, abstractmethod


class HasherPort(ABC):
    @abstractmethod
    def hashear(self, password: str) -> str: ...

    @abstractmethod
    def verificar(self, password: str, password_hash: str) -> bool: ...
