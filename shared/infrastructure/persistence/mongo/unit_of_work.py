from shared.application.persistence.unit_of_work import UnitOfWorkPort
from shared.infrastructure.persistence.mongo.database import mongo_manager


class MongoUnitOfWork(UnitOfWorkPort):
    def __init__(self):
        self._client = mongo_manager.client
        self._session = None

    async def __aenter__(self):
        if not self._client:
            raise RuntimeError("El cliente de MongoDB no esta inicializado")

        self._session = await self._client.start_session()
        self._session.start_transaction()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                await self._session.abort_transaction()
            else:
                await self._session.commit_transaction()
        finally:
            await self._session.end_session()

    @property
    def session(self):
        return self._session
