from unittest.mock import AsyncMock, MagicMock, patch

from modules.dashboard.infrastructure.persistence.mongo.solicitudes_resumen_adapter import (
    MongoSolicitudesResumenAdapter,
)

_RUTA = (
    "modules.dashboard.infrastructure.persistence.mongo.solicitudes_resumen_adapter.mongo_manager"
)


async def test_obtener_deriva_pendientes_del_grupo_por_estado():
    coleccion = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(
        return_value=[
            {
                "total": [{"cantidad": 5}],
                "estado": [
                    {"_id": "pendiente", "cantidad": 2},
                    {"_id": "resuelta", "cantidad": 3},
                ],
                "tipo": [{"_id": "mantenimiento", "cantidad": 5}],
            }
        ]
    )
    coleccion.aggregate = MagicMock(return_value=cursor)

    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = {"solicitudes": coleccion}
        resumen = await MongoSolicitudesResumenAdapter().obtener()

    assert resumen.total == 5
    assert resumen.pendientes == 2


async def test_obtener_pendientes_es_cero_sin_solicitudes_pendientes():
    coleccion = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(
        return_value=[
            {
                "total": [{"cantidad": 1}],
                "estado": [{"_id": "resuelta", "cantidad": 1}],
                "tipo": [{"_id": "ajuste", "cantidad": 1}],
            }
        ]
    )
    coleccion.aggregate = MagicMock(return_value=cursor)

    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = {"solicitudes": coleccion}
        resumen = await MongoSolicitudesResumenAdapter().obtener()

    assert resumen.pendientes == 0
