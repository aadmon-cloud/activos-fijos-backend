from jose import JWTError, jwt

from config.settings import settings
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.application.user_auth.errors import TokenUsuarioInvalidoError
from shared.application.user_auth.ports import VerificadorTokenUsuarioPort


class VerificadorTokenUsuarioJWT(VerificadorTokenUsuarioPort):
    def verificar(self, token: str) -> IdentidadUsuarioAutenticada:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except JWTError as exc:
            raise TokenUsuarioInvalidoError(detalle=str(exc)) from exc

        id_usuario = payload.get("sub")
        email = payload.get("email")
        nombre = payload.get("nombre")
        rol = payload.get("rol")
        if not id_usuario or not email or not nombre or not rol:
            raise TokenUsuarioInvalidoError(detalle="Faltan claims obligatorios en el token.")

        return IdentidadUsuarioAutenticada(
            id_usuario=id_usuario,
            email=email,
            nombre=nombre,
            rol=rol,
            area_id=payload.get("area_id"),
        )
