import logging
import time

from google.api_core.exceptions import GoogleAPICallError, NotFound, PermissionDenied
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class ErrorRecuperacionSecreto(Exception):
    """Raised when a secret cannot be fetched from GCP Secret Manager."""


class GestorSecretosGCP:
    def __init__(self, id_proyecto: str):
        self._cliente = secretmanager.SecretManagerServiceClient()
        self._id_proyecto = id_proyecto

    def obtener_secreto(
        self,
        id_secreto: str,
        id_version: str = "latest",
        reintentos: int = 3,
        retraso: int = 5,
    ) -> str:
        nombre_secreto = (
            f"projects/{self._id_proyecto}/secrets/{id_secreto}/versions/{id_version}"
        )

        for intento in range(reintentos):
            try:
                respuesta = self._cliente.access_secret_version(
                    request={"name": nombre_secreto}
                )
                return respuesta.payload.data.decode("UTF-8")
            except NotFound as exc:
                raise ErrorRecuperacionSecreto(
                    f"El secreto '{id_secreto}' no existe en GCP."
                ) from exc
            except PermissionDenied as exc:
                raise ErrorRecuperacionSecreto(
                    f"No hay permisos para leer el secreto '{id_secreto}'."
                ) from exc
            except GoogleAPICallError as exc:
                if intento < reintentos - 1:
                    logger.warning(
                        "Intento %s fallido leyendo '%s'. Reintentando en %ss.",
                        intento + 1,
                        id_secreto,
                        retraso,
                    )
                    time.sleep(retraso)
                    continue

                raise ErrorRecuperacionSecreto(
                    f"Fallo tras {reintentos} intentos para '{id_secreto}': {exc.message}"
                ) from exc
            except Exception as exc:
                raise ErrorRecuperacionSecreto(
                    f"Error inesperado en Secret Manager: {exc}"
                ) from exc
