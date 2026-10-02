from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from bson import ObjectId

from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    MovimientoPendiente,
)
from modules.aprobaciones_pendientes.infrastructure.persistence.mongo.movimiento_pendiente_repository import (
    MongoMovimientoPendienteRepository,
)
from shared.domain.entities.audit_persona import AuditPersona


class _UowFalso:
    session = "sesion-de-la-transaccion"


def _db_falsa(doc_encontrado=None):
    coleccion = MagicMock()
    coleccion.find_one = AsyncMock(return_value=doc_encontrado)
    coleccion.replace_one = AsyncMock()
    coleccion.delete_one = AsyncMock()
    coleccion.insert_one = AsyncMock()
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coleccion)
    return db, coleccion


def _pendiente():
    return MovimientoPendiente.proponer(
        tipo_propuesto="entrada",
        payload={"producto_codigo": "PROD-001", "cantidad": 10},
        creado_por=AuditPersona(
            id_persona="507f1f77bcf86cd799439099", nombre="Ana", fecha=datetime.now(UTC)
        ),
    ).model_copy(update={"id": "507f1f77bcf86cd799439011"})


async def test_obtener_por_id_devuelve_none_si_no_existe():
    db, _ = _db_falsa(doc_encontrado=None)
    repo = MongoMovimientoPendienteRepository(db)

    resultado = await repo.obtener_por_id("507f1f77bcf86cd799439011")

    assert resultado is None


async def test_obtener_por_id_mapea_el_documento():
    pendiente = _pendiente()
    doc = pendiente.model_dump(exclude={"id"})
    doc["_id"] = ObjectId(pendiente.id)
    doc["creado_por"]["id_persona"] = ObjectId(pendiente.creado_por.id_persona)
    db, coleccion = _db_falsa(doc_encontrado=doc)
    repo = MongoMovimientoPendienteRepository(db)

    resultado = await repo.obtener_por_id(pendiente.id)

    assert resultado.id == pendiente.id
    assert resultado.tipo_propuesto == "entrada"
    assert resultado.payload["producto_codigo"] == "PROD-001"
    coleccion.find_one.assert_called_once_with({"_id": ObjectId(pendiente.id)})


async def test_obtener_por_id_mapea_movimiento_id_y_confirmado_por_si_estan_presentes():
    confirmado_por = AuditPersona(
        id_persona="507f1f77bcf86cd799439098", nombre="Admin", fecha=datetime.now(UTC)
    )
    pendiente = _pendiente().confirmar(
        movimiento_id="507f1f77bcf86cd799439097", confirmado_por=confirmado_por
    )
    doc = pendiente.model_dump(exclude={"id"})
    doc["_id"] = ObjectId(pendiente.id)
    doc["creado_por"]["id_persona"] = ObjectId(pendiente.creado_por.id_persona)
    doc["confirmado_por"]["id_persona"] = ObjectId(confirmado_por.id_persona)
    doc["movimiento_id"] = ObjectId(pendiente.movimiento_id)
    db, _ = _db_falsa(doc_encontrado=doc)
    repo = MongoMovimientoPendienteRepository(db)

    resultado = await repo.obtener_por_id(pendiente.id)

    assert resultado.estado == "confirmada"
    assert resultado.movimiento_id == pendiente.movimiento_id
    assert resultado.confirmado_por.id_persona == confirmado_por.id_persona


async def test_actualizar_propaga_la_sesion_de_la_transaccion():
    db, coleccion = _db_falsa()
    repo = MongoMovimientoPendienteRepository(db)
    uow = _UowFalso()

    await repo.actualizar(_pendiente(), uow=uow)

    assert coleccion.replace_one.call_args.kwargs["session"] == "sesion-de-la-transaccion"


async def test_actualizar_sin_uow_no_pasa_sesion():
    db, coleccion = _db_falsa()
    repo = MongoMovimientoPendienteRepository(db)

    await repo.actualizar(_pendiente())

    assert coleccion.replace_one.call_args.kwargs["session"] is None


async def test_eliminar_propaga_la_sesion_de_la_transaccion():
    db, coleccion = _db_falsa()
    repo = MongoMovimientoPendienteRepository(db)
    uow = _UowFalso()

    await repo.eliminar("507f1f77bcf86cd799439011", uow=uow)

    coleccion.delete_one.assert_called_once_with(
        {"_id": ObjectId("507f1f77bcf86cd799439011")}, session="sesion-de-la-transaccion"
    )


async def test_crear_asigna_un_id_nuevo():
    db, coleccion = _db_falsa()
    repo = MongoMovimientoPendienteRepository(db)
    pendiente = MovimientoPendiente.proponer(
        tipo_propuesto="salida",
        payload={"producto_codigo": "PROD-001", "cantidad": 5, "ubicacion": "A10-1"},
        creado_por=AuditPersona(
            id_persona="507f1f77bcf86cd799439099", nombre="Ana", fecha=datetime.now(UTC)
        ),
    )

    creado = await repo.crear(pendiente)

    assert creado.id is not None
    coleccion.insert_one.assert_called_once()
