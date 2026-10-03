from datetime import UTC, datetime, timedelta

from jose import jwt

from config.settings import settings
from modules.usuarios.application.ports.emisor_token import EmisorTokenPort
from modules.usuarios.domain.entities import Usuario


class JWTEmisorToken(EmisorTokenPort):
    def emitir(self, usuario: Usuario) -> str:
        payload = {
            "sub": usuario.id,
            "email": usuario.email,
            "nombre": f"{usuario.nombre} {usuario.apellido}".strip(),
            "rol": usuario.rol.value,
            "area_id": usuario.area_id,
            "exp": datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
