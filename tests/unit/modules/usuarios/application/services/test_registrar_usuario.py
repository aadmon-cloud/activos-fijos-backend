from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.usuarios.application.dto.registrar_usuario_dto import RegistrarUsuarioDTO
from modules.usuarios.application.services.registrar_usuario import RegistrarUsuarioService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.domain.errors import (
    AreaInvalidaError,
    EmailYaRegistradoError,
    IdentificacionYaRegistradaError,
    PasswordDebilError,
)
from shared.domain.entities.audit import AuditPersona


def _usuario_existente(**overrides) -> Usuario:
    valores = dict(
        id="9",
        email="ana@example.com",
        nombre="X",
        apellido="Y",
        password_hash="h",
        rol=RolUsuario.EMPLEADO,
        area_id=None,
        telefono=None,
        identificacion=None,
        activo=True,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Usuario(**valores)


def _dto(**overrides) -> RegistrarUsuarioDTO:
    valores = dict(
        email="Ana@Example.com",
        nombre="  Ana  ",
        apellido="  Garcia  ",
        password="password123",
        rol=RolUsuario.EMPLEADO,
        creado_por_id="1",
        creado_por_nombre="Admin",
        area_id=None,
        telefono=None,
        identificacion=None,
    )
    valores.update(overrides)
    return RegistrarUsuarioDTO(**valores)


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_email.return_value = None
    mock.obtener_por_identificacion.return_value = None
    mock.guardar.side_effect = lambda usuario: Usuario(
        id="1",
        email=usuario.email,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        password_hash=usuario.password_hash,
        rol=usuario.rol,
        area_id=usuario.area_id,
        telefono=usuario.telefono,
        identificacion=usuario.identificacion,
        activo=usuario.activo,
        creado_por=usuario.creado_por,
        actualizado_por=usuario.actualizado_por,
    )
    return mock


@pytest.fixture
def hasher_mock():
    mock = MagicMock()
    mock.hashear.return_value = "hash-seguro"
    return mock


@pytest.fixture
def verificador_area_mock():
    mock = AsyncMock()
    mock.existe.return_value = True
    return mock


async def test_registrar_usuario_guarda_la_entidad_con_datos_normalizados(
    repositorio_mock, hasher_mock, verificador_area_mock
):
    service = RegistrarUsuarioService(repositorio_mock, hasher_mock, verificador_area_mock)

    resultado = await service.ejecutar(_dto())

    assert resultado.email == "ana@example.com"
    assert resultado.nombre == "Ana"
    assert resultado.apellido == "Garcia"
    hasher_mock.hashear.assert_called_once_with("password123")
    repositorio_mock.guardar.assert_called_once()
    usuario_guardado = repositorio_mock.guardar.call_args.args[0]
    assert usuario_guardado.password_hash == "hash-seguro"
    assert usuario_guardado.creado_por.id_persona == "1"


async def test_registrar_usuario_lanza_error_si_la_password_es_debil(
    repositorio_mock, hasher_mock, verificador_area_mock
):
    service = RegistrarUsuarioService(repositorio_mock, hasher_mock, verificador_area_mock)

    with pytest.raises(PasswordDebilError):
        await service.ejecutar(_dto(password="corta"))

    repositorio_mock.guardar.assert_not_called()


async def test_registrar_usuario_lanza_error_si_el_email_ya_existe(
    repositorio_mock, hasher_mock, verificador_area_mock
):
    repositorio_mock.obtener_por_email.return_value = _usuario_existente()
    service = RegistrarUsuarioService(repositorio_mock, hasher_mock, verificador_area_mock)

    with pytest.raises(EmailYaRegistradoError):
        await service.ejecutar(_dto())

    repositorio_mock.guardar.assert_not_called()


async def test_registrar_usuario_lanza_error_si_la_identificacion_ya_existe(
    repositorio_mock, hasher_mock, verificador_area_mock
):
    repositorio_mock.obtener_por_identificacion.return_value = _usuario_existente(
        email="otro@example.com", identificacion="123"
    )
    service = RegistrarUsuarioService(repositorio_mock, hasher_mock, verificador_area_mock)

    with pytest.raises(IdentificacionYaRegistradaError):
        await service.ejecutar(_dto(identificacion="123"))

    repositorio_mock.guardar.assert_not_called()


async def test_registrar_usuario_lanza_error_si_el_area_no_existe(
    repositorio_mock, hasher_mock, verificador_area_mock
):
    verificador_area_mock.existe.return_value = False
    service = RegistrarUsuarioService(repositorio_mock, hasher_mock, verificador_area_mock)

    with pytest.raises(AreaInvalidaError):
        await service.ejecutar(_dto(area_id="area-inexistente"))

    repositorio_mock.guardar.assert_not_called()
