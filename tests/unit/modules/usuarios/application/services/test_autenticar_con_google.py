from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.usuarios.application.dto.login_google_dto import LoginGoogleDTO
from modules.usuarios.application.ports.verificador_identidad_google import IdentidadGoogle
from modules.usuarios.application.services.autenticar_con_google import AutenticarConGoogleService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.domain.errors import CuentaGoogleSinAccesoError, TokenGoogleInvalidoError
from shared.domain.entities.audit import AuditPersona


def _usuario(**overrides) -> Usuario:
    valores = dict(
        id="u1",
        email="ana@fundacion.org",
        nombre="Ana",
        apellido="Garcia",
        password_hash="no-se-usa",
        rol=RolUsuario.ADMINISTRADOR_GENERAL,
        area_id=None,
        telefono=None,
        identificacion=None,
        activo=True,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)

    return Usuario(**valores)


def _servicio(usuario=None, email="ana@fundacion.org"):
    repo = AsyncMock()
    repo.obtener_por_email.return_value = usuario
    verificador = AsyncMock()
    verificador.verificar.return_value = IdentidadGoogle(email=email)
    emisor = MagicMock()
    emisor.emitir.return_value = "jwt-del-sistema"

    return AutenticarConGoogleService(repo, verificador, emisor), repo, verificador, emisor


_DTO = LoginGoogleDTO(credencial="token-de-google", nonce="nonce-1234")


async def test_un_usuario_registrado_y_activo_abre_sesion():
    service, repo, verificador, emisor = _servicio(_usuario())

    token = await service.ejecutar(_DTO)

    verificador.verificar.assert_awaited_once_with("token-de-google", "nonce-1234")
    assert token.access_token == "jwt-del-sistema"
    assert token.usuario.email == "ana@fundacion.org"
    emisor.emitir.assert_called_once()


async def test_el_correo_de_google_se_busca_en_minusculas_y_sin_espacios():
    service, repo, _, _ = _servicio(_usuario(), email="  Ana@Fundacion.ORG ")

    await service.ejecutar(_DTO)

    repo.obtener_por_email.assert_awaited_once_with("ana@fundacion.org")


async def test_una_cuenta_que_no_esta_registrada_no_entra_ni_se_crea():
    service, repo, _, emisor = _servicio(None)

    with pytest.raises(CuentaGoogleSinAccesoError):
        await service.ejecutar(_DTO)

    repo.guardar.assert_not_called()
    emisor.emitir.assert_not_called()


async def test_un_usuario_desactivado_no_entra():
    service, _, _, emisor = _servicio(_usuario(activo=False))

    with pytest.raises(CuentaGoogleSinAccesoError):
        await service.ejecutar(_DTO)

    emisor.emitir.assert_not_called()


async def test_si_google_rechaza_el_token_no_se_consulta_ni_se_emite_sesion():
    service, repo, verificador, emisor = _servicio(_usuario())
    verificador.verificar.side_effect = TokenGoogleInvalidoError()

    with pytest.raises(TokenGoogleInvalidoError):
        await service.ejecutar(_DTO)

    repo.obtener_por_email.assert_not_called()
    emisor.emitir.assert_not_called()
