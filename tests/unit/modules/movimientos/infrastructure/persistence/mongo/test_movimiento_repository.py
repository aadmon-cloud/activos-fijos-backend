from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId
from pymongo.errors import OperationFailure

from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    EtapaRechazo,
    SentidoPrestamo,
    TipoMovimiento,
)
from modules.movimientos.infrastructure.persistence.mongo.movimiento_repository import (
    MongoMovimientoRepository,
    _doc_a_entidad,
    _entidad_a_doc,
    crear_indices,
)

_MODULO = "modules.movimientos.infrastructure.persistence.mongo.movimiento_repository"


def _movimiento_completo(fabrica):
    audit = fabrica.audit("r1", "Responsable")
    activo_a, activo_b = str(ObjectId()), str(ObjectId())
    items = [
        fabrica.item(
            activo_id=activo_a,
            responsable_original_id=str(ObjectId()),
            estado=EstadoItemMovimiento.DEVUELTO,
            aprobado_por_responsable=audit,
            devolucion_solicitada_por=audit,
            recibido_por=audit,
            fecha_devolucion_real=datetime(2026, 1, 5, tzinfo=UTC),
            novedad_devolucion="Rayado",
        ),
        fabrica.item(
            activo_id=activo_b,
            responsable_original_id=str(ObjectId()),
            estado=EstadoItemMovimiento.RECHAZADO,
            rechazado_por=audit,
            etapa_rechazo=EtapaRechazo.ADMINISTRACION,
            motivo_rechazo="No hay",
        ),
    ]

    return fabrica.movimiento(
        id=None,
        sentido=SentidoPrestamo.PRESTAR,
        items=items,
        usuario_destino_id=str(ObjectId()),
        estado=EstadoMovimiento.DEVUELTO,
        aprobado_por_admin=audit,
        recordatorio_devolucion_enviado=True,
    )


def test_entidad_a_doc_convierte_las_referencias_a_object_id(fabrica):
    movimiento = _movimiento_completo(fabrica)

    doc = _entidad_a_doc(movimiento)

    assert "id" not in doc
    assert doc["tipo"] == "prestamo"
    assert doc["sentido"] == "prestar"
    assert doc["estado"] == "devuelto"
    assert doc["usuario_destino_id"] == ObjectId(movimiento.usuario_destino_id)
    assert doc["items"][0]["activo_id"] == ObjectId(movimiento.items[0].activo_id)
    assert doc["items"][0]["responsable_original_id"] == ObjectId(movimiento.items[0].responsable_original_id)
    assert doc["items"][1]["etapa_rechazo"] == "administracion"
    assert doc["items"][1]["estado"] == "rechazado"


def test_un_movimiento_se_guarda_y_se_lee_sin_perder_nada(fabrica):
    movimiento = _movimiento_completo(fabrica)

    leido = _doc_a_entidad({**_entidad_a_doc(movimiento), "_id": ObjectId()})

    assert leido.items == movimiento.items
    assert leido.sentido == SentidoPrestamo.PRESTAR
    assert leido.usuario_destino_id == movimiento.usuario_destino_id
    assert leido.aprobado_por_admin == movimiento.aprobado_por_admin
    assert leido.recordatorio_devolucion_enviado is True


def test_una_baja_se_guarda_sin_destinatario_ni_sentido(fabrica):
    movimiento = fabrica.movimiento(
        tipo=TipoMovimiento.BAJA, usuario_destino_id=None, items=[fabrica.item(activo_id=str(ObjectId()), responsable_original_id=None)]
    )

    doc = _entidad_a_doc(movimiento)
    leido = _doc_a_entidad({**doc, "_id": ObjectId()})

    assert doc["usuario_destino_id"] is None
    assert doc["sentido"] is None
    assert leido.usuario_destino_id is None and leido.sentido is None
    assert leido.items[0].responsable_original_id is None


def test_la_marca_del_recordatorio_vale_false_si_el_documento_no_la_trae(fabrica):
    doc = _entidad_a_doc(_movimiento_completo(fabrica))
    del doc["recordatorio_devolucion_enviado"]

    assert _doc_a_entidad({**doc, "_id": ObjectId()}).recordatorio_devolucion_enviado is False


@patch(f"{_MODULO}.mongo_manager")
async def test_crear_indices_crea_los_indices_esperados_y_quita_el_del_modelo_anterior(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"movimientos": coleccion_mock}

    await crear_indices()

    coleccion_mock.drop_index.assert_awaited_once_with("idx_activo_id")
    nombres = {c.kwargs.get("name") for c in coleccion_mock.create_index.call_args_list}
    assert nombres == {
        "idx_items_activo_id",
        "idx_estado",
        "idx_tipo",
        "idx_usuario_destino_id",
        "idx_creado_por_id",
    }


@patch(f"{_MODULO}.mongo_manager")
async def test_crear_indices_tolera_que_el_indice_anterior_ya_no_exista(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.drop_index.side_effect = OperationFailure("index not found")
    mongo_manager_mock.get_database.return_value = {"movimientos": coleccion_mock}

    await crear_indices()

    assert coleccion_mock.create_index.await_count == 5


@patch(f"{_MODULO}.mongo_manager")
async def test_activos_ocupados_devuelve_los_pedidos_cuyo_item_sigue_vivo(mongo_manager_mock):
    libre, ocupado, otro = ObjectId(), ObjectId(), ObjectId()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(
        return_value=[
            {
                "items": [
                    {"activo_id": ocupado, "estado": "en_curso"},
                    {"activo_id": libre, "estado": "devuelto"},  # ya volvio: no ocupa
                    {"activo_id": otro, "estado": "pendiente_admin"},  # vivo, pero no se pregunto por el
                ]
            }
        ]
    )
    coleccion = MagicMock()
    coleccion.find = MagicMock(return_value=cursor)
    mongo_manager_mock.get_database.return_value = {"movimientos": coleccion}

    ocupados = await MongoMovimientoRepository().activos_ocupados([str(libre), str(ocupado)])

    assert ocupados == {str(ocupado)}
    filtro = coleccion.find.call_args.args[0]
    assert set(filtro["items"]["$elemMatch"]["estado"]["$in"]) == {
        "pendiente_responsable",
        "pendiente_admin",
        "en_curso",
        "devolucion_solicitada",
    }
    assert set(filtro["items"]["$elemMatch"]["activo_id"]["$in"]) == {libre, ocupado}


@patch(f"{_MODULO}.mongo_manager")
async def test_listar_devoluciones_por_recordar_filtra_en_curso_con_fecha_y_sin_recordatorio(mongo_manager_mock):
    limite = datetime(2026, 11, 11, tzinfo=UTC)
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[])
    coleccion = MagicMock()
    coleccion.find = MagicMock(return_value=cursor)
    mongo_manager_mock.get_database.return_value = {"movimientos": coleccion}

    assert await MongoMovimientoRepository().listar_devoluciones_por_recordar(limite) == []

    coleccion.find.assert_called_once_with(
        {
            "estado": "en_curso",
            "fecha_retorno_estimada": {"$ne": None, "$lte": limite},
            "recordatorio_devolucion_enviado": {"$ne": True},
        }
    )
