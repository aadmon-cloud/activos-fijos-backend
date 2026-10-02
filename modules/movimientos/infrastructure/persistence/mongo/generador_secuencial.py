from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from modules.movimientos.application.ports.generador_secuencial import GeneradorSecuencialPort
from shared.application.persistence.unit_of_work import UnitOfWorkPort

COLECCION = "contadores_movimientos"


class MongoGeneradorSecuencial(GeneradorSecuencialPort):
    """`find_one_and_update` con `$inc` es atómico incluso bajo concurrencia —
    corrige la race condition del legacy (`find_one` + `update_one` separados)."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[COLECCION]

    async def siguiente(
        self,
        nombre: str,
        prefijo: str,
        ancho: int = 3,
        uow: UnitOfWorkPort | None = None,
    ) -> str:
        session = uow.session if uow else None
        doc = await self._col.find_one_and_update(
            {"nombre": nombre},
            {"$inc": {"ultimo_numero": 1}, "$setOnInsert": {"prefijo": prefijo}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        return f"{doc['prefijo']}-{doc['ultimo_numero']:0{ancho}d}"
