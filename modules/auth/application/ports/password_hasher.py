from abc import ABC, abstractmethod


class PasswordHasherPort(ABC):
    @abstractmethod
    def hashear(self, password: str) -> str:
        """Return the hashed representation of a plaintext password."""

    @abstractmethod
    def verificar(self, password: str, password_hash: str) -> bool:
        """Return whether the plaintext password matches the stored hash."""
