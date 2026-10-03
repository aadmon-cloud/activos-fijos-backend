from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.tareas.application.services.listar_tareas import ListarTareasService
from modules.tareas.domain.entities import Tarea


async def test_listar_tareas_mapea_entidades_a_dto():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar.return_value = [
        Tarea(id="1", titulo="A", completada=False, fecha_creacion=datetime(2026, 7, 23, tzinfo=UTC)),
        Tarea(id="2", titulo="B", completada=True, fecha_creacion=datetime(2026, 7, 22, tzinfo=UTC)),
    ]
    service = ListarTareasService(repositorio_mock)

    resultado = await service.ejecutar()

    assert [tarea_dto.id for tarea_dto in resultado] == ["1", "2"]
    assert resultado[1].completada is True
