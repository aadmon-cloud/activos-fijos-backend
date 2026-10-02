from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from modules.auth.application.ports.token import TokenPort


class JwtTokenAdapter(TokenPort):
    def __init__(self, secret_key: str, algorithm: str, expira_minutos: int):
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expira_minutos = expira_minutos

    def crear_token(self, claims: dict[str, Any]) -> str:
        ahora = datetime.now(UTC)
        datos = {
            **claims,
            "iat": ahora,
            "exp": ahora + timedelta(minutes=self._expira_minutos),
        }
        return jwt.encode(datos, self._secret_key, algorithm=self._algorithm)

    def decodificar_token(self, token: str) -> dict[str, Any] | None:
        try:
            return jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except JWTError:
            return None
