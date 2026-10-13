from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from modules.dashboard.infrastructure.persistence.mongo.auditorias_resumen_adapter import (
    MongoAuditoriasResumenAdapter,
)

_RUTA = "modules.dashboard.infrastructure.persistence.mongo.auditorias_resumen_adapter.mongo_manager"


class _CursorFind:
    def __init__(self, documentos):
        self._documentos = documentos

    def __aiter__(self):
        return self._generador()

    async def _generador(self):
        for doc in self._documentos:
            yield doc


async def test_obtener_arma_el_resumen_con_las_ultimas_auditorias_y_sus_nombres():
    auditoria_id = ObjectId()
    usuario_id = ObjectId()
    fecha_cierre = datetime(2026, 1, 1, tzinfo=UTC)

    coleccion_auditorias = MagicMock()
    cursor_facet = MagicMock()
    cursor_facet.to_list = AsyncMock(
        return_value=[
            {
                "total": [{"cantidad": 1}],
                "estado": [{"_id": "notificada", "cantidad": 1}],
            }
        ]
    )
    cursor_ultimas = MagicMock()
    cursor_ultimas.to_list = AsyncMock(
        return_value=[
            {
                "_id": auditoria_id,
                "usuario_auditado_id": usuario_id,
                "fecha_cierre": fecha_cierre,
                "no_encontrados": 2,
            }
        ]
    )
    coleccion_auditorias.aggregate = MagicMock(side_effect=[cursor_facet, cursor_ultimas])

    coleccion_usuarios = MagicMock()
    coleccion_usuarios.find = MagicMock(
        return_value=_CursorFind([{"_id": usuario_id, "nombre": "Camilo", "apellido": "Perez"}])
    )

    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = {
            "auditorias": coleccion_auditorias,
            "usuarios": coleccion_usuarios,
        }
        resumen = await MongoAuditoriasResumenAdapter().obtener(limite_recientes=5)

    assert resumen.total == 1
    assert resumen.por_estado == {"notificada": 1}
    assert len(resumen.ultimas) == 1
    reciente = resumen.ultimas[0]
    assert reciente.id == str(auditoria_id)
    assert reciente.usuario_auditado_nombre == "Camilo Perez"
    assert reciente.no_encontrados == 2
    assert reciente.fecha_cierre == fecha_cierre


async def test_obtener_sin_auditorias_no_consulta_usuarios():
    coleccion_auditorias = MagicMock()
    cursor_facet = MagicMock()
    cursor_facet.to_list = AsyncMock(return_value=[])
    cursor_ultimas = MagicMock()
    cursor_ultimas.to_list = AsyncMock(return_value=[])
    coleccion_auditorias.aggregate = MagicMock(side_effect=[cursor_facet, cursor_ultimas])

    coleccion_usuarios = MagicMock()
    coleccion_usuarios.find = MagicMock(side_effect=AssertionError("no deberia consultarse"))

    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = {
            "auditorias": coleccion_auditorias,
            "usuarios": coleccion_usuarios,
        }
        resumen = await MongoAuditoriasResumenAdapter().obtener(limite_recientes=5)

    assert resumen.total == 0
    assert resumen.ultimas == []
