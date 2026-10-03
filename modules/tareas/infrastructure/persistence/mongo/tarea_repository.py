from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.tareas.domain.entities import Tarea
from shared.infrastructure.persistence.mongo.database import mongo_manager


def _entidad_a_doc(tarea: Tarea) -> dict:
    return {
        "titulo": tarea.titulo,
        "completada": tarea.completada,
        "fecha_creacion": tarea.fecha_creacion,
    }


def _doc_a_entidad(doc: dict) -> Tarea:
    return Tarea(
        id=str(doc["_id"]),
        titulo=doc["titulo"],
        completada=doc["completada"],
        fecha_creacion=doc["fecha_creacion"],
    )


class MongoTareaRepository(TareaRepositoryPort):
    def __init__(self, collection_name: str = "tareas"):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, tarea: Tarea) -> Tarea:
        resultado = await self._collection.insert_one(_entidad_a_doc(tarea))
        documento = await self._collection.find_one({"_id": resultado.inserted_id})
        return _doc_a_entidad(documento)

    async def listar(self) -> list[Tarea]:
        documentos = (
            await self._collection.find({})
            .sort("fecha_creacion", -1)
            .to_list(length=None)
        )
        return [_doc_a_entidad(documento) for documento in documentos]
