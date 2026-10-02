from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from bson import ObjectId

from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.movimientos.infrastructure.persistence.mongo.movimiento_repository import (
    MongoMovimientoRepository,
)
from shared.domain.entities.audit_persona import AuditPersona


class _UowFalso:
    session = "sesion-de-la-transaccion"


def _db_falsa(doc_encontrado=None):
    coleccion = MagicMock()
    coleccion.find_one = AsyncMock(return_value=doc_encontrado)
    coleccion.replace_one = AsyncMock()
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coleccion)
    return db, coleccion


def _movimiento():
    return Movimiento.registrar_salida(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        cantidad=5,
        motivo=None,
        cliente_destino=None,
        ubicacion="A10-1",
        notas=None,
        remision="RM-001",
        creado_por=AuditPersona(
            id_persona="507f1f77bcf86cd799439099", nombre="admin", fecha=datetime.now(UTC)
        ),
    ).model_copy(update={"id": "507f1f77bcf86cd799439011"})


async def test_obtener_por_id_devuelve_none_si_no_existe():
    db, _ = _db_falsa(doc_encontrado=None)
    repo = MongoMovimientoRepository(db)

    resultado = await repo.obtener_por_id("507f1f77bcf86cd799439011")

    assert resultado is None


async def test_obtener_por_id_con_id_invalido_devuelve_none_sin_consultar_mongo():
    db, coleccion = _db_falsa()
    repo = MongoMovimientoRepository(db)

    resultado = await repo.obtener_por_id("no-es-un-object-id")

    assert resultado is None
    coleccion.find_one.assert_not_called()


async def test_obtener_por_id_mapea_el_documento():
    movimiento = _movimiento()
    doc = movimiento.model_dump(exclude={"id"})
    doc["_id"] = ObjectId(movimiento.id)
    doc["creado_por"]["id_persona"] = ObjectId(movimiento.creado_por.id_persona)
    db, coleccion = _db_falsa(doc_encontrado=doc)
    repo = MongoMovimientoRepository(db)

    resultado = await repo.obtener_por_id(movimiento.id)

    assert resultado.id == movimiento.id
    assert resultado.remision == "RM-001"
    coleccion.find_one.assert_called_once_with({"_id": ObjectId(movimiento.id)})


async def test_actualizar_propaga_la_sesion_de_la_transaccion():
    db, coleccion = _db_falsa()
    repo = MongoMovimientoRepository(db)
    uow = _UowFalso()

    await repo.actualizar(_movimiento(), uow=uow)

    assert coleccion.replace_one.call_args.kwargs["session"] == "sesion-de-la-transaccion"


async def test_actualizar_sin_uow_no_pasa_sesion():
    db, coleccion = _db_falsa()
    repo = MongoMovimientoRepository(db)

    await repo.actualizar(_movimiento())

    assert coleccion.replace_one.call_args.kwargs["session"] is None
