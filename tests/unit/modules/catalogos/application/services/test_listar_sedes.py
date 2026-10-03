from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.catalogos.application.services.listar_sedes import ListarSedesService
from modules.catalogos.domain.entities import Sede
from shared.domain.entities.audit import AuditPersona


async def test_listar_sedes_retorna_los_dtos_del_repositorio():
    repositorio_mock = AsyncMock()
    audit = AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC))
    repositorio_mock.listar.return_value = [
        Sede(id="1", nombre="Prado", descripcion=None, creado_por=audit, actualizado_por=None),
        Sede(id="2", nombre="Bosa", descripcion=None, creado_por=audit, actualizado_por=None),
    ]
    service = ListarSedesService(repositorio_mock)

    resultado = await service.ejecutar()

    assert len(resultado) == 2
