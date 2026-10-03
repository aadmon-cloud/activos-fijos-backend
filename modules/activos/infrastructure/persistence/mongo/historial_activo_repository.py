from bson import ObjectId

from modules.activos.application.ports.historial_activo_repository import (
    HistorialActivoRepositoryPort,
)
from modules.activos.domain.entities import EntradaHistorialActivo
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "activos_historial"


def _audit_a_doc(audit: AuditPersona) -> dict:
    return {"id_persona": audit.id_persona, "nombre": audit.nombre, "fecha": audit.fecha}


def _doc_a_audit(doc: dict) -> AuditPersona:
    return AuditPersona(id_persona=doc["id_persona"], nombre=doc["nombre"], fecha=doc["fecha"])


def _entidad_a_doc(entrada: EntradaHistorialActivo) -> dict:
    return {
        "activo_id": ObjectId(entrada.activo_id),
        "campo": entrada.campo,
        "valor_anterior": entrada.valor_anterior,
        "valor_nuevo": entrada.valor_nuevo,
        "modificado_por": _audit_a_doc(entrada.modificado_por),
    }


def _doc_a_entidad(doc: dict) -> EntradaHistorialActivo:
    return EntradaHistorialActivo(
        id=str(doc["_id"]),
        activo_id=str(doc["activo_id"]),
        campo=doc["campo"],
        valor_anterior=doc["valor_anterior"],
        valor_nuevo=doc["valor_nuevo"],
        modificado_por=_doc_a_audit(doc["modificado_por"]),
    )


async def crear_indices() -> None:
    coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
    await coleccion.create_index(
        [("activo_id", 1), ("modificado_por.fecha", -1)], name="idx_activo_id_fecha"
    )


class MongoHistorialActivoRepository(HistorialActivoRepositoryPort):
    def __init__(self, collection_name: str = _NOMBRE_COLECCION):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def registrar(self, entrada: EntradaHistorialActivo) -> EntradaHistorialActivo:
        documento = _entidad_a_doc(entrada)
        resultado = await self._collection.insert_one(documento)
        guardado = await self._collection.find_one({"_id": resultado.inserted_id})
        return _doc_a_entidad(guardado)

    async def listar_por_activo(self, activo_id: str) -> list[EntradaHistorialActivo]:
        documentos = (
            await self._collection.find({"activo_id": ObjectId(activo_id)})
            .sort("modificado_por.fecha", -1)
            .to_list(length=None)
        )
        return [_doc_a_entidad(documento) for documento in documentos]
