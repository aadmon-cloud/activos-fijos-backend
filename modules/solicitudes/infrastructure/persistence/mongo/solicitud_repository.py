from bson import ObjectId

from modules.solicitudes.application.ports.solicitud_repository import SolicitudRepositoryPort
from modules.solicitudes.domain.entities import (
    EntradaSeguimiento,
    EstadoSolicitud,
    PrioridadSolicitud,
    Solicitud,
    TipoSolicitud,
)
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "solicitudes"


def _audit_a_doc(audit: AuditPersona | None) -> dict | None:
    if audit is None:
        return None
    return {"id_persona": audit.id_persona, "nombre": audit.nombre, "fecha": audit.fecha}


def _doc_a_audit(doc: dict | None) -> AuditPersona | None:
    if doc is None:
        return None
    return AuditPersona(id_persona=doc["id_persona"], nombre=doc["nombre"], fecha=doc["fecha"])


def _seguimiento_a_doc(entrada: EntradaSeguimiento) -> dict:
    return {
        "autor": _audit_a_doc(entrada.autor),
        "comentario": entrada.comentario,
        "estado_anterior": entrada.estado_anterior,
        "estado_nuevo": entrada.estado_nuevo,
    }


def _doc_a_seguimiento(doc: dict) -> EntradaSeguimiento:
    return EntradaSeguimiento(
        autor=_doc_a_audit(doc["autor"]),
        comentario=doc["comentario"],
        estado_anterior=doc.get("estado_anterior"),
        estado_nuevo=doc.get("estado_nuevo"),
    )


def _entidad_a_doc(solicitud: Solicitud) -> dict:
    return {
        "tipo": solicitud.tipo.value,
        "activo_id": ObjectId(solicitud.activo_id),
        "descripcion": solicitud.descripcion,
        "prioridad": solicitud.prioridad.value,
        "evidencias": solicitud.evidencias,
        "estado": solicitud.estado.value,
        "rol_asignado": solicitud.rol_asignado,
        "area_id": ObjectId(solicitud.area_id) if solicitud.area_id else None,
        "seguimiento": [_seguimiento_a_doc(e) for e in solicitud.seguimiento],
        "creado_por": _audit_a_doc(solicitud.creado_por),
        "actualizado_por": _audit_a_doc(solicitud.actualizado_por),
    }


def _doc_a_entidad(doc: dict) -> Solicitud:
    return Solicitud(
        id=str(doc["_id"]),
        tipo=TipoSolicitud(doc["tipo"]),
        activo_id=str(doc["activo_id"]),
        descripcion=doc["descripcion"],
        prioridad=PrioridadSolicitud(doc["prioridad"]),
        evidencias=doc.get("evidencias", []),
        estado=EstadoSolicitud(doc["estado"]),
        rol_asignado=doc.get("rol_asignado"),
        area_id=str(doc["area_id"]) if doc.get("area_id") else None,
        seguimiento=[_doc_a_seguimiento(e) for e in doc.get("seguimiento", [])],
        creado_por=_doc_a_audit(doc["creado_por"]),
        actualizado_por=_doc_a_audit(doc.get("actualizado_por")),
    )


async def crear_indices() -> None:
    coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
    await coleccion.create_index("activo_id", name="idx_activo_id")
    await coleccion.create_index("estado", name="idx_estado")
    await coleccion.create_index("rol_asignado", name="idx_rol_asignado")
    await coleccion.create_index("area_id", name="idx_area_id")
    await coleccion.create_index("creado_por.id_persona", name="idx_creado_por_id")


class MongoSolicitudRepository(SolicitudRepositoryPort):
    def __init__(self, collection_name: str = _NOMBRE_COLECCION):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, solicitud: Solicitud) -> Solicitud:
        documento = _entidad_a_doc(solicitud)

        if solicitud.id is None:
            resultado = await self._collection.insert_one(documento)
            id_documento = resultado.inserted_id
        else:
            id_documento = ObjectId(solicitud.id)
            await self._collection.replace_one({"_id": id_documento}, documento)

        guardado = await self._collection.find_one({"_id": id_documento})
        return _doc_a_entidad(guardado)

    async def obtener_por_id(self, id_solicitud: str) -> Solicitud | None:
        doc = await self._collection.find_one({"_id": ObjectId(id_solicitud)})
        return _doc_a_entidad(doc) if doc else None

    async def listar(
        self,
        tipo: TipoSolicitud | None,
        estado: EstadoSolicitud | None,
        activo_id: str | None,
        rol_asignado: str | None,
        area_id: str | None,
        creado_por_id: str | None,
        skip: int,
        limit: int,
    ) -> list[Solicitud]:
        filtro: dict = {}
        if tipo:
            filtro["tipo"] = tipo.value
        if estado:
            filtro["estado"] = estado.value
        if activo_id:
            filtro["activo_id"] = ObjectId(activo_id)
        if rol_asignado:
            filtro["rol_asignado"] = rol_asignado
        if area_id:
            filtro["area_id"] = ObjectId(area_id)
        if creado_por_id:
            filtro["creado_por.id_persona"] = creado_por_id

        documentos = (
            await self._collection.find(filtro)
            .sort("_id", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=None)
        )
        return [_doc_a_entidad(documento) for documento in documentos]
