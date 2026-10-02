from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.reservas.application.ports.reserva_repository import ReservaRepositoryPort
from modules.reservas.domain.entities.reserva import Reserva
from shared.application.persistence.unit_of_work import UnitOfWorkPort

COLECCION = "reservas_stock"


class MongoReservaRepository(ReservaRepositoryPort):
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[COLECCION]

    async def obtener_por_session_id(self, session_id: str) -> Reserva | None:
        doc = await self._col.find_one({"session_id": session_id})
        return self._doc_a_reserva(doc) if doc else None

    async def crear(self, reserva: Reserva) -> Reserva:
        nuevo_id = ObjectId()
        reserva_con_id = reserva.model_copy(update={"id": str(nuevo_id)})
        doc = self._entidad_a_doc(reserva_con_id)
        doc["_id"] = nuevo_id
        await self._col.insert_one(doc)
        return reserva_con_id

    async def actualizar(
        self, reserva: Reserva, uow: UnitOfWorkPort | None = None
    ) -> Reserva:
        session = uow.session if uow else None
        doc = self._entidad_a_doc(reserva)
        await self._col.replace_one({"_id": ObjectId(reserva.id)}, doc, session=session)
        return reserva

    async def eliminar(self, session_id: str, uow: UnitOfWorkPort | None = None) -> bool:
        session = uow.session if uow else None
        resultado = await self._col.delete_one({"session_id": session_id}, session=session)
        return resultado.deleted_count > 0

    async def listar_activas_por_producto_ubicacion(
        self, producto_codigo: str, ubicacion: str
    ) -> list[Reserva]:
        cursor = self._col.find(
            {
                "items": {
                    "$elemMatch": {"producto_codigo": producto_codigo, "ubicacion": ubicacion}
                }
            }
        )
        docs = await cursor.to_list(length=None)
        return [self._doc_a_reserva(doc) for doc in docs]

    def _entidad_a_doc(self, reserva: Reserva) -> dict:
        doc = reserva.model_dump(exclude={"id"})
        doc["creado_por"]["id_persona"] = ObjectId(reserva.creado_por.id_persona)
        if reserva.actualizado_por:
            doc["actualizado_por"]["id_persona"] = ObjectId(reserva.actualizado_por.id_persona)
        return doc

    def _doc_a_reserva(self, doc: dict) -> Reserva:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        doc["creado_por"]["id_persona"] = str(doc["creado_por"]["id_persona"])
        if doc.get("actualizado_por"):
            doc["actualizado_por"]["id_persona"] = str(doc["actualizado_por"]["id_persona"])
        return Reserva(**doc)
