from datetime import datetime

from bson import ObjectId
from pymongo.errors import OperationFailure

from modules.movimientos.application.ports.movimiento_repository import (
    MovimientoRepositoryPort,
    ParaMiMovimiento,
    VisibilidadMovimiento,
)
from modules.movimientos.domain.entities import (
    ESTADOS_ITEM_ACTIVOS,
    ActaMovimiento,
    ChequeoItem,
    EstadoItemMovimiento,
    EstadoMovimiento,
    EtapaRechazo,
    ItemMovimiento,
    LineaActa,
    Movimiento,
    ResultadoChequeo,
    SelloActa,
    SentidoPrestamo,
    TipoActa,
    TipoMovimiento,
)
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "movimientos"
_ESTADOS_ITEM_ACTIVOS = [estado.value for estado in ESTADOS_ITEM_ACTIVOS]

# Items que esperan una accion de administracion: confirmar una salida, aprobar una baja o recibir una devolucion.
_ESTADOS_ITEM_QUE_ESPERAN_ADMIN = [
    EstadoItemMovimiento.PENDIENTE_ADMIN.value,
    EstadoItemMovimiento.DEVOLUCION_SOLICITADA.value,
]


def _audit_a_doc(audit: AuditPersona | None) -> dict | None:
    if audit is None:
        return None
    return {"id_persona": audit.id_persona, "nombre": audit.nombre, "fecha": audit.fecha}


def _doc_a_audit(doc: dict | None) -> AuditPersona | None:
    if doc is None:
        return None
    return AuditPersona(id_persona=doc["id_persona"], nombre=doc["nombre"], fecha=doc["fecha"])


def _chequeo_a_doc(chequeo: ChequeoItem | None) -> dict | None:
    if chequeo is None:
        return None
    return {
        "resultado": chequeo.resultado.value,
        "observacion": chequeo.observacion,
        "por": _audit_a_doc(chequeo.por),
    }


def _doc_a_chequeo(doc: dict | None) -> ChequeoItem | None:
    if doc is None:
        return None
    return ChequeoItem(
        resultado=ResultadoChequeo(doc["resultado"]),
        observacion=doc.get("observacion"),
        por=_doc_a_audit(doc["por"]),
    )


def _sello_a_doc(sello: SelloActa | None) -> dict | None:
    if sello is None:
        return None
    return {"id_persona": sello.id_persona, "nombre": sello.nombre, "correo": sello.correo, "fecha": sello.fecha}


def _doc_a_sello(doc: dict | None) -> SelloActa | None:
    if doc is None:
        return None
    return SelloActa(
        id_persona=doc["id_persona"], nombre=doc["nombre"], correo=doc["correo"], fecha=doc["fecha"]
    )


def _acta_a_doc(acta: ActaMovimiento) -> dict:
    return {
        "id": acta.id,
        "tipo": acta.tipo.value,
        "numero": acta.numero,
        "lineas": [
            {
                "activo_id": ObjectId(linea.activo_id),
                "resultado": linea.resultado.value,
                "observacion": linea.observacion,
            }
            for linea in acta.lineas
        ],
        "archivo_id": acta.archivo_id,
        "cerrada_por": _sello_a_doc(acta.cerrada_por),
        "aceptada_por": _sello_a_doc(acta.aceptada_por),
    }


def _doc_a_acta(doc: dict) -> ActaMovimiento:
    return ActaMovimiento(
        id=doc["id"],
        tipo=TipoActa(doc["tipo"]),
        numero=doc["numero"],
        lineas=[
            LineaActa(
                activo_id=str(linea["activo_id"]),
                resultado=ResultadoChequeo(linea["resultado"]),
                observacion=linea.get("observacion"),
            )
            for linea in doc["lineas"]
        ],
        archivo_id=doc.get("archivo_id"),
        cerrada_por=_doc_a_sello(doc["cerrada_por"]),
        aceptada_por=_doc_a_sello(doc.get("aceptada_por")),
    )


def _object_id(valor: str | None) -> ObjectId | None:
    return ObjectId(valor) if valor else None


def _str_o_none(valor) -> str | None:
    return str(valor) if valor else None


def _item_a_doc(item: ItemMovimiento) -> dict:
    return {
        "activo_id": ObjectId(item.activo_id),
        "responsable_original_id": _object_id(item.responsable_original_id),
        "estado": item.estado.value,
        "aprobado_por_responsable": _audit_a_doc(item.aprobado_por_responsable),
        "rechazado_por": _audit_a_doc(item.rechazado_por),
        "etapa_rechazo": item.etapa_rechazo.value if item.etapa_rechazo else None,
        "motivo_rechazo": item.motivo_rechazo,
        "devolucion_solicitada_por": _audit_a_doc(item.devolucion_solicitada_por),
        "recibido_por": _audit_a_doc(item.recibido_por),
        "fecha_devolucion_real": item.fecha_devolucion_real,
        "novedad_devolucion": item.novedad_devolucion,
        "chequeo_salida": _chequeo_a_doc(item.chequeo_salida),
        "chequeo_ingreso": _chequeo_a_doc(item.chequeo_ingreso),
    }


