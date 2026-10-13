from unittest.mock import AsyncMock, MagicMock, patch

from modules.dashboard.infrastructure.persistence.mongo.activos_resumen_adapter import (
    MongoActivosResumenAdapter,
)

_RUTA = "modules.dashboard.infrastructure.persistence.mongo.activos_resumen_adapter.mongo_manager"


async def test_obtener_arma_el_resumen_de_activos():
    coleccion = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(
        return_value=[
            {
                "total": [{"cantidad": 3}],
                "estado_ciclo_vida": [
                    {"_id": "disponible", "cantidad": 2},
                    {"_id": "prestado", "cantidad": 1},
                ],
                "tipo": [{"_id": "activo_fijo", "cantidad": 3}],
            }
        ]
    )
    coleccion.aggregate = MagicMock(return_value=cursor)

    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = {"activos": coleccion}
        resumen = await MongoActivosResumenAdapter().obtener()

    assert resumen.total == 3
    assert resumen.por_estado_ciclo_vida == {"disponible": 2, "prestado": 1}
    assert resumen.por_tipo == {"activo_fijo": 3}
