from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.usuarios.application.dto.cambiar_password_dto import CambiarPasswordDTO
from modules.usuarios.application.services.cambiar_password import CambiarPasswordService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.domain.errors import (
    PasswordActualIncorrectaError,
    PasswordDebilError,
    PasswordNuevaIgualALaActualError,
    UsuarioNoEncontradoError,
)
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


def _dto(actual: str = "clave-actual-1", nueva: str = "clave-nueva-2") -> CambiarPasswordDTO:
    return CambiarPasswordDTO(id_usuario="1", password_actual=actual, password_nueva=nueva)


def _servicio(verifica: bool = True):
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _usuario()
    hasher_mock = MagicMock()
    hasher_mock.verificar.return_value = verifica
    hasher_mock.hashear.return_value = "hash-nuevo"

    return CambiarPasswordService(repositorio_mock, hasher_mock), repositorio_mock, hasher_mock


async def test_cambiar_password_verifica_la_actual_y_guarda_el_hash_nuevo():
    service, repositorio_mock, hasher_mock = _servicio()

    await service.ejecutar(_dto())

    hasher_mock.verificar.assert_called_once_with("clave-actual-1", "hash-viejo")
    guardado = repositorio_mock.guardar.call_args.args[0]
    assert guardado.password_hash == "hash-nuevo"
    assert guardado.actualizado_por.id_persona == "1"


async def test_cambiar_password_rechaza_una_actual_incorrecta():
    service, repositorio_mock, _ = _servicio(verifica=False)

    with pytest.raises(PasswordActualIncorrectaError):
        await service.ejecutar(_dto())

    repositorio_mock.guardar.assert_not_called()


async def test_cambiar_password_rechaza_una_nueva_debil():
    service, repositorio_mock, _ = _servicio()

    with pytest.raises(PasswordDebilError):
        await service.ejecutar(_dto(nueva="corta"))

    repositorio_mock.guardar.assert_not_called()


async def test_cambiar_password_rechaza_una_nueva_igual_a_la_actual():
    service, repositorio_mock, _ = _servicio()

    with pytest.raises(PasswordNuevaIgualALaActualError):
        await service.ejecutar(_dto(actual="misma-clave-1", nueva="misma-clave-1"))

    repositorio_mock.guardar.assert_not_called()


async def test_cambiar_password_lanza_error_si_el_usuario_no_existe():
    service, repositorio_mock, _ = _servicio()
    repositorio_mock.obtener_por_id.return_value = None

    with pytest.raises(UsuarioNoEncontradoError):
        await service.ejecutar(_dto())
