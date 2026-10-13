from bson import ObjectId

from modules.notificaciones.application.ports.notificacion_repository import (
    NotificacionRepositoryPort,
)
from modules.notificaciones.domain.entities import EstadoNotificacion, Notificacion
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "notificaciones"


def _entidad_a_doc(notificacion: Notificacion) -> dict:
    return {
        "destinatarios": notificacion.destinatarios,
        "correos": notificacion.correos,
        "asunto": notificacion.asunto,
        "cuerpo": notificacion.cuerpo,
        "estado": notificacion.estado.value,
        "detalle": notificacion.detalle,
        "intentos": notificacion.intentos,
        "creada_en": notificacion.creada_en,
        "actualizada_en": notificacion.actualizada_en,
    }


def _doc_a_entidad(doc: dict) -> Notificacion:
    return Notificacion(
        id=str(doc["_id"]),
        destinatarios=doc.get("destinatarios", []),
        correos=doc.get("correos", []),
        asunto=doc["asunto"],
        cuerpo=doc["cuerpo"],
        estado=EstadoNotificacion(doc["estado"]),
        detalle=doc.get("detalle"),
        intentos=doc.get("intentos", 1),
        creada_en=doc["creada_en"],
        actualizada_en=doc["actualizada_en"],
    )


def _filtro(estado: EstadoNotificacion | None) -> dict:
    return {"estado": estado.value} if estado else {}


async def crear_indices() -> None:
    coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
    await coleccion.create_index("estado", name="idx_estado")
    await coleccion.create_index("creada_en", name="idx_creada_en")


class MongoNotificacionRepository(NotificacionRepositoryPort):
    def __init__(self, collection_name: str = _NOMBRE_COLECCION):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, notificacion: Notificacion) -> Notificacion:
        documento = _entidad_a_doc(notificacion)

        if notificacion.id is None:
            resultado = await self._collection.insert_one(documento)
            id_documento = resultado.inserted_id
        else:
            id_documento = ObjectId(notificacion.id)
            await self._collection.replace_one({"_id": id_documento}, documento)

        guardado = await self._collection.find_one({"_id": id_documento})
        return _doc_a_entidad(guardado)

    async def obtener_por_id(self, id_notificacion: str) -> Notificacion | None:
        doc = await self._collection.find_one({"_id": ObjectId(id_notificacion)})
        return _doc_a_entidad(doc) if doc else None

    async def listar(
        self, estado: EstadoNotificacion | None, skip: int, limit: int
    ) -> list[Notificacion]:
        documentos = (
            await self._collection.find(_filtro(estado))
            .sort("_id", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=None)
        )
        return [_doc_a_entidad(documento) for documento in documentos]

    async def contar(self, estado: EstadoNotificacion | None) -> int:
        return await self._collection.count_documents(_filtro(estado))
