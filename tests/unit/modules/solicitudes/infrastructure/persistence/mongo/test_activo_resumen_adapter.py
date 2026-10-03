from unittest.mock import AsyncMock, patch

from bson import ObjectId

from modules.solicitudes.infrastructure.persistence.mongo.activo_resumen_adapter import (
    MongoActivoResumenAdapter,
)


@patch("modules.solicitudes.infrastructure.persistence.mongo.activo_resumen_adapter.mongo_manager")
async def test_obtener_resumen_retorna_none_si_no_existe(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = None
    mongo_manager_mock.get_database.return_value = {"activos": coleccion_mock}
    adapter = MongoActivoResumenAdapter()

    resultado = await adapter.obtener_resumen(str(ObjectId()))

    assert resultado is None


@patch("modules.solicitudes.infrastructure.persistence.mongo.activo_resumen_adapter.mongo_manager")
async def test_obtener_resumen_retorna_el_resumen_si_existe(mongo_manager_mock):
    activo_id = ObjectId()
    responsable_id = ObjectId()
    area_id = ObjectId()
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = {
        "_id": activo_id,
        "responsable_id": responsable_id,
        "area_id": area_id,
    }
    mongo_manager_mock.get_database.return_value = {"activos": coleccion_mock}
    adapter = MongoActivoResumenAdapter()

    resultado = await adapter.obtener_resumen(str(activo_id))

    assert resultado.id == str(activo_id)
    assert resultado.responsable_id == str(responsable_id)
    assert resultado.area_id == str(area_id)
