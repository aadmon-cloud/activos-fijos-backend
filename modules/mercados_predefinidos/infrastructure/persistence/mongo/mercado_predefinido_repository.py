from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.mercados_predefinidos.application.ports.mercado_predefinido_repository import (
    MercadoPredefinidoRepositoryPort,
)
from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
)

COLECCION = "catalogo_mercados_predefinidos"


class MongoMercadoPredefinidoRepository(MercadoPredefinidoRepositoryPort):
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[COLECCION]

    async def obtener_por_nombre(self, nombre: str) -> MercadoPredefinido | None:
        doc = await self._col.find_one({"nombre": nombre})
        return self._doc_a_mercado(doc) if doc else None

    async def existe_por_nombre(self, nombre: str) -> bool:
        return await self._col.count_documents({"nombre": nombre}, limit=1) > 0

    async def crear(self, mercado: MercadoPredefinido) -> MercadoPredefinido:
        nuevo_id = ObjectId()
        mercado_con_id = mercado.model_copy(update={"id": str(nuevo_id)})
        doc = self._entidad_a_doc(mercado_con_id)
        doc["_id"] = nuevo_id
        await self._col.insert_one(doc)
        return mercado_con_id

    async def actualizar(self, mercado: MercadoPredefinido) -> MercadoPredefinido:
        doc = self._entidad_a_doc(mercado)
        await self._col.replace_one({"_id": ObjectId(mercado.id)}, doc)
        return mercado

    async def listar(self, solo_activos: bool = True) -> list[MercadoPredefinido]:
        filtro = {"activo": True} if solo_activos else {}
        cursor = self._col.find(filtro)
        docs = await cursor.to_list(length=None)
        return [self._doc_a_mercado(doc) for doc in docs]

    def _entidad_a_doc(self, mercado: MercadoPredefinido) -> dict:
        doc = mercado.model_dump(exclude={"id"})
        doc["creado_por"]["id_persona"] = ObjectId(mercado.creado_por.id_persona)
        if mercado.actualizado_por:
            doc["actualizado_por"]["id_persona"] = ObjectId(
                mercado.actualizado_por.id_persona
            )
        return doc

    def _doc_a_mercado(self, doc: dict) -> MercadoPredefinido:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        doc["creado_por"]["id_persona"] = str(doc["creado_por"]["id_persona"])
        if doc.get("actualizado_por"):
            doc["actualizado_por"]["id_persona"] = str(
                doc["actualizado_por"]["id_persona"]
            )
        return MercadoPredefinido(**doc)
