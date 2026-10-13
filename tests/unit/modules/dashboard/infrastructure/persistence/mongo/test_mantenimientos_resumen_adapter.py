from unittest.mock import AsyncMock, MagicMock, patch

from modules.dashboard.infrastructure.persistence.mongo.mantenimientos_resumen_adapter import (
    MongoMantenimientosResumenAdapter,
)

_RUTA = (
    "modules.dashboard.infrastructure.persistence.mongo.mantenimientos_resumen_adapter."
    "mongo_manager"
)


async def test_obtener_incluye_el_conteo_de_pendientes_de_alerta():
    coleccion = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(
        return_value=[{"total": [{"cantidad": 4}], "estado": [{"_id": "programado", "cantidad": 4}]}]
    )
    coleccion.aggregate = MagicMock(return_value=cursor)
    coleccion.count_documents = AsyncMock(return_value=2)

    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = {"mantenimientos": coleccion}
        resumen = await MongoMantenimientosResumenAdapter().obtener()

    assert resumen.total == 4
    assert resumen.por_estado == {"programado": 4}
    assert resumen.pendientes_de_alerta == 2

    filtro = coleccion.count_documents.call_args.args[0]
    assert filtro["estado"] == "completado"
    assert filtro["alerta_enviada"] is False
    assert "$lte" in filtro["proxima_fecha_sugerida"]
