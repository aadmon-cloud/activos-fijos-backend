from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.usuarios.application.dto.listar_usuarios_dto import ListarUsuariosDTO
from modules.usuarios.application.services.listar_usuarios import ListarUsuariosService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from shared.domain.entities.audit import AuditPersona


def _usuario(id_: str) -> Usuario:
    return Usuario(
        id=id_,
        email=f"user{id_}@example.com",
        nombre="Ana",
        apellido="Garcia",
        password_hash="hash",
        rol=RolUsuario.EMPLEADO,
        area_id=None,
        telefono=None,
        identificacion=None,
        activo=True,
        creado_por=AuditPersona(id_persona="0", nombre="Sistema", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


async def test_listar_usuarios_retorna_los_dtos_del_repositorio():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar.return_value = [_usuario("1"), _usuario("2")]
    service = ListarUsuariosService(repositorio_mock)

    resultado = await service.ejecutar(ListarUsuariosDTO(busqueda=None, skip=0, limit=100))

    assert len(resultado) == 2
    repositorio_mock.listar.assert_called_once_with(busqueda=None, skip=0, limit=100)


async def test_listar_usuarios_limita_el_limit_maximo():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar.return_value = []
    service = ListarUsuariosService(repositorio_mock)

    await service.ejecutar(ListarUsuariosDTO(busqueda=None, skip=0, limit=5000))

    repositorio_mock.listar.assert_called_once_with(busqueda=None, skip=0, limit=1000)
