from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.ejemplo_tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.ejemplo_tareas.domain.entities.tarea import Tarea
from modules.ejemplo_tareas.infrastructure.persistence.mongo.pipelines.tarea_pipeline import (
    TareaPipelineBuilder,
)

COLECCION = "tareas"


class MongoTareaRepository(TareaRepositoryPort):
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[COLECCION]

    async def guardar(self, tarea: Tarea) -> Tarea:
        doc = tarea.model_dump()
        doc["_id"] = doc.pop("id")
        await self._col.insert_one(doc)
        return tarea

    async def obtener_por_id(self, tarea_id: str) -> Tarea | None:
        doc = await self._col.find_one({"_id": tarea_id})
        if doc is None:
            return None
        return self._doc_a_tarea(doc)

    async def listar_paginado(self, pagina: int, limite: int) -> tuple[list[Tarea], int]:
        pipeline = (
            TareaPipelineBuilder()
            .ordenar_por_fecha_creacion_desc()
            .paginar(pagina, limite)
            .construir()
        )
        cursor = self._col.aggregate(pipeline)
        resultados = await cursor.to_list(length=1)

        if not resultados:
            return [], 0

        resultado = resultados[0]
        tareas = [self._doc_a_tarea(doc) for doc in resultado.get("resultado", [])]
        return tareas, resultado.get("total_elementos", 0)

    async def actualizar(self, tarea: Tarea) -> Tarea:
        doc = tarea.model_dump()
        doc["_id"] = doc.pop("id")
        await self._col.replace_one({"_id": tarea.id}, doc)
        return tarea

    def _doc_a_tarea(self, doc: dict) -> Tarea:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        return Tarea(**doc)
