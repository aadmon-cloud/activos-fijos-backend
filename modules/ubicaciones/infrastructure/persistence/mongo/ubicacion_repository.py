from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.ubicaciones.application.ports.ubicacion_repository import UbicacionRepositoryPort
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from shared.application.persistence.unit_of_work import UnitOfWorkPort

COLECCION = "stock_ubicaciones"


class MongoUbicacionRepository(UbicacionRepositoryPort):
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[COLECCION]

    async def obtener(self, producto_codigo: str, ubicacion: str) -> Ubicacion | None:
        doc = await self._col.find_one(
            {"producto_codigo": producto_codigo, "ubicacion": ubicacion}
        )
        return self._doc_a_ubicacion(doc) if doc else None

    async def existe(self, producto_codigo: str, ubicacion: str) -> bool:
        return (
            await self._col.count_documents(
                {"producto_codigo": producto_codigo, "ubicacion": ubicacion}, limit=1
            )
            > 0
        )

    async def listar_por_producto(
        self, producto_codigo: str, uow: UnitOfWorkPort | None = None
    ) -> list[Ubicacion]:
        session = uow.session if uow else None
        cursor = self._col.find({"producto_codigo": producto_codigo}, session=session)
        docs = await cursor.to_list(length=None)
        return [self._doc_a_ubicacion(doc) for doc in docs]

    async def crear(self, ubicacion: Ubicacion, uow: UnitOfWorkPort | None = None) -> Ubicacion:
        session = uow.session if uow else None
        nuevo_id = ObjectId()
        ubicacion_con_id = ubicacion.model_copy(update={"id": str(nuevo_id)})
        doc = self._entidad_a_doc(ubicacion_con_id)
        doc["_id"] = nuevo_id
        await self._col.insert_one(doc, session=session)
        return ubicacion_con_id

    async def actualizar(
        self, ubicacion: Ubicacion, uow: UnitOfWorkPort | None = None
    ) -> Ubicacion:
        session = uow.session if uow else None
        doc = self._entidad_a_doc(ubicacion)
        await self._col.replace_one({"_id": ObjectId(ubicacion.id)}, doc, session=session)
        return ubicacion

    async def eliminar(
        self, producto_codigo: str, ubicacion: str, uow: UnitOfWorkPort | None = None
    ) -> bool:
        session = uow.session if uow else None
        resultado = await self._col.delete_one(
            {"producto_codigo": producto_codigo, "ubicacion": ubicacion}, session=session
        )
        return resultado.deleted_count > 0

    def _entidad_a_doc(self, ubicacion: Ubicacion) -> dict:
        doc = ubicacion.model_dump(exclude={"id"})
        doc["creado_por"]["id_persona"] = ObjectId(ubicacion.creado_por.id_persona)
        if ubicacion.actualizado_por:
            doc["actualizado_por"]["id_persona"] = ObjectId(
                ubicacion.actualizado_por.id_persona
            )
        return doc

    def _doc_a_ubicacion(self, doc: dict) -> Ubicacion:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        doc["creado_por"]["id_persona"] = str(doc["creado_por"]["id_persona"])
        if doc.get("actualizado_por"):
            doc["actualizado_por"]["id_persona"] = str(
                doc["actualizado_por"]["id_persona"]
            )
        return Ubicacion(**doc)
