import google.auth.transport.requests
import google.oauth2.id_token

from shared.application.service_invocation.ports import IProveedorTokenServicio


class ProveedorTokenCloudRunGoogle(IProveedorTokenServicio):
    def __init__(self):
        self._solicitud_autenticacion = google.auth.transport.requests.Request()

    def obtener_token(self, audiencia: str) -> str:
        return google.oauth2.id_token.fetch_id_token(
            self._solicitud_autenticacion,
            audience=audiencia,
        )
