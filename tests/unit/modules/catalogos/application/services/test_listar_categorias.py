from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.catalogos.application.services.listar_categorias import ListarCategoriasService
from modules.catalogos.domain.entities import Categoria
from shared.domain.entities.audit import AuditPersona


async def test_listar_categorias_retorna_los_dtos_del_repositorio():
    repositorio_mock = AsyncMock()
    audit = AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC))
    repositorio_mock.listar.return_value = [
        Categoria(id="1", nombre="Muebles", descripcion=None, creado_por=audit, actualizado_por=None),
    ]
    service = ListarCategoriasService(repositorio_mock)

    resultado = await service.ejecutar()

    assert len(resultado) == 1
    assert resultado[0].nombre == "Muebles"
