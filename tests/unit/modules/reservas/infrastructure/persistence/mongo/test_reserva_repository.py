from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from modules.reservas.domain.entities.reserva import ItemReserva, Reserva
from modules.reservas.infrastructure.persistence.mongo.reserva_repository import (
    MongoReservaRepository,
)
from shared.domain.entities.audit_persona import AuditPersona


class _UowFalso:
    session = "sesion-de-la-transaccion"


def _db_falsa():
    coleccion = MagicMock()
    coleccion.replace_one = AsyncMock()
    coleccion.delete_one = AsyncMock()
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coleccion)
    return db, coleccion


def _reserva():
    return Reserva.crear(
        session_id="session-1",
        items=[ItemReserva(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=5)],
        datos_adicionales=None,
        creado_por=AuditPersona(
            id_persona="507f1f77bcf86cd799439099", nombre="admin", fecha=datetime.now(UTC)
        ),
    ).model_copy(update={"id": "507f1f77bcf86cd799439011"})


async def test_actualizar_propaga_la_sesion_de_la_transaccion():
    db, coleccion = _db_falsa()
    repo = MongoReservaRepository(db)
    uow = _UowFalso()

    await repo.actualizar(_reserva(), uow=uow)

    assert coleccion.replace_one.call_args.kwargs["session"] == "sesion-de-la-transaccion"


async def test_actualizar_sin_uow_no_pasa_sesion():
    db, coleccion = _db_falsa()
    repo = MongoReservaRepository(db)

    await repo.actualizar(_reserva())

    assert coleccion.replace_one.call_args.kwargs["session"] is None


async def test_eliminar_propaga_la_sesion_de_la_transaccion():
    db, coleccion = _db_falsa()
    coleccion.delete_one.return_value = MagicMock(deleted_count=1)
    repo = MongoReservaRepository(db)
    uow = _UowFalso()

    await repo.eliminar("session-1", uow=uow)

    assert coleccion.delete_one.call_args.kwargs["session"] == "sesion-de-la-transaccion"


async def test_eliminar_sin_uow_no_pasa_sesion():
    db, coleccion = _db_falsa()
    coleccion.delete_one.return_value = MagicMock(deleted_count=1)
    repo = MongoReservaRepository(db)

    await repo.eliminar("session-1")

    assert coleccion.delete_one.call_args.kwargs["session"] is None
