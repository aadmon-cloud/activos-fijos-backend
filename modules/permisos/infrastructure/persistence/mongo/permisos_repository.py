from bson import ObjectId

from modules.permisos.application.ports.permisos_repository import PermisosRolRepositoryPort
from modules.permisos.domain.entities import AccionPermiso, CambioPermiso, PermisosRol
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager
from shared.infrastructure.security.consulta_permisos_rol_mongo import consulta_permisos_rol

_COLECCION_PERMISOS = "permisos_rol"
_COLECCION_HISTORIAL = "permisos_historial"


def _audit_a_doc(audit: AuditPersona | None) -> dict | None:
    if audit is None:
        return None
    return {"id_persona": audit.id_persona, "nombre": audit.nombre, "fecha": audit.fecha}


def _doc_a_audit(doc: dict | None) -> AuditPersona | None:
    if doc is None:
        return None
    return AuditPersona(id_persona=doc["id_persona"], nombre=doc["nombre"], fecha=doc["fecha"])


def _permisos_a_doc(permisos_rol: PermisosRol) -> dict:
    return {
        "rol": permisos_rol.rol,
        "permisos": list(permisos_rol.permisos),
        "creado_por": _audit_a_doc(permisos_rol.creado_por),
        "actualizado_por": _audit_a_doc(permisos_rol.actualizado_por),
    }


def _doc_a_permisos(doc: dict) -> PermisosRol:
    return PermisosRol(
        id=str(doc["_id"]),
        rol=doc["rol"],
        permisos=tuple(doc.get("permisos", [])),
        creado_por=_doc_a_audit(doc["creado_por"]),
        actualizado_por=_doc_a_audit(doc.get("actualizado_por")),
    )


def _cambio_a_doc(cambio: CambioPermiso) -> dict:
    return {
        "rol": cambio.rol,
        "permiso": cambio.permiso,
        "accion": cambio.accion.value,
        "por": _audit_a_doc(cambio.por),
    }


def _doc_a_cambio(doc: dict) -> CambioPermiso:
    return CambioPermiso(
        id=str(doc["_id"]),
        rol=doc["rol"],
        permiso=doc["permiso"],
        accion=AccionPermiso(doc["accion"]),
        por=_doc_a_audit(doc["por"]),
    )


async def crear_indices() -> None:
    base = mongo_manager.get_database()
    await base[_COLECCION_PERMISOS].create_index("rol", name="uq_rol", unique=True)
    await base[_COLECCION_HISTORIAL].create_index([("rol", 1), ("por.fecha", -1)], name="ix_rol_fecha")
    await base[_COLECCION_HISTORIAL].create_index([("por.fecha", -1)], name="ix_fecha")


class MongoPermisosRolRepository(PermisosRolRepositoryPort):
    @property
    def _permisos(self):
        return mongo_manager.get_database()[_COLECCION_PERMISOS]

    @property
    def _historial(self):
        return mongo_manager.get_database()[_COLECCION_HISTORIAL]

    async def obtener(self, rol: str) -> PermisosRol | None:
        doc = await self._permisos.find_one({"rol": rol})
        return _doc_a_permisos(doc) if doc else None

    async def listar(self) -> list[PermisosRol]:
        documentos = await self._permisos.find({}).to_list(length=None)
        return [_doc_a_permisos(documento) for documento in documentos]

    async def guardar(self, permisos_rol: PermisosRol) -> PermisosRol:
        documento = _permisos_a_doc(permisos_rol)

        if permisos_rol.id is None:
            # Un documento por rol: el indice unico evita duplicados si dos procesos arrancan a la vez.
            await self._permisos.replace_one({"rol": permisos_rol.rol}, documento, upsert=True)
        else:
            await self._permisos.replace_one({"_id": ObjectId(permisos_rol.id)}, documento)

        # La autorizacion de las rutas guarda la matriz en memoria unos segundos: el cambio debe verse ya.
        consulta_permisos_rol.invalidar()

        guardado = await self._permisos.find_one({"rol": permisos_rol.rol})
        return _doc_a_permisos(guardado)

    async def registrar_cambios(self, cambios: list[CambioPermiso]) -> None:
        if cambios:
            await self._historial.insert_many([_cambio_a_doc(cambio) for cambio in cambios])

    async def listar_historial(self, rol: str | None, skip: int, limit: int) -> list[CambioPermiso]:
        filtro = {"rol": rol} if rol else {}
        cursor = self._historial.find(filtro).sort([("por.fecha", -1), ("_id", -1)]).skip(skip).limit(limit)
        return [_doc_a_cambio(documento) for documento in await cursor.to_list(length=limit)]
