from unittest.mock import AsyncMock, patch

from bson import ObjectId

from modules.mantenimientos.infrastructure.persistence.mongo.verificador_tecnico_adapter import (
    MongoVerificadorTecnico,
)

_RUTA = (
    "modules.mantenimientos.infrastructure.persistence.mongo.verificador_tecnico_adapter."
    "mongo_manager"
)


@patch(_RUTA)
async def test_tiene_rol_mantenimiento_retorna_false_si_el_usuario_no_existe(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = None
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    resultado = await MongoVerificadorTecnico().tiene_rol_mantenimiento(str(ObjectId()))

    assert resultado is False


@patch(_RUTA)
async def test_tiene_rol_mantenimiento_retorna_false_si_el_rol_no_coincide(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = {"rol": "administrativo"}
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    resultado = await MongoVerificadorTecnico().tiene_rol_mantenimiento(str(ObjectId()))

    assert resultado is False


@patch(_RUTA)
async def test_tiene_rol_mantenimiento_retorna_true_si_el_rol_coincide(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = {"rol": "mantenimiento", "activo": True}
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    resultado = await MongoVerificadorTecnico().tiene_rol_mantenimiento(str(ObjectId()))

    assert resultado is True


@patch(_RUTA)
async def test_un_tecnico_desactivado_no_es_valido(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = {"rol": "mantenimiento", "activo": False}
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    resultado = await MongoVerificadorTecnico().tiene_rol_mantenimiento(str(ObjectId()))

    assert resultado is False


@patch(_RUTA)
async def test_un_usuario_sin_campo_activo_no_es_valido(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = {"rol": "mantenimiento"}
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    assert await MongoVerificadorTecnico().tiene_rol_mantenimiento(str(ObjectId())) is False
