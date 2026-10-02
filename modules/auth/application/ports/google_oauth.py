from abc import ABC, abstractmethod

from modules.auth.application.dto.datos_google_usuario_dto import DatosGoogleUsuarioDTO


class GoogleOAuthPort(ABC):
    @abstractmethod
    def construir_url_autorizacion(self) -> str:
        """Retorna la URL de autorización de Google para iniciar el flujo OAuth.

        Raises:
            GoogleOAuthNoConfiguradoError: si faltan credenciales en el servidor.
        """

    @abstractmethod
    async def obtener_datos_usuario(self, code: str) -> DatosGoogleUsuarioDTO:
        """Intercambia el `code` por un access_token y obtiene los datos del usuario.

        Raises:
            GoogleOAuthNoConfiguradoError: si faltan credenciales en el servidor.
            GoogleOAuthError: si el intercambio falla o Google no retorna un email.
        """
