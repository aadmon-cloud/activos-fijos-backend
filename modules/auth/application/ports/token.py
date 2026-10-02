from abc import ABC, abstractmethod
from typing import Any


class TokenPort(ABC):
    @abstractmethod
    def crear_token(self, claims: dict[str, Any]) -> str:
        """Issue a signed token embedding the given claims."""

    @abstractmethod
    def decodificar_token(self, token: str) -> dict[str, Any] | None:
        """Return the claims of a valid token, or None if invalid/expired."""
