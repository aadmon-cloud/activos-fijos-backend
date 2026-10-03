from bson import ObjectId

from modules.catalogos.application.ports.lugar_repository import LugarRepositoryPort
from modules.catalogos.domain.entities import Lugar, TipoLugar
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "lugares"


def _audit_a_doc(audit: AuditPersona | None) -> dict | None:
    if audit is None:
        return None
    return {"id_persona": audit.id_persona, "nombre": audit.nombre, "fecha": audit.fecha}


def _doc_a_audit(doc: dict | None) -> AuditPersona | None:
    if doc is None:
        return None
    return AuditPersona(id_persona=doc["id_persona"], nombre=doc["nombre"], fecha=doc["fecha"])


def _entidad_a_doc(lugar: Lugar) -> dict:
    return {
        "nombre": lugar.nombre,
        "tipo": lugar.tipo.value,
        "sede_id": ObjectId(lugar.sede_id),
        "creado_por": _audit_a_doc(lugar.creado_por),
        "actualizado_por": _audit_a_doc(lugar.actualizado_por),
    }


def _doc_a_entidad(doc: dict) -> Lugar:
    return Lugar(
        id=str(doc["_id"]),
        nombre=doc["nombre"],
        tipo=TipoLugar(doc["tipo"]),
        sede_id=str(doc["sede_id"]),
        creado_por=_doc_a_audit(doc["creado_por"]),
        actualizado_por=_doc_a_audit(doc.get("actualizado_por")),
    )


async def crear_indices() -> None:
    coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
    await coleccion.create_index(
        [("sede_id", 1), ("nombre", 1)], name="uq_sede_nombre", unique=True
    )
    await coleccion.create_index("sede_id", name="idx_sede_id")


class MongoLugarRepository(LugarRepositoryPort):
    def __init__(self, collection_name: str = _NOMBRE_COLECCION):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, lugar: Lugar) -> Lugar:
        documento = _entidad_a_doc(lugar)

        if lugar.id is None:
            resultado = await self._collection.insert_one(documento)
            id_documento = resultado.inserted_id
        else:
            id_documento = ObjectId(lugar.id)
            await self._collection.replace_one({"_id": id_documento}, documento)

        guardado = await self._collection.find_one({"_id": id_documento})
        return _doc_a_entidad(guardado)

    async def obtener_por_id(self, id_lugar: str) -> Lugar | None:
        doc = await self._collection.find_one({"_id": ObjectId(id_lugar)})
        return _doc_a_entidad(doc) if doc else None

    async def obtener_por_nombre_y_sede(self, sede_id: str, nombre: str) -> Lugar | None:
        doc = await self._collection.find_one(
            {"sede_id": ObjectId(sede_id), "nombre": nombre}
        )
        return _doc_a_entidad(doc) if doc else None

    async def listar(self, sede_id: str | None) -> list[Lugar]:
        filtro: dict = {}
        if sede_id:
            filtro["sede_id"] = ObjectId(sede_id)

        documentos = await self._collection.find(filtro).sort("nombre", 1).to_list(length=None)
        return [_doc_a_entidad(documento) for documento in documentos]

    async def existe_alguno_con_sede(self, sede_id: str) -> bool:
        return await self._collection.find_one({"sede_id": ObjectId(sede_id)}) is not None

    async def eliminar(self, id_lugar: str) -> None:
        await self._collection.delete_one({"_id": ObjectId(id_lugar)})
