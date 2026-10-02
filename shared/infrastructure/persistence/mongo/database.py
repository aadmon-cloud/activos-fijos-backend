import logging

from motor.motor_asyncio import AsyncIOMotorClient

from config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    client: AsyncIOMotorClient = None
    db_name: str = settings.MONGO_DB

    def connect(self):
        if self.client:
            return

        logger.info("Conectando a MongoDB: %s", self.db_name)
        self.client = AsyncIOMotorClient(
            settings.MONGO_URL,
            maxPoolSize=100,
            minPoolSize=10,
            uuidRepresentation="standard",
            serverSelectionTimeoutMS=5000,
            # Sin esto, Motor decodifica fechas de Mongo como datetime "naive"
            # (sin tzinfo), que no se puede comparar con datetime.now(UTC) usado
            # en todo el proyecto (p. ej. Usuario.token_reset_valido) — lanza
            # TypeError: can't compare offset-naive and offset-aware datetimes.
            tz_aware=True,
        )
        logger.info("Conexion a MongoDB establecida.")

    def close(self):
        if self.client:
            self.client.close()
            self.client = None
            logger.info("Cliente MongoDB cerrado.")

    def get_database(self):
        return self.client[self.db_name]


mongo_manager = DatabaseManager()
