from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.catalogos.application.services.listar_condiciones import ListarCondicionesService
from modules.catalogos.domain.entities import Condicion
from shared.domain.entities.audit import AuditPersona


async def test_listar_condiciones_retorna_los_dtos_del_repositorio():
    repositorio_mock = AsyncMock()
    audit = AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC))
    repositorio_mock.listar.return_value = [
        Condicion(
            id="1", nombre="Bueno", color="#4CAF50", descripcion=None, creado_por=audit,
            actualizado_por=None,
        ),
    ]
    service = ListarCondicionesService(repositorio_mock)

    resultado = await service.ejecutar()

    assert len(resultado) == 1
    assert resultado[0].nombre == "Bueno"
