from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.usuarios.application.dto.restablecer_password_dto import RestablecerPasswordDTO
from modules.usuarios.application.services.restablecer_password import RestablecerPasswordService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.domain.errors import PasswordDebilError, UsuarioNoEncontradoError
from shared.domain.entities.audit import AuditPersona


def _usuario() -> Usuario:
    return Usuario(
        id="1",
        email="ana@example.com",
        nombre="Ana",
        apellido="Garcia",
        password_hash="hash-viejo",
        rol=RolUsuario.EMPLEADO,
        area_id=None,
        telefono=None,
        identificacion=None,
        activo=True,
        creado_por=AuditPersona(id_persona="0", nombre="Sistema", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


def _dto(password_nueva: str = "nueva-clave-123") -> RestablecerPasswordDTO:
    return RestablecerPasswordDTO(
        id_usuario="1",
        password_nueva=password_nueva,
        actualizado_por_id="9",
        actualizado_por_nombre="Admin",
    )


async def test_restablecer_password_guarda_el_hash_nuevo_y_audita():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _usuario()
    hasher_mock = MagicMock()
    hasher_mock.hashear.return_value = "hash-nuevo"
    service = RestablecerPasswordService(repositorio_mock, hasher_mock)

    await service.ejecutar(_dto())

    guardado = repositorio_mock.guardar.call_args.args[0]
    assert guardado.password_hash == "hash-nuevo"
    assert guardado.actualizado_por.id_persona == "9"
    hasher_mock.hashear.assert_called_once_with("nueva-clave-123")


async def test_restablecer_password_rechaza_una_clave_debil_sin_consultar_nada():
    repositorio_mock = AsyncMock()
    service = RestablecerPasswordService(repositorio_mock, MagicMock())

    with pytest.raises(PasswordDebilError):
        await service.ejecutar(_dto("corta"))

    repositorio_mock.obtener_por_id.assert_not_called()


async def test_restablecer_password_lanza_error_si_el_usuario_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    service = RestablecerPasswordService(repositorio_mock, MagicMock())

    with pytest.raises(UsuarioNoEncontradoError):
        await service.ejecutar(_dto())

    repositorio_mock.guardar.assert_not_called()
