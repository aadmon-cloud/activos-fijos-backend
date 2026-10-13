from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from modules.mantenimientos.infrastructure.persistence.mongo.buscador_activos_adapter import (
    MongoBuscadorActivos,
)
from modules.mantenimientos.infrastructure.persistence.mongo.solicitud_verificador_adapter import (
    MongoSolicitudVerificador,
)

_RUTA_BUSCADOR = (
    "modules.mantenimientos.infrastructure.persistence.mongo.buscador_activos_adapter.mongo_manager"
)
_RUTA_SOLICITUD = (
    "modules.mantenimientos.infrastructure.persistence.mongo.solicitud_verificador_adapter.mongo_manager"
)


@patch(_RUTA_BUSCADOR)
async def test_buscar_por_codigo_devuelve_el_id_de_cada_codigo_existente(mongo_manager_mock):
    activo_a, activo_b = ObjectId(), ObjectId()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(
        return_value=[
            {"_id": activo_a, "numero_inventario": "BAÑO1"},
            {"_id": activo_b, "numero_inventario": "lavamanos1"},
        ]
    )
    coleccion = MagicMock()
    coleccion.find = MagicMock(return_value=cursor)
    mongo_manager_mock.get_database.return_value = {"activos": coleccion}

    resultado = await MongoBuscadorActivos().buscar_por_codigo(["BAÑO1", "lavamanos1", "otro"])

    assert resultado == {"BAÑO1": str(activo_a), "lavamanos1": str(activo_b)}
    filtro, proyeccion = coleccion.find.call_args.args
    assert filtro == {"numero_inventario": {"$in": ["BAÑO1", "lavamanos1", "otro"]}}
    assert proyeccion == {"numero_inventario": 1}


@patch(_RUTA_BUSCADOR)
async def test_buscar_por_codigo_sin_codigos_no_consulta(mongo_manager_mock):
    resultado = await MongoBuscadorActivos().buscar_por_codigo([])

    assert resultado == {}
    mongo_manager_mock.get_database.assert_not_called()


@patch(_RUTA_SOLICITUD)
async def test_corresponde_al_activo_consulta_la_solicitud_por_activo(mongo_manager_mock):
    solicitud_id, activo_id = ObjectId(), ObjectId()
    coleccion = AsyncMock()
    coleccion.find_one.return_value = {"_id": solicitud_id}
    mongo_manager_mock.get_database.return_value = {"solicitudes": coleccion}

    resultado = await MongoSolicitudVerificador().corresponde_al_activo(str(solicitud_id), str(activo_id))

    assert resultado is True
    filtro, _ = coleccion.find_one.call_args.args
    assert filtro == {"_id": solicitud_id, "activo_id": activo_id}


@patch(_RUTA_SOLICITUD)
async def test_no_corresponde_si_la_solicitud_no_existe_o_es_de_otro_activo(mongo_manager_mock):
    coleccion = AsyncMock()
    coleccion.find_one.return_value = None
    mongo_manager_mock.get_database.return_value = {"solicitudes": coleccion}

    assert await MongoSolicitudVerificador().corresponde_al_activo(str(ObjectId()), str(ObjectId())) is False
