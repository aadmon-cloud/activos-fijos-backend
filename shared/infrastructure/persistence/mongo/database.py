import logging
import os
import tempfile
from datetime import UTC

from motor.motor_asyncio import AsyncIOMotorClient

from config.settings import settings
from shared.infrastructure.gcp.secret_manager import GestorSecretosGCP

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.db_name: str = settings.MONGO_DB
        self._temp_cert_path: str | None = None

    def connect(self) -> None:
        if self.client:
            return

        if settings.ENTORNO == "local":
            self._conectar_local()
        else:
            self._conectar_con_certificado_gcp()

    def _conectar_local(self) -> None:
        logger.info("Conectando a MongoDB local (ENTORNO=local, sin TLS/X.509).")
        self.client = AsyncIOMotorClient(
            settings.MONGO_URL,
            tz_aware=True,
            tzinfo=UTC,
            uuidRepresentation="standard",
            serverSelectionTimeoutMS=5000,
        )

    def _conectar_con_certificado_gcp(self) -> None:
        logger.info("Iniciando conexion segura a MongoDB con X.509.")

        if not settings.MONGO_CERT_SECRET_NAME:
            raise ValueError(
                "MONGO_CERT_SECRET_NAME es obligatorio cuando ENTORNO != 'local'."
            )

        try:
            gestor_secretos = GestorSecretosGCP(settings.GCP_PROJECT_ID)
            contenido_certificado = gestor_secretos.obtener_secreto(
                settings.MONGO_CERT_SECRET_NAME
            )

            if not contenido_certificado:
                raise ValueError("El secreto del certificado de Mongo esta vacio.")

            temp_file = tempfile.NamedTemporaryFile(
                suffix=".pem", mode="w", delete=False
            )
            temp_file.write(contenido_certificado)
            temp_file.close()
            self._temp_cert_path = temp_file.name

            self.client = AsyncIOMotorClient(
                settings.MONGO_URL,
                tls=True,
                tlsCertificateKeyFile=self._temp_cert_path,
                authMechanism="MONGODB-X509",
                maxPoolSize=100,
                minPoolSize=10,
                tz_aware=True,
                tzinfo=UTC,
                uuidRepresentation="standard",
                serverSelectionTimeoutMS=5000,
            )
            logger.info("Conexion establecida a MongoDB: %s", self.db_name)
        except Exception:
            if self._temp_cert_path and os.path.exists(self._temp_cert_path):
                os.remove(self._temp_cert_path)
            raise

    def close(self) -> None:
        if self.client:
            self.client.close()
            self.client = None

        if self._temp_cert_path and os.path.exists(self._temp_cert_path):
            os.remove(self._temp_cert_path)
            self._temp_cert_path = None

    def get_database(self):
        return self.client[self.db_name]


mongo_manager = DatabaseManager()
