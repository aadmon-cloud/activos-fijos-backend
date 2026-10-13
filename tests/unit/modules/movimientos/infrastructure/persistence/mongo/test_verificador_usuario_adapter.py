from unittest.mock import AsyncMock, patch

from bson import ObjectId

from modules.movimientos.infrastructure.persistence.mongo.verificador_usuario_adapter import (
    MongoVerificadorUsuario,
)

_RUTA = "modules.movimientos.infrastructure.persistence.mongo.verificador_usuario_adapter.mongo_manager"


@patch(_RUTA)
async def test_existe_retorna_false_si_no_encuentra_el_usuario(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = None
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    resultado = await MongoVerificadorUsuario().existe(str(ObjectId()))

    assert resultado is False


@patch(_RUTA)
async def test_existe_retorna_true_si_encuentra_el_usuario(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = {"_id": ObjectId()}
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    resultado = await MongoVerificadorUsuario().existe(str(ObjectId()))

    assert resultado is True
