from unittest.mock import AsyncMock, MagicMock

from pymongo import ReturnDocument

from modules.movimientos.infrastructure.persistence.mongo.generador_secuencial import (
    MongoGeneradorSecuencial,
)


class _UowFalso:
    session = "sesion-de-la-transaccion"


def _db_falsa(doc_resultante: dict):
    coleccion = MagicMock()
    coleccion.find_one_and_update = AsyncMock(return_value=doc_resultante)
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coleccion)
    return db, coleccion


async def test_siguiente_usa_inc_atomico_con_upsert():
    db, coleccion = _db_falsa({"prefijo": "RM", "ultimo_numero": 24})
    generador = MongoGeneradorSecuencial(db)

    resultado = await generador.siguiente(nombre="remision", prefijo="RM")

    assert resultado == "RM-024"
    _, kwargs = coleccion.find_one_and_update.call_args
    args = coleccion.find_one_and_update.call_args.args
    assert args[0] == {"nombre": "remision"}
    assert args[1] == {"$inc": {"ultimo_numero": 1}, "$setOnInsert": {"prefijo": "RM"}}
    assert kwargs["upsert"] is True
    assert kwargs["return_document"] == ReturnDocument.AFTER


async def test_siguiente_propaga_la_sesion_de_la_transaccion():
    db, coleccion = _db_falsa({"prefijo": "RM", "ultimo_numero": 1})
    generador = MongoGeneradorSecuencial(db)
    uow = _UowFalso()

    await generador.siguiente(nombre="remision", prefijo="RM", uow=uow)

    assert coleccion.find_one_and_update.call_args.kwargs["session"] == "sesion-de-la-transaccion"


async def test_siguiente_respeta_el_ancho_configurado():
    db, _ = _db_falsa({"prefijo": "RM", "ultimo_numero": 7})
    generador = MongoGeneradorSecuencial(db)

    resultado = await generador.siguiente(nombre="remision", prefijo="RM", ancho=5)

    assert resultado == "RM-00007"
