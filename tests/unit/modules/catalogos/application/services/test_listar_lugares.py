from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.catalogos.application.dto.listar_lugares_dto import ListarLugaresDTO
from modules.catalogos.application.services.listar_lugares import ListarLugaresService
from modules.catalogos.domain.entities import Lugar, TipoLugar
from shared.domain.entities.audit import AuditPersona

_AUDIT = AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC))


async def test_listar_lugares_filtra_por_sede():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar.return_value = [
        Lugar(id="1", nombre="Bodega", tipo=TipoLugar.BODEGA, sede_id="1", creado_por=_AUDIT,
              actualizado_por=None),
    ]
    service = ListarLugaresService(repositorio_mock)

    resultado = await service.ejecutar(ListarLugaresDTO(sede_id="1"))

    assert len(resultado) == 1
    repositorio_mock.listar.assert_called_once_with(sede_id="1")
