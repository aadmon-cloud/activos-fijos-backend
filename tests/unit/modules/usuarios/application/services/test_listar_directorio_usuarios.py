from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.usuarios.application.services.listar_directorio_usuarios import (
    ListarDirectorioUsuariosService,
)
from modules.usuarios.domain.entities import RolUsuario, Usuario
from shared.domain.entities.audit import AuditPersona


def _usuario(id_: str, activo: bool = True) -> Usuario:
    return Usuario(
        id=id_,
        email=f"user{id_}@example.com",
        nombre="Ana",
        apellido=f"Garcia{id_}",
        password_hash="hash",
        rol=RolUsuario.EMPLEADO,
        area_id="area-1",
        telefono="3001234567",
        identificacion="123",
        activo=activo,
        creado_por=AuditPersona(id_persona="0", nombre="Sistema", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


async def test_el_directorio_solo_incluye_personas_activas():
    repositorio = AsyncMock()
    repositorio.listar.return_value = [_usuario("1"), _usuario("2", activo=False), _usuario("3")]

    resultado = await ListarDirectorioUsuariosService(repositorio).ejecutar()

    assert [u.id for u in resultado] == ["1", "3"]


async def test_el_directorio_no_expone_correo_rol_ni_contacto():
    repositorio = AsyncMock()
    repositorio.listar.return_value = [_usuario("1")]

    persona = (await ListarDirectorioUsuariosService(repositorio).ejecutar())[0]

    assert set(persona.__dict__) == {"id", "nombre", "apellido"}


async def test_pasa_la_busqueda_y_acota_el_limite():
    repositorio = AsyncMock()
    repositorio.listar.return_value = []

    await ListarDirectorioUsuariosService(repositorio).ejecutar(busqueda="ana", limit=99999)

    repositorio.listar.assert_awaited_once_with(busqueda="ana", skip=0, limit=1000)
