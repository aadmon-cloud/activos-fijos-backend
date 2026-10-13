from unittest.mock import AsyncMock, patch

from pymongo.errors import OperationFailure

from modules.usuarios.infrastructure.persistence.mongo.usuario_repository import crear_indices

_MODULO = "modules.usuarios.infrastructure.persistence.mongo.usuario_repository"


def _llamada(coleccion_mock, nombre):
    return next(
        c for c in coleccion_mock.create_index.call_args_list if c.kwargs.get("name") == nombre
    )


@patch(f"{_MODULO}.mongo_manager")
async def test_crear_indices_crea_los_cuatro_indices_esperados(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    await crear_indices()

    nombres_creados = {
        llamada.kwargs.get("name") for llamada in coleccion_mock.create_index.call_args_list
    }
    assert nombres_creados == {"uq_email", "uq_identificacion_texto", "idx_area_id", "idx_rol"}
    assert _llamada(coleccion_mock, "uq_email").kwargs["unique"] is True


@patch(f"{_MODULO}.mongo_manager")
async def test_la_identificacion_es_unica_solo_cuando_tiene_texto(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    await crear_indices()

    llamada = _llamada(coleccion_mock, "uq_identificacion_texto")
    assert llamada.kwargs["unique"] is True
    # Varios usuarios sin identificacion (null) no deben chocar entre si.
    assert llamada.kwargs["partialFilterExpression"] == {"identificacion": {"$type": "string"}}


@patch(f"{_MODULO}.mongo_manager")
async def test_retira_el_indice_sparse_anterior(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    await crear_indices()

    coleccion_mock.drop_index.assert_awaited_once_with("uq_identificacion")


@patch(f"{_MODULO}.mongo_manager")
async def test_si_el_indice_anterior_no_existe_sigue_creando_los_demas(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.drop_index.side_effect = OperationFailure("index not found")
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    await crear_indices()

    assert coleccion_mock.create_index.await_count == 4
