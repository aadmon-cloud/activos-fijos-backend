from unittest.mock import AsyncMock, patch

from modules.usuarios.infrastructure.persistence.mongo.usuario_repository import crear_indices


@patch("modules.usuarios.infrastructure.persistence.mongo.usuario_repository.mongo_manager")
async def test_crear_indices_crea_los_cuatro_indices_esperados(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    await crear_indices()

    nombres_creados = {
        llamada.kwargs.get("name") for llamada in coleccion_mock.create_index.call_args_list
    }
    assert nombres_creados == {"uq_email", "uq_identificacion", "idx_area_id", "idx_rol"}

    llamada_email = next(
        c for c in coleccion_mock.create_index.call_args_list if c.kwargs.get("name") == "uq_email"
    )
    assert llamada_email.kwargs["unique"] is True

    llamada_identificacion = next(
        c
        for c in coleccion_mock.create_index.call_args_list
        if c.kwargs.get("name") == "uq_identificacion"
    )
    assert llamada_identificacion.kwargs["unique"] is True
    assert llamada_identificacion.kwargs["sparse"] is True
