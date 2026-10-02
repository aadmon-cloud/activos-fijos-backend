from modules.auth.application.ports.google_oauth import GoogleOAuthPort


class IniciarLoginGoogleService:
    def __init__(self, google_oauth: GoogleOAuthPort):
        self._google_oauth = google_oauth

    def ejecutar(self) -> str:
        """Retorna la URL a la que redirigir para iniciar el login con Google.

        Raises:
            GoogleOAuthNoConfiguradoError: si faltan credenciales en el servidor.
        """
        return self._google_oauth.construir_url_autorizacion()
