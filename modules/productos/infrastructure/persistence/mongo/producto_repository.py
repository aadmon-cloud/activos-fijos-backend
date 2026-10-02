import re

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.entities.producto import Producto
from modules.productos.infrastructure.persistence.mongo.pipelines.producto_pipeline import (
    ProductoPipelineBuilder,
)
from shared.application.persistence.unit_of_work import UnitOfWorkPort

COLECCION = "catalogo_productos"


class MongoProductoRepository(ProductoRepositoryPort):
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[COLECCION]

    async def obtener_por_codigo(self, codigo: str) -> Producto | None:
        doc = await self._col.find_one({"codigo": codigo})
        return self._doc_a_producto(doc) if doc else None

    async def existe_por_codigo(self, codigo: str) -> bool:
        return await self._col.count_documents({"codigo": codigo}, limit=1) > 0

    async def crear(self, producto: Producto) -> Producto:
        nuevo_id = ObjectId()
        producto_con_id = producto.model_copy(update={"id": str(nuevo_id)})
        doc = self._entidad_a_doc(producto_con_id)
        doc["_id"] = nuevo_id
        await self._col.insert_one(doc)
        return producto_con_id

    async def actualizar(
        self, producto: Producto, uow: UnitOfWorkPort | None = None
    ) -> Producto:
        doc = self._entidad_a_doc(producto)
        session = uow.session if uow else None
        await self._col.replace_one({"_id": ObjectId(producto.id)}, doc, session=session)
        return producto

    async def eliminar(self, codigo: str) -> bool:
        resultado = await self._col.delete_one({"codigo": codigo})
        return resultado.deleted_count > 0

    async def listar_paginado(self, pagina: int, limite: int) -> tuple[list[Producto], int]:
        pipeline = (
            ProductoPipelineBuilder()
            .ordenar_por_fecha_creacion_desc()
            .paginar(pagina, limite)
            .construir()
        )
        cursor = self._col.aggregate(pipeline)
        resultados = await cursor.to_list(length=1)

        if not resultados:
            return [], 0

        resultado = resultados[0]
        productos = [self._doc_a_producto(doc) for doc in resultado.get("resultado", [])]
        return productos, resultado.get("total_elementos", 0)

    async def buscar_por_texto(self, texto: str) -> list[Producto]:
        patron = re.escape(texto)
        cursor = self._col.find(
            {
                "$or": [
                    {"nombre": {"$regex": patron, "$options": "i"}},
                    {"codigo": {"$regex": patron, "$options": "i"}},
                    {"descripcion": {"$regex": patron, "$options": "i"}},
                ]
            }
        )
        docs = await cursor.to_list(length=None)
        return [self._doc_a_producto(doc) for doc in docs]

    async def listar_bajo_stock(self) -> list[Producto]:
        cursor = self._col.find({"$expr": {"$lt": ["$stock_actual", "$stock_minimo"]}})
        docs = await cursor.to_list(length=None)
        return [self._doc_a_producto(doc) for doc in docs]

    async def calcular_valor_total(self) -> float:
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "valor_total": {"$sum": {"$multiply": ["$stock_actual", "$precio_unitario"]}},
                }
            }
        ]
        resultados = await self._col.aggregate(pipeline).to_list(length=1)
        return resultados[0]["valor_total"] if resultados else 0.0

    def _entidad_a_doc(self, producto: Producto) -> dict:
        doc = producto.model_dump(exclude={"id"})
        doc["creado_por"]["id_persona"] = ObjectId(producto.creado_por.id_persona)
        if producto.actualizado_por:
            doc["actualizado_por"]["id_persona"] = ObjectId(
                producto.actualizado_por.id_persona
            )
        return doc

    def _doc_a_producto(self, doc: dict) -> Producto:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        doc["creado_por"]["id_persona"] = str(doc["creado_por"]["id_persona"])
        if doc.get("actualizado_por"):
            doc["actualizado_por"]["id_persona"] = str(
                doc["actualizado_por"]["id_persona"]
            )
        return Producto(**doc)
