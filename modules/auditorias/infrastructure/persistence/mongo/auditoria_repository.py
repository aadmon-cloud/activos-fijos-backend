from bson import ObjectId

from modules.auditorias.application.ports.auditoria_repository import AuditoriaRepositoryPort
from modules.auditorias.domain.entities import (
    Auditoria,
    EstadoAuditoria,
    ItemAuditoria,
    ResultadoVerificacion,
)
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "auditorias"


def _audit_a_doc(audit: AuditPersona | None) -> dict | None:
    if audit is None:
        return None
    return {"id_persona": audit.id_persona, "nombre": audit.nombre, "fecha": audit.fecha}


def _doc_a_audit(doc: dict | None) -> AuditPersona | None:
    if doc is None:
        return None
    return AuditPersona(id_persona=doc["id_persona"], nombre=doc["nombre"], fecha=doc["fecha"])


def _item_a_doc(item: ItemAuditoria) -> dict:
    return {
        "activo_id": ObjectId(item.activo_id),
        "nombre": item.nombre,
        "numero_inventario": item.numero_inventario,
        "tipo": item.tipo,
        "descripcion": item.descripcion,
        "serie": item.serie,
        "estado_ciclo_vida_al_inicio": item.estado_ciclo_vida_al_inicio,
        "resultado": item.resultado.value if item.resultado else None,
        "observacion": item.observacion,
        "verificado_en": item.verificado_en,
    }


def _doc_a_item(doc: dict) -> ItemAuditoria:
    return ItemAuditoria(
        activo_id=str(doc["activo_id"]),
        nombre=doc["nombre"],
        numero_inventario=doc["numero_inventario"],
        tipo=doc["tipo"],
        descripcion=doc.get("descripcion"),
        serie=doc.get("serie"),
        estado_ciclo_vida_al_inicio=doc["estado_ciclo_vida_al_inicio"],
        resultado=ResultadoVerificacion(doc["resultado"]) if doc.get("resultado") else None,
        observacion=doc.get("observacion"),
        verificado_en=doc.get("verificado_en"),
    )


def _entidad_a_doc(auditoria: Auditoria) -> dict:
    return {
        "usuario_auditado_id": ObjectId(auditoria.usuario_auditado_id),
        "estado": auditoria.estado.value,
        "items": [_item_a_doc(item) for item in auditoria.items],
        "fecha_cierre": auditoria.fecha_cierre,
        "pdf_archivo_id": auditoria.pdf_archivo_id,
        "detalle_error_notificacion": auditoria.detalle_error_notificacion,
        "creado_por": _audit_a_doc(auditoria.creado_por),
        "actualizado_por": _audit_a_doc(auditoria.actualizado_por),
    }


def _doc_a_entidad(doc: dict) -> Auditoria:
    return Auditoria(
        id=str(doc["_id"]),
        usuario_auditado_id=str(doc["usuario_auditado_id"]),
        estado=EstadoAuditoria(doc["estado"]),
        items=[_doc_a_item(item) for item in doc.get("items", [])],
        fecha_cierre=doc.get("fecha_cierre"),
        pdf_archivo_id=doc.get("pdf_archivo_id"),
        detalle_error_notificacion=doc.get("detalle_error_notificacion"),
        creado_por=_doc_a_audit(doc["creado_por"]),
        actualizado_por=_doc_a_audit(doc.get("actualizado_por")),
    )


def _construir_filtro(
    usuario_auditado_id: str | None,
    estado: EstadoAuditoria | None,
    creado_por_id: str | None,
) -> dict:
    filtro: dict = {}
    if usuario_auditado_id:
        filtro["usuario_auditado_id"] = ObjectId(usuario_auditado_id)
    if estado:
        filtro["estado"] = estado.value
    if creado_por_id:
        filtro["creado_por.id_persona"] = creado_por_id
    return filtro


async def crear_indices() -> None:
    coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
    await coleccion.create_index("usuario_auditado_id", name="idx_usuario_auditado_id")
    await coleccion.create_index("estado", name="idx_estado")
    await coleccion.create_index("creado_por.id_persona", name="idx_creado_por_id")


class MongoAuditoriaRepository(AuditoriaRepositoryPort):
    def __init__(self, collection_name: str = _NOMBRE_COLECCION):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, auditoria: Auditoria) -> Auditoria:
        documento = _entidad_a_doc(auditoria)

        if auditoria.id is None:
            resultado = await self._collection.insert_one(documento)
            id_documento = resultado.inserted_id
        else:
            id_documento = ObjectId(auditoria.id)
            await self._collection.replace_one({"_id": id_documento}, documento)

        guardado = await self._collection.find_one({"_id": id_documento})
        return _doc_a_entidad(guardado)

    async def obtener_por_id(self, id_auditoria: str) -> Auditoria | None:
        doc = await self._collection.find_one({"_id": ObjectId(id_auditoria)})
        return _doc_a_entidad(doc) if doc else None

    async def listar(
        self,
        usuario_auditado_id: str | None,
        estado: EstadoAuditoria | None,
        creado_por_id: str | None,
        skip: int,
        limit: int,
    ) -> list[Auditoria]:
        filtro = _construir_filtro(usuario_auditado_id, estado, creado_por_id)
        documentos = (
            await self._collection.find(filtro)
            .sort("_id", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=None)
        )
        return [_doc_a_entidad(documento) for documento in documentos]

    async def contar(
        self,
        usuario_auditado_id: str | None,
        estado: EstadoAuditoria | None,
        creado_por_id: str | None,
    ) -> int:
        filtro = _construir_filtro(usuario_auditado_id, estado, creado_por_id)
        return await self._collection.count_documents(filtro)
