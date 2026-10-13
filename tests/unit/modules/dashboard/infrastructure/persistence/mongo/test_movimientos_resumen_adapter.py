from unittest.mock import AsyncMock, MagicMock, patch

from modules.dashboard.infrastructure.persistence.mongo.movimientos_resumen_adapter import (
    MongoMovimientosResumenAdapter,
)

_RUTA = (
    "modules.dashboard.infrastructure.persistence.mongo.movimientos_resumen_adapter.mongo_manager"
)


async def test_obtener_suma_solicitado_y_aprobado_responsable_como_pendientes():
    coleccion = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(
        return_value=[
            {
                "total": [{"cantidad": 6}],
                "tipo": [{"_id": "prestamo", "cantidad": 6}],
                "estado": [
                    {"_id": "solicitado", "cantidad": 2},
                    {"_id": "aprobado_responsable", "cantidad": 1},
                    {"_id": "en_curso", "cantidad": 3},
                ],
            }
        ]
    )
    coleccion.aggregate = MagicMock(return_value=cursor)

    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = {"movimientos": coleccion}
        resumen = await MongoMovimientosResumenAdapter().obtener()

    assert resumen.total == 6
    assert resumen.pendientes_de_aprobacion == 3


async def test_obtener_no_cuenta_en_curso_como_pendiente_de_aprobacion():
    coleccion = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(
        return_value=[
            {
                "total": [{"cantidad": 1}],
                "tipo": [{"_id": "baja", "cantidad": 1}],
                "estado": [{"_id": "ejecutado", "cantidad": 1}],
            }
        ]
    )
    coleccion.aggregate = MagicMock(return_value=cursor)

    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = {"movimientos": coleccion}
        resumen = await MongoMovimientosResumenAdapter().obtener()

    assert resumen.pendientes_de_aprobacion == 0
