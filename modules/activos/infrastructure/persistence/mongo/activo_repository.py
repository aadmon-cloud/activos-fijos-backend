import re

from bson import ObjectId

from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.domain.entities import Activo, Complemento, EstadoCicloVida, TipoActivo
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "activos"


def _audit_a_doc(audit: AuditPersona | None) -> dict | None:
    if audit is None:
        return None
    return {"id_persona": audit.id_persona, "nombre": audit.nombre, "fecha": audit.fecha}


def _doc_a_audit(doc: dict | None) -> AuditPersona | None:
    if doc is None:
        return None
    return AuditPersona(id_persona=doc["id_persona"], nombre=doc["nombre"], fecha=doc["fecha"])


def _complemento_a_doc(complemento: Complemento) -> dict:
    return {
        "nombre": complemento.nombre,
        "descripcion": complemento.descripcion,
        "cantidad": complemento.cantidad,
        "serie": complemento.serie,
    }


def _doc_a_complemento(doc: dict) -> Complemento:
    return Complemento(
        nombre=doc["nombre"],
        descripcion=doc.get("descripcion"),
        cantidad=doc["cantidad"],
        serie=doc.get("serie"),
    )


def _entidad_a_doc(activo: Activo) -> dict:
    return {
        "nombre": activo.nombre,
        "numero_inventario": activo.numero_inventario,
        "tipo": activo.tipo.value,
        "marca": activo.marca,
        "modelo": activo.modelo,
        "serie": activo.serie,
        "descripcion": activo.descripcion,
        "categoria_id": ObjectId(activo.categoria_id),
        "area_id": ObjectId(activo.area_id),
        "responsable_id": ObjectId(activo.responsable_id),
        "condicion_id": ObjectId(activo.condicion_id),
        "estado_ciclo_vida": activo.estado_ciclo_vida.value,
        "sede_id": ObjectId(activo.sede_id),
        "lugar_id": ObjectId(activo.lugar_id),
        "complementos": [_complemento_a_doc(c) for c in activo.complementos],
        "observaciones": activo.observaciones,
        "foto_url": activo.foto_url,
        "ficha_tecnica_url": activo.ficha_tecnica_url,
        "creado_por": _audit_a_doc(activo.creado_por),
        "actualizado_por": _audit_a_doc(activo.actualizado_por),
    }


def _doc_a_entidad(doc: dict) -> Activo:
    return Activo(
        id=str(doc["_id"]),
        nombre=doc["nombre"],
        numero_inventario=doc["numero_inventario"],
        tipo=TipoActivo(doc["tipo"]),
        marca=doc.get("marca"),
        modelo=doc.get("modelo"),
        serie=doc.get("serie"),
        descripcion=doc.get("descripcion"),
        categoria_id=str(doc["categoria_id"]),
        area_id=str(doc["area_id"]),
        responsable_id=str(doc["responsable_id"]),
        condicion_id=str(doc["condicion_id"]),
        estado_ciclo_vida=EstadoCicloVida(doc["estado_ciclo_vida"]),
        sede_id=str(doc["sede_id"]),
        lugar_id=str(doc["lugar_id"]),
        complementos=[_doc_a_complemento(c) for c in doc.get("complementos", [])],
        observaciones=doc.get("observaciones"),
        foto_url=doc.get("foto_url"),
        ficha_tecnica_url=doc.get("ficha_tecnica_url"),
        creado_por=_doc_a_audit(doc["creado_por"]),
        actualizado_por=_doc_a_audit(doc.get("actualizado_por")),
    )


def _construir_filtro(
    area_id: str | None,
    categoria_id: str | None,
    responsable_id: str | None,
    condicion_id: str | None,
    sede_id: str | None,
    lugar_id: str | None,
    estado_ciclo_vida: EstadoCicloVida | None,
    busqueda: str | None,
) -> dict:
    filtro: dict = {}
    if area_id:
        filtro["area_id"] = ObjectId(area_id)
    if categoria_id:
        filtro["categoria_id"] = ObjectId(categoria_id)
    if responsable_id:
        filtro["responsable_id"] = ObjectId(responsable_id)
    if condicion_id:
        filtro["condicion_id"] = ObjectId(condicion_id)
    if sede_id:
        filtro["sede_id"] = ObjectId(sede_id)
    if lugar_id:
        filtro["lugar_id"] = ObjectId(lugar_id)
    if estado_ciclo_vida:
        filtro["estado_ciclo_vida"] = estado_ciclo_vida.value
    if busqueda:
        # El texto del usuario se escapa: sin esto seria una expresion regular arbitraria
        # (inyeccion y ReDoS).
        patron = {"$regex": re.escape(busqueda), "$options": "i"}
        filtro["$or"] = [
            {"nombre": patron},
            {"numero_inventario": patron},
            {"marca": patron},
            {"modelo": patron},
            {"serie": patron},
        ]

    return filtro


async def crear_indices() -> None:
    coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
    await coleccion.create_index(
        "numero_inventario", name="uq_numero_inventario", unique=True
    )
    await coleccion.create_index("area_id", name="idx_area_id")
    await coleccion.create_index("categoria_id", name="idx_categoria_id")
    await coleccion.create_index("responsable_id", name="idx_responsable_id")
    await coleccion.create_index("condicion_id", name="idx_condicion_id")
    await coleccion.create_index("estado_ciclo_vida", name="idx_estado_ciclo_vida")
    await coleccion.create_index("sede_id", name="idx_sede_id")
    await coleccion.create_index("lugar_id", name="idx_lugar_id")


class MongoActivoRepository(ActivoRepositoryPort):
    def __init__(self, collection_name: str = _NOMBRE_COLECCION):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, activo: Activo) -> Activo:
        documento = _entidad_a_doc(activo)

        if activo.id is None:
            resultado = await self._collection.insert_one(documento)
            id_documento = resultado.inserted_id
        else:
            id_documento = ObjectId(activo.id)
            await self._collection.replace_one({"_id": id_documento}, documento)

        guardado = await self._collection.find_one({"_id": id_documento})
        return _doc_a_entidad(guardado)

    async def obtener_por_id(self, id_activo: str) -> Activo | None:
        doc = await self._collection.find_one({"_id": ObjectId(id_activo)})
        return _doc_a_entidad(doc) if doc else None

    async def obtener_por_numero_inventario(self, numero_inventario: str) -> Activo | None:
        doc = await self._collection.find_one({"numero_inventario": numero_inventario})
        return _doc_a_entidad(doc) if doc else None

    async def listar(
        self,
        area_id: str | None,
        categoria_id: str | None,
        responsable_id: str | None,
        condicion_id: str | None,
        sede_id: str | None,
        lugar_id: str | None,
        estado_ciclo_vida: EstadoCicloVida | None,
        busqueda: str | None,
        skip: int,
        limit: int,
    ) -> list[Activo]:
        filtro = _construir_filtro(
            area_id,
            categoria_id,
            responsable_id,
            condicion_id,
            sede_id,
            lugar_id,
            estado_ciclo_vida,
            busqueda,
        )

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
        area_id: str | None,
        categoria_id: str | None,
        responsable_id: str | None,
        condicion_id: str | None,
        sede_id: str | None,
        lugar_id: str | None,
        estado_ciclo_vida: EstadoCicloVida | None,
        busqueda: str | None,
    ) -> int:
        filtro = _construir_filtro(
            area_id,
            categoria_id,
            responsable_id,
            condicion_id,
            sede_id,
            lugar_id,
            estado_ciclo_vida,
            busqueda,
        )
        return await self._collection.count_documents(filtro)
