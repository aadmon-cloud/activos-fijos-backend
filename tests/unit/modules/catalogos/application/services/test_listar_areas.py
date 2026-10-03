from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.catalogos.application.services.listar_areas import ListarAreasService
from modules.catalogos.domain.entities import Area
from shared.domain.entities.audit import AuditPersona


async def test_listar_areas_retorna_los_dtos_del_repositorio():
    repositorio_mock = AsyncMock()
    audit = AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC))
    repositorio_mock.listar.return_value = [
        Area(id="1", nombre="Direccion", descripcion=None, creado_por=audit, actualizado_por=None),
        Area(id="2", nombre="Tecnologia", descripcion=None, creado_por=audit, actualizado_por=None),
    ]
    service = ListarAreasService(repositorio_mock)

    resultado = await service.ejecutar()

    assert len(resultado) == 2
    assert resultado[0].nombre == "Direccion"
