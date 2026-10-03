from bson import ObjectId

from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.domain.entities import RolUsuario, Usuario
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager


def _audit_a_doc(audit: AuditPersona | None) -> dict | None:
    if audit is None:
        return None
    return {"id_persona": audit.id_persona, "nombre": audit.nombre, "fecha": audit.fecha}


def _doc_a_audit(doc: dict | None) -> AuditPersona | None:
    if doc is None:
        return None
    return AuditPersona(id_persona=doc["id_persona"], nombre=doc["nombre"], fecha=doc["fecha"])


def _entidad_a_doc(usuario: Usuario) -> dict:
    return {
        "email": usuario.email,
        "nombre": usuario.nombre,
        "apellido": usuario.apellido,
        "password_hash": usuario.password_hash,
        "rol": usuario.rol.value,
        "area_id": ObjectId(usuario.area_id) if usuario.area_id else None,
        "telefono": usuario.telefono,
        "identificacion": usuario.identificacion,
        "activo": usuario.activo,
        "creado_por": _audit_a_doc(usuario.creado_por),
        "actualizado_por": _audit_a_doc(usuario.actualizado_por),
    }


def _doc_a_entidad(doc: dict) -> Usuario:
    return Usuario(
        id=str(doc["_id"]),
        email=doc["email"],
        nombre=doc["nombre"],
        apellido=doc["apellido"],
        password_hash=doc["password_hash"],
        rol=RolUsuario(doc["rol"]),
        area_id=str(doc["area_id"]) if doc.get("area_id") else None,
        telefono=doc.get("telefono"),
        identificacion=doc.get("identificacion"),
        activo=doc["activo"],
        creado_por=_doc_a_audit(doc["creado_por"]),
        actualizado_por=_doc_a_audit(doc.get("actualizado_por")),
    )


async def crear_indices() -> None:
    coleccion = mongo_manager.get_database()["usuarios"]
    await coleccion.create_index("email", name="uq_email", unique=True)
    await coleccion.create_index(
        "identificacion", name="uq_identificacion", unique=True, sparse=True
    )
    await coleccion.create_index("area_id", name="idx_area_id")
    await coleccion.create_index("rol", name="idx_rol")


class MongoUsuarioRepository(UsuarioRepositoryPort):
    def __init__(self, collection_name: str = "usuarios"):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, usuario: Usuario) -> Usuario:
        documento = _entidad_a_doc(usuario)

        if usuario.id is None:
            resultado = await self._collection.insert_one(documento)
            id_documento = resultado.inserted_id
        else:
            id_documento = ObjectId(usuario.id)
            await self._collection.replace_one({"_id": id_documento}, documento)

        guardado = await self._collection.find_one({"_id": id_documento})
        return _doc_a_entidad(guardado)

    async def obtener_por_id(self, id_usuario: str) -> Usuario | None:
        doc = await self._collection.find_one({"_id": ObjectId(id_usuario)})
        return _doc_a_entidad(doc) if doc else None

    async def obtener_por_email(self, email: str) -> Usuario | None:
        doc = await self._collection.find_one({"email": email})
        return _doc_a_entidad(doc) if doc else None

    async def obtener_por_identificacion(self, identificacion: str) -> Usuario | None:
        doc = await self._collection.find_one({"identificacion": identificacion})
        return _doc_a_entidad(doc) if doc else None

    async def listar(self, busqueda: str | None, skip: int, limit: int) -> list[Usuario]:
        filtro: dict = {}
        if busqueda:
            patron = {"$regex": busqueda, "$options": "i"}
            filtro["$or"] = [
                {"nombre": patron},
                {"apellido": patron},
                {"email": patron},
                {"identificacion": patron},
            ]

        documentos = (
            await self._collection.find(filtro)
            .sort("_id", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=None)
        )
        return [_doc_a_entidad(documento) for documento in documentos]
