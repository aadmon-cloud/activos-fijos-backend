from bson import ObjectId

from modules.catalogos.application.ports.categoria_repository import CategoriaRepositoryPort
from modules.catalogos.domain.entities import Categoria
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "categorias"


def _audit_a_doc(audit: AuditPersona | None) -> dict | None:
    if audit is None:
        return None
    return {"id_persona": audit.id_persona, "nombre": audit.nombre, "fecha": audit.fecha}


def _doc_a_audit(doc: dict | None) -> AuditPersona | None:
    if doc is None:
        return None
    return AuditPersona(id_persona=doc["id_persona"], nombre=doc["nombre"], fecha=doc["fecha"])


def _entidad_a_doc(categoria: Categoria) -> dict:
    return {
        "nombre": categoria.nombre,
        "descripcion": categoria.descripcion,
        "creado_por": _audit_a_doc(categoria.creado_por),
        "actualizado_por": _audit_a_doc(categoria.actualizado_por),
    }


def _doc_a_entidad(doc: dict) -> Categoria:
    return Categoria(
        id=str(doc["_id"]),
        nombre=doc["nombre"],
        descripcion=doc.get("descripcion"),
        creado_por=_doc_a_audit(doc["creado_por"]),
        actualizado_por=_doc_a_audit(doc.get("actualizado_por")),
    )


async def crear_indices() -> None:
    coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
    await coleccion.create_index("nombre", name="uq_nombre", unique=True)


class MongoCategoriaRepository(CategoriaRepositoryPort):
    def __init__(self, collection_name: str = _NOMBRE_COLECCION):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, categoria: Categoria) -> Categoria:
        documento = _entidad_a_doc(categoria)

        if categoria.id is None:
            resultado = await self._collection.insert_one(documento)
            id_documento = resultado.inserted_id
        else:
            id_documento = ObjectId(categoria.id)
            await self._collection.replace_one({"_id": id_documento}, documento)

        guardado = await self._collection.find_one({"_id": id_documento})
        return _doc_a_entidad(guardado)

    async def obtener_por_id(self, id_categoria: str) -> Categoria | None:
        doc = await self._collection.find_one({"_id": ObjectId(id_categoria)})
        return _doc_a_entidad(doc) if doc else None

    async def obtener_por_nombre(self, nombre: str) -> Categoria | None:
        doc = await self._collection.find_one({"nombre": nombre})
        return _doc_a_entidad(doc) if doc else None

    async def listar(self) -> list[Categoria]:
        documentos = await self._collection.find({}).sort("nombre", 1).to_list(length=None)
        return [_doc_a_entidad(documento) for documento in documentos]

    async def eliminar(self, id_categoria: str) -> None:
        await self._collection.delete_one({"_id": ObjectId(id_categoria)})
