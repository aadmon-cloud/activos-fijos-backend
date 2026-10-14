"""Solo un Super administrador asigna ese rol o gestiona a otro Super administrador (evita ascensos indebidos)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.usuarios.application.dto.actualizar_usuario_dto import ActualizarUsuarioDTO
from modules.usuarios.application.dto.desactivar_usuario_dto import DesactivarUsuarioDTO
from modules.usuarios.application.dto.reactivar_usuario_dto import ReactivarUsuarioDTO
from modules.usuarios.application.dto.registrar_usuario_dto import RegistrarUsuarioDTO
from modules.usuarios.application.dto.restablecer_password_dto import RestablecerPasswordDTO
from modules.usuarios.application.services.actualizar_usuario import ActualizarUsuarioService
from modules.usuarios.application.services.desactivar_usuario import DesactivarUsuarioService
from modules.usuarios.application.services.reactivar_usuario import ReactivarUsuarioService
from modules.usuarios.application.services.registrar_usuario import RegistrarUsuarioService
from modules.usuarios.application.services.restablecer_password import RestablecerPasswordService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.domain.errors import GestionSuperAdministradorNoPermitidaError
from shared.domain.entities.audit import AuditPersona
from shared.domain.errors import ErrorCategory

_ADMIN = "administrador_general"
_SUPER = "super_administrador"


def _usuario(rol: RolUsuario, activo: bool = True) -> Usuario:
    return Usuario(
        id="7",
        email="x@example.com",
        nombre="X",
        apellido="Y",
        password_hash="hash",
        rol=rol,
        area_id=None,
        telefono=None,
        identificacion=None,
        activo=activo,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


def _repo(usuario: Usuario | None):
    repo = AsyncMock()
    repo.obtener_por_id.return_value = usuario
    repo.obtener_por_email.return_value = None
    repo.obtener_por_identificacion.return_value = None
    repo.guardar.side_effect = lambda u: u
    return repo


# Registrar


async def test_un_administrador_general_no_puede_registrar_a_un_super_administrador():
    repo = _repo(None)
    servicio = RegistrarUsuarioService(repo, AsyncMock(), AsyncMock())

    with pytest.raises(GestionSuperAdministradorNoPermitidaError) as exc_info:
        await servicio.ejecutar(
            RegistrarUsuarioDTO(
                email="a@b.com", nombre="A", apellido="B", rol=RolUsuario.SUPER_ADMINISTRADOR,
                creado_por_id="1", creado_por_nombre="Admin", actor_rol=_ADMIN,
            )
        )

    assert exc_info.value.code == "USR-013"
    assert exc_info.value.category == ErrorCategory.FORBIDDEN
    repo.guardar.assert_not_called()


async def test_si_no_se_informa_el_actor_se_asume_sin_privilegios():
    servicio = RegistrarUsuarioService(_repo(None), AsyncMock(), AsyncMock())

    with pytest.raises(GestionSuperAdministradorNoPermitidaError):
        await servicio.ejecutar(
            RegistrarUsuarioDTO(
                email="a@b.com", nombre="A", apellido="B", rol=RolUsuario.SUPER_ADMINISTRADOR,
                creado_por_id="1", creado_por_nombre="Admin",
            )
        )


async def test_un_super_administrador_si_puede_registrar_a_otro_super_administrador():
    hasher = AsyncMock()
    hasher.hashear = lambda texto: "hash"
    repo = _repo(None)
    servicio = RegistrarUsuarioService(repo, hasher, AsyncMock())

    await servicio.ejecutar(
        RegistrarUsuarioDTO(
            email="a@b.com", nombre="A", apellido="B", rol=RolUsuario.SUPER_ADMINISTRADOR,
            creado_por_id="1", creado_por_nombre="Super", actor_rol=_SUPER,
        )
    )

    assert repo.guardar.call_args.args[0].rol == RolUsuario.SUPER_ADMINISTRADOR


async def test_un_administrador_general_sigue_registrando_los_demas_roles():
    hasher = AsyncMock()
    hasher.hashear = lambda texto: "hash"
    repo = _repo(None)

    await RegistrarUsuarioService(repo, hasher, AsyncMock()).ejecutar(
        RegistrarUsuarioDTO(
            email="a@b.com", nombre="A", apellido="B", rol=RolUsuario.EMPLEADO,
            creado_por_id="1", creado_por_nombre="Admin", actor_rol=_ADMIN,
        )
    )

    repo.guardar.assert_awaited_once()


# Actualizar


def _actualizar(**cambios):
    return ActualizarUsuarioDTO(id_usuario="7", actualizado_por_id="1", actualizado_por_nombre="Admin", **cambios)


async def test_un_administrador_general_no_puede_ascenderse_ni_ascender_a_otro():
    repo = _repo(_usuario(RolUsuario.EMPLEADO))
    servicio = ActualizarUsuarioService(repo, AsyncMock())

    with pytest.raises(GestionSuperAdministradorNoPermitidaError):
        await servicio.ejecutar(_actualizar(rol=RolUsuario.SUPER_ADMINISTRADOR, actor_rol=_ADMIN))

    repo.guardar.assert_not_called()


async def test_un_administrador_general_no_puede_editar_a_un_super_administrador():
    repo = _repo(_usuario(RolUsuario.SUPER_ADMINISTRADOR))
    servicio = ActualizarUsuarioService(repo, AsyncMock())

    with pytest.raises(GestionSuperAdministradorNoPermitidaError):
        await servicio.ejecutar(_actualizar(nombre="Otro", actor_rol=_ADMIN))

    with pytest.raises(GestionSuperAdministradorNoPermitidaError):
        await servicio.ejecutar(_actualizar(rol=RolUsuario.EMPLEADO, actor_rol=_ADMIN))

    repo.guardar.assert_not_called()


async def test_un_super_administrador_puede_ascender_y_degradar():
    repo = _repo(_usuario(RolUsuario.EMPLEADO))
    servicio = ActualizarUsuarioService(repo, AsyncMock())

    await servicio.ejecutar(_actualizar(rol=RolUsuario.SUPER_ADMINISTRADOR, actor_rol=_SUPER))

    assert repo.guardar.call_args.args[0].rol == RolUsuario.SUPER_ADMINISTRADOR


async def test_un_administrador_general_sigue_editando_a_usuarios_comunes():
    repo = _repo(_usuario(RolUsuario.EMPLEADO))

    await ActualizarUsuarioService(repo, AsyncMock()).ejecutar(
        _actualizar(rol=RolUsuario.JEFE_AREA, actor_rol=_ADMIN)
    )

    assert repo.guardar.call_args.args[0].rol == RolUsuario.JEFE_AREA


# Desactivar, reactivar y restablecer la contrasena


def _desactivar(actor_rol):
    return DesactivarUsuarioDTO(id_usuario="7", actualizado_por_id="1", actualizado_por_nombre="A", actor_rol=actor_rol)


def _reactivar(actor_rol):
    return ReactivarUsuarioDTO(id_usuario="7", actualizado_por_id="1", actualizado_por_nombre="A", actor_rol=actor_rol)


def _restablecer(actor_rol):
    return RestablecerPasswordDTO(
        id_usuario="7", password_nueva="password123", actualizado_por_id="1", actualizado_por_nombre="A",
        actor_rol=actor_rol,
    )


async def test_un_administrador_general_no_puede_desactivar_a_un_super_administrador():
    repo = _repo(_usuario(RolUsuario.SUPER_ADMINISTRADOR))

    with pytest.raises(GestionSuperAdministradorNoPermitidaError):
        await DesactivarUsuarioService(repo).ejecutar(_desactivar(_ADMIN))

    repo.guardar.assert_not_called()


async def test_un_administrador_general_no_puede_reactivar_a_un_super_administrador():
    repo = _repo(_usuario(RolUsuario.SUPER_ADMINISTRADOR, activo=False))

    with pytest.raises(GestionSuperAdministradorNoPermitidaError):
        await ReactivarUsuarioService(repo).ejecutar(_reactivar(_ADMIN))


async def test_un_administrador_general_no_puede_restablecer_la_contrasena_de_un_super_administrador():
    repo = _repo(_usuario(RolUsuario.SUPER_ADMINISTRADOR))
    hasher = AsyncMock()
    hasher.hashear = lambda texto: "hash"

    with pytest.raises(GestionSuperAdministradorNoPermitidaError):
        await RestablecerPasswordService(repo, hasher).ejecutar(_restablecer(_ADMIN))

    repo.guardar.assert_not_called()


async def test_un_super_administrador_puede_desactivar_y_reactivar_a_otro_super_administrador():
    repo = _repo(_usuario(RolUsuario.SUPER_ADMINISTRADOR))
    await DesactivarUsuarioService(repo).ejecutar(_desactivar(_SUPER))
    assert repo.guardar.call_args.args[0].activo is False

    repo = _repo(_usuario(RolUsuario.SUPER_ADMINISTRADOR, activo=False))
    await ReactivarUsuarioService(repo).ejecutar(_reactivar(_SUPER))
    assert repo.guardar.call_args.args[0].activo is True


async def test_un_administrador_general_sigue_desactivando_a_usuarios_comunes():
    repo = _repo(_usuario(RolUsuario.EMPLEADO))

    await DesactivarUsuarioService(repo).ejecutar(_desactivar(_ADMIN))

    assert repo.guardar.call_args.args[0].activo is False
