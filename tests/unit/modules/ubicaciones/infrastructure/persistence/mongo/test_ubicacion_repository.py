from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from modules.ubicaciones.infrastructure.persistence.mongo.ubicacion_repository import (
    MongoUbicacionRepository,
)
from shared.domain.entities.audit_persona import AuditPersona


class _UowFalso:
    session = "sesion-de-la-transaccion"


def _db_falsa():
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[])
    coleccion = MagicMock()
    coleccion.insert_one = AsyncMock()
    coleccion.replace_one = AsyncMock()
    coleccion.delete_one = AsyncMock()
    coleccion.find = MagicMock(return_value=cursor)
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coleccion)
    return db, coleccion


def _ubicacion():
    return Ubicacion.crear(
        "PROD-001",
        "A10-1",
        50,
        AuditPersona(id_persona="507f1f77bcf86cd799439099", nombre="admin", fecha=datetime.now(UTC)),
    )


async def test_crear_propaga_la_sesion_de_la_transaccion():
    db, coleccion = _db_falsa()
    repo = MongoUbicacionRepository(db)
    uow = _UowFalso()

    await repo.crear(_ubicacion(), uow=uow)

    assert coleccion.insert_one.call_args.kwargs["session"] == "sesion-de-la-transaccion"


async def test_crear_sin_uow_no_pasa_sesion():
    db, coleccion = _db_falsa()
    repo = MongoUbicacionRepository(db)

    await repo.crear(_ubicacion())

    assert coleccion.insert_one.call_args.kwargs["session"] is None


async def test_listar_por_producto_propaga_la_sesion():
    db, coleccion = _db_falsa()
    repo = MongoUbicacionRepository(db)
    uow = _UowFalso()

    await repo.listar_por_producto("PROD-001", uow=uow)

    assert coleccion.find.call_args.kwargs["session"] == "sesion-de-la-transaccion"
