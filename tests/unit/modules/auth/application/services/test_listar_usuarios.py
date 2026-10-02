from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.auth.application.dto.listar_usuarios import ListarUsuariosInput
from modules.auth.application.services.listar_usuarios import ListarUsuariosService
from modules.auth.domain.entities.usuario import Usuario
from shared.domain.entities.audit_persona import AuditPersona


def _usuario(n):
    return Usuario(
        id=f"id-{n}",
        email=f"user{n}@example.com",
        username=f"user{n}",
        creado_por=AuditPersona(id_persona=f"id-{n}", nombre=f"user{n}", fecha=datetime.now(UTC)),
    )


async def test_ejecutar_retorna_respuesta_paginada():
    usuario_repository_mock = AsyncMock()
    usuario_repository_mock.listar_paginado.return_value = ([_usuario(1), _usuario(2)], 2)
    service = ListarUsuariosService(usuario_repository_mock)

    resultado = await service.ejecutar(ListarUsuariosInput(pagina=1, limite=10))

    assert resultado.total_elementos == 2
    assert len(resultado.resultado) == 2
    usuario_repository_mock.listar_paginado.assert_called_once_with(pagina=1, limite=10)