def _doc_a_item(doc: dict) -> ItemMovimiento:
    return ItemMovimiento(
        activo_id=str(doc["activo_id"]),
        responsable_original_id=_str_o_none(doc.get("responsable_original_id")),
        estado=EstadoItemMovimiento(doc["estado"]),
        aprobado_por_responsable=_doc_a_audit(doc.get("aprobado_por_responsable")),
        rechazado_por=_doc_a_audit(doc.get("rechazado_por")),
        etapa_rechazo=EtapaRechazo(doc["etapa_rechazo"]) if doc.get("etapa_rechazo") else None,
        motivo_rechazo=doc.get("motivo_rechazo"),
        devolucion_solicitada_por=_doc_a_audit(doc.get("devolucion_solicitada_por")),
        recibido_por=_doc_a_audit(doc.get("recibido_por")),
        fecha_devolucion_real=doc.get("fecha_devolucion_real"),
        novedad_devolucion=doc.get("novedad_devolucion"),
        chequeo_salida=_doc_a_chequeo(doc.get("chequeo_salida")),
        chequeo_ingreso=_doc_a_chequeo(doc.get("chequeo_ingreso")),
    )


def _entidad_a_doc(movimiento: Movimiento) -> dict:
    return {
        "tipo": movimiento.tipo.value,
        "sentido": movimiento.sentido.value if movimiento.sentido else None,
        "items": [_item_a_doc(item) for item in movimiento.items],
        "usuario_destino_id": _object_id(movimiento.usuario_destino_id),
        "descripcion": movimiento.descripcion,
        "evento_nombre": movimiento.evento_nombre,
        "fecha_salida_estimada": movimiento.fecha_salida_estimada,
        "fecha_retorno_estimada": movimiento.fecha_retorno_estimada,
        "fecha_entrega_real": movimiento.fecha_entrega_real,
        "fecha_devolucion_real": movimiento.fecha_devolucion_real,
        "estado": movimiento.estado.value,
        "aprobado_por_admin": _audit_a_doc(movimiento.aprobado_por_admin),
        "comprobante_archivo_id": movimiento.comprobante_archivo_id,
        "creado_por": _audit_a_doc(movimiento.creado_por),
        "actualizado_por": _audit_a_doc(movimiento.actualizado_por),
        "recordatorio_devolucion_enviado": movimiento.recordatorio_devolucion_enviado,
        "actas": [_acta_a_doc(acta) for acta in movimiento.actas],
    }


def _doc_a_entidad(doc: dict) -> Movimiento:
    return Movimiento(
        id=str(doc["_id"]),
        tipo=TipoMovimiento(doc["tipo"]),
        sentido=SentidoPrestamo(doc["sentido"]) if doc.get("sentido") else None,
        items=[_doc_a_item(item) for item in doc["items"]],
        usuario_destino_id=_str_o_none(doc.get("usuario_destino_id")),
        descripcion=doc["descripcion"],
        evento_nombre=doc.get("evento_nombre"),
        fecha_salida_estimada=doc.get("fecha_salida_estimada"),
        fecha_retorno_estimada=doc.get("fecha_retorno_estimada"),
        fecha_entrega_real=doc.get("fecha_entrega_real"),
        fecha_devolucion_real=doc.get("fecha_devolucion_real"),
        estado=EstadoMovimiento(doc["estado"]),
        aprobado_por_admin=_doc_a_audit(doc.get("aprobado_por_admin")),
        comprobante_archivo_id=doc.get("comprobante_archivo_id"),
        creado_por=_doc_a_audit(doc["creado_por"]),
        actualizado_por=_doc_a_audit(doc.get("actualizado_por")),
        recordatorio_devolucion_enviado=doc.get("recordatorio_devolucion_enviado", False),
        actas=[_doc_a_acta(acta) for acta in doc.get("actas", [])],
    )


def _condiciones_visibilidad(visible_para: VisibilidadMovimiento) -> list[dict]:
    """Lo que creo, donde es destinatario o responsable original de algun activo, o es de un activo a su cargo."""
    actor = ObjectId(visible_para.actor_id)
    condiciones = [
        {"creado_por.id_persona": visible_para.actor_id},
        {"usuario_destino_id": actor},
        {"items.responsable_original_id": actor},
    ]
    if visible_para.activo_ids:
        condiciones.append({"items.activo_id": {"$in": [ObjectId(a) for a in visible_para.activo_ids]}})

    return condiciones


def _condiciones_para_mi(para_mi: ParaMiMovimiento) -> list[dict]:
    """Donde es destinatario o responsable (original o actual) y, si es administrador, lo que espera su accion."""
    actor = ObjectId(para_mi.actor_id)
    condiciones = [{"usuario_destino_id": actor}, {"items.responsable_original_id": actor}]
    if para_mi.activo_ids:
        condiciones.append({"items.activo_id": {"$in": [ObjectId(a) for a in para_mi.activo_ids]}})
    if para_mi.es_administrador:
        condiciones.append({"items.estado": {"$in": _ESTADOS_ITEM_QUE_ESPERAN_ADMIN}})

    return condiciones


