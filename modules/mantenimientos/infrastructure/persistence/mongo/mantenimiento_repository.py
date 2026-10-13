from datetime import datetime
from decimal import Decimal

from bson import ObjectId
from bson.decimal128 import Decimal128

from modules.mantenimientos.application.ports.mantenimiento_repository import (
    MantenimientoRepositoryPort,
)
from modules.mantenimientos.domain.entities import (
    ArchivoMantenimiento,
    EstadoMantenimiento,
    Mantenimiento,
    TipoMantenimiento,
)
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "mantenimientos"


def _audit_a_doc(audit: AuditPersona | None) -> dict | None:
    if audit is None:
        return None
    return {"id_persona": audit.id_persona, "nombre": audit.nombre, "fecha": audit.fecha}


def _doc_a_audit(doc: dict | None) -> AuditPersona | None:
    if doc is None:
        return None
    return AuditPersona(id_persona=doc["id_persona"], nombre=doc["nombre"], fecha=doc["fecha"])


def _archivo_a_doc(archivo: ArchivoMantenimiento) -> dict:
    return {"archivo_id": archivo.archivo_id, "nombre": archivo.nombre}


def _doc_a_archivo(doc: dict) -> ArchivoMantenimiento:
    return ArchivoMantenimiento(archivo_id=doc["archivo_id"], nombre=doc["nombre"])


def _entidad_a_doc(mantenimiento: Mantenimiento) -> dict:
    return {
        "activo_id": ObjectId(mantenimiento.activo_id),
        "solicitud_id": (
            ObjectId(mantenimiento.solicitud_id) if mantenimiento.solicitud_id else None
        ),
        "tipo": mantenimiento.tipo.value,
        "tecnico_responsable_id": ObjectId(mantenimiento.tecnico_responsable_id),
        "fecha": mantenimiento.fecha,
        "observaciones": mantenimiento.observaciones,
        "costo": Decimal128(mantenimiento.costo) if mantenimiento.costo is not None else None,
        "documentos": [_archivo_a_doc(a) for a in mantenimiento.documentos],
        "evidencias": [_archivo_a_doc(a) for a in mantenimiento.evidencias],
        "estado": mantenimiento.estado.value,
        "frecuencia_dias": mantenimiento.frecuencia_dias,
        "proxima_fecha_sugerida": mantenimiento.proxima_fecha_sugerida,
        "alerta_enviada": mantenimiento.alerta_enviada,
        "creado_por": _audit_a_doc(mantenimiento.creado_por),
        "actualizado_por": _audit_a_doc(mantenimiento.actualizado_por),
    }


def _doc_a_entidad(doc: dict) -> Mantenimiento:
    costo = doc.get("costo")
    return Mantenimiento(
        id=str(doc["_id"]),
        activo_id=str(doc["activo_id"]),
        solicitud_id=str(doc["solicitud_id"]) if doc.get("solicitud_id") else None,
        tipo=TipoMantenimiento(doc["tipo"]),
        tecnico_responsable_id=str(doc["tecnico_responsable_id"]),
        fecha=doc["fecha"],
        observaciones=doc.get("observaciones"),
        costo=costo.to_decimal() if isinstance(costo, Decimal128) else None,
        documentos=[_doc_a_archivo(a) for a in doc.get("documentos", [])],
        evidencias=[_doc_a_archivo(a) for a in doc.get("evidencias", [])],
        estado=EstadoMantenimiento(doc["estado"]),
        frecuencia_dias=doc.get("frecuencia_dias"),
        proxima_fecha_sugerida=doc.get("proxima_fecha_sugerida"),
        alerta_enviada=doc.get("alerta_enviada", False),
        creado_por=_doc_a_audit(doc["creado_por"]),
        actualizado_por=_doc_a_audit(doc.get("actualizado_por")),
    )


def _filtro_comun(
    activo_id: str | None,
    tecnico_responsable_id: str | None,
    estado: EstadoMantenimiento | None,
    tipo: TipoMantenimiento | None,
    solicitud_id: str | None,
) -> dict:
    filtro: dict = {}
    if activo_id:
        filtro["activo_id"] = ObjectId(activo_id)
    if tecnico_responsable_id:
        filtro["tecnico_responsable_id"] = ObjectId(tecnico_responsable_id)
    if estado:
        filtro["estado"] = estado.value
    if tipo:
        filtro["tipo"] = tipo.value
    if solicitud_id:
        filtro["solicitud_id"] = ObjectId(solicitud_id)
    return filtro


async def crear_indices() -> None:
    coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
    await coleccion.create_index("activo_id", name="idx_activo_id")
    await coleccion.create_index("estado", name="idx_estado")
    await coleccion.create_index("tecnico_responsable_id", name="idx_tecnico_responsable_id")
    await coleccion.create_index("solicitud_id", name="idx_solicitud_id")
    await coleccion.create_index("proxima_fecha_sugerida", name="idx_proxima_fecha_sugerida")


class MongoMantenimientoRepository(MantenimientoRepositoryPort):
    def __init__(self, collection_name: str = _NOMBRE_COLECCION):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, mantenimiento: Mantenimiento) -> Mantenimiento:
        documento = _entidad_a_doc(mantenimiento)

        if mantenimiento.id is None:
            resultado = await self._collection.insert_one(documento)
            id_documento = resultado.inserted_id
        else:
            id_documento = ObjectId(mantenimiento.id)
            await self._collection.replace_one({"_id": id_documento}, documento)

        guardado = await self._collection.find_one({"_id": id_documento})
        return _doc_a_entidad(guardado)

    async def guardar_varios(self, mantenimientos: list[Mantenimiento]) -> list[Mantenimiento]:
        if not mantenimientos:
            return []

        resultado = await self._collection.insert_many(
            [_entidad_a_doc(mantenimiento) for mantenimiento in mantenimientos]
        )
        documentos = await self._collection.find({"_id": {"$in": resultado.inserted_ids}}).to_list(
            length=None
        )
        por_id = {documento["_id"]: documento for documento in documentos}

        # Mismo orden en que se pidieron guardar.
        return [_doc_a_entidad(por_id[id_documento]) for id_documento in resultado.inserted_ids]

    async def obtener_por_id(self, id_mantenimiento: str) -> Mantenimiento | None:
        doc = await self._collection.find_one({"_id": ObjectId(id_mantenimiento)})
        return _doc_a_entidad(doc) if doc else None

    async def listar(
        self,
        activo_id: str | None,
        tecnico_responsable_id: str | None,
        estado: EstadoMantenimiento | None,
        tipo: TipoMantenimiento | None,
        solicitud_id: str | None,
        skip: int,
        limit: int,
    ) -> list[Mantenimiento]:
        filtro = _filtro_comun(activo_id, tecnico_responsable_id, estado, tipo, solicitud_id)
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
        activo_id: str | None,
        tecnico_responsable_id: str | None,
        estado: EstadoMantenimiento | None,
        tipo: TipoMantenimiento | None,
        solicitud_id: str | None,
    ) -> int:
        filtro = _filtro_comun(activo_id, tecnico_responsable_id, estado, tipo, solicitud_id)
        return await self._collection.count_documents(filtro)

    async def listar_pendientes_de_alerta(self, limite_fecha: datetime) -> list[Mantenimiento]:
        filtro = {
            "estado": EstadoMantenimiento.COMPLETADO.value,
            "alerta_enviada": False,
            "proxima_fecha_sugerida": {"$ne": None, "$lte": limite_fecha},
        }
        documentos = await self._collection.find(filtro).to_list(length=None)
        return [_doc_a_entidad(documento) for documento in documentos]
