from bson import ObjectId

from modules.catalogos.application.ports.sede_repository import SedeRepositoryPort
from modules.catalogos.domain.entities import Sede
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "sedes"


def _audit_a_doc(audit: AuditPersona | None) -> dict | None:
    if audit is None:
        return None
    return {"id_persona": audit.id_persona, "nombre": audit.nombre, "fecha": audit.fecha}


def _doc_a_audit(doc: dict | None) -> AuditPersona | None:
    if doc is None:
        return None
    return AuditPersona(id_persona=doc["id_persona"], nombre=doc["nombre"], fecha=doc["fecha"])


def _entidad_a_doc(sede: Sede) -> dict:
    return {
        "nombre": sede.nombre,
        "descripcion": sede.descripcion,
        "creado_por": _audit_a_doc(sede.creado_por),
        "actualizado_por": _audit_a_doc(sede.actualizado_por),
    }


def _doc_a_entidad(doc: dict) -> Sede:
    return Sede(
        id=str(doc["_id"]),
        nombre=doc["nombre"],
        descripcion=doc.get("descripcion"),
        creado_por=_doc_a_audit(doc["creado_por"]),
        actualizado_por=_doc_a_audit(doc.get("actualizado_por")),
    )


async def crear_indices() -> None:
    coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
    await coleccion.create_index("nombre", name="uq_nombre", unique=True)


class MongoSedeRepository(SedeRepositoryPort):
    def __init__(self, collection_name: str = _NOMBRE_COLECCION):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, sede: Sede) -> Sede:
        documento = _entidad_a_doc(sede)

        if sede.id is None:
            resultado = await self._collection.insert_one(documento)
            id_documento = resultado.inserted_id
        else:
            id_documento = ObjectId(sede.id)
            await self._collection.replace_one({"_id": id_documento}, documento)

        guardado = await self._collection.find_one({"_id": id_documento})
        return _doc_a_entidad(guardado)

    async def obtener_por_id(self, id_sede: str) -> Sede | None:
        doc = await self._collection.find_one({"_id": ObjectId(id_sede)})
        return _doc_a_entidad(doc) if doc else None

    async def obtener_por_nombre(self, nombre: str) -> Sede | None:
        doc = await self._collection.find_one({"nombre": nombre})
        return _doc_a_entidad(doc) if doc else None

    async def listar(self) -> list[Sede]:
        documentos = await self._collection.find({}).sort("nombre", 1).to_list(length=None)
        return [_doc_a_entidad(documento) for documento in documentos]

    async def eliminar(self, id_sede: str) -> None:
        await self._collection.delete_one({"_id": ObjectId(id_sede)})