def _construir_filtro(
    tipo: TipoMovimiento | None,
    estado: EstadoMovimiento | None,
    activo_id: str | None,
    usuario_destino_id: str | None,
    creado_por_id: str | None,
    visible_para: VisibilidadMovimiento | None,
    para_mi: ParaMiMovimiento | None,
) -> dict:
    filtro: dict = {}
    if tipo:
        filtro["tipo"] = tipo.value
    if estado:
        filtro["estado"] = estado.value
    if activo_id:
        filtro["items.activo_id"] = ObjectId(activo_id)
    if usuario_destino_id:
        filtro["usuario_destino_id"] = ObjectId(usuario_destino_id)
    if creado_por_id:
        filtro["creado_por.id_persona"] = creado_por_id

    # Cada restriccion es un OR interno; entre ellas y con los demas filtros se combinan con AND.
    restricciones = []
    if visible_para is not None:
        restricciones.append({"$or": _condiciones_visibilidad(visible_para)})
    if para_mi is not None:
        restricciones.append({"$or": _condiciones_para_mi(para_mi)})
    if restricciones:
        filtro["$and"] = restricciones

    return filtro


async def crear_indices() -> None:
    coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]

    # Indice del modelo anterior (un activo por movimiento): ya no aplica.
    try:
        await coleccion.drop_index("idx_activo_id")
    except OperationFailure:
        pass

    await coleccion.create_index("items.activo_id", name="idx_items_activo_id")
    await coleccion.create_index("estado", name="idx_estado")
    await coleccion.create_index("tipo", name="idx_tipo")
    await coleccion.create_index("usuario_destino_id", name="idx_usuario_destino_id")
    await coleccion.create_index("creado_por.id_persona", name="idx_creado_por_id")


class MongoMovimientoRepository(MovimientoRepositoryPort):
    def __init__(self, collection_name: str = _NOMBRE_COLECCION):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, movimiento: Movimiento) -> Movimiento:
        documento = _entidad_a_doc(movimiento)

        if movimiento.id is None:
            resultado = await self._collection.insert_one(documento)
            id_documento = resultado.inserted_id
        else:
            id_documento = ObjectId(movimiento.id)
            await self._collection.replace_one({"_id": id_documento}, documento)

        guardado = await self._collection.find_one({"_id": id_documento})
        return _doc_a_entidad(guardado)

    async def obtener_por_id(self, id_movimiento: str) -> Movimiento | None:
        doc = await self._collection.find_one({"_id": ObjectId(id_movimiento)})
        return _doc_a_entidad(doc) if doc else None

    async def activos_ocupados(self, activo_ids: list[str]) -> set[str]:
        ids = [ObjectId(activo_id) for activo_id in activo_ids]
        documentos = await self._collection.find(
            {"items": {"$elemMatch": {"activo_id": {"$in": ids}, "estado": {"$in": _ESTADOS_ITEM_ACTIVOS}}}},
            {"items.activo_id": 1, "items.estado": 1},
        ).to_list(length=None)

        pedidos = set(activo_ids)

        return {
            str(item["activo_id"])
            for documento in documentos
            for item in documento["items"]
            if item["estado"] in _ESTADOS_ITEM_ACTIVOS and str(item["activo_id"]) in pedidos
        }

    async def listar_devoluciones_por_recordar(self, limite_fecha: datetime) -> list[Movimiento]:
        documentos = await self._collection.find(
            {
                "estado": EstadoMovimiento.EN_CURSO.value,
                "fecha_retorno_estimada": {"$ne": None, "$lte": limite_fecha},
                "recordatorio_devolucion_enviado": {"$ne": True},
            }
        ).to_list(length=None)

        return [_doc_a_entidad(documento) for documento in documentos]

    async def listar(
        self,
        tipo: TipoMovimiento | None,
        estado: EstadoMovimiento | None,
        activo_id: str | None,
        usuario_destino_id: str | None,
        creado_por_id: str | None,
        visible_para: VisibilidadMovimiento | None,
        para_mi: ParaMiMovimiento | None,
        skip: int,
        limit: int,
    ) -> list[Movimiento]:
        filtro = _construir_filtro(
            tipo, estado, activo_id, usuario_destino_id, creado_por_id, visible_para, para_mi
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
        tipo: TipoMovimiento | None,
        estado: EstadoMovimiento | None,
        activo_id: str | None,
        usuario_destino_id: str | None,
        creado_por_id: str | None,
        visible_para: VisibilidadMovimiento | None,
        para_mi: ParaMiMovimiento | None,
    ) -> int:
        filtro = _construir_filtro(
            tipo, estado, activo_id, usuario_destino_id, creado_por_id, visible_para, para_mi
        )
        return await self._collection.count_documents(filtro)
