from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.usuarios.application.ports.verificador_identidad_google import (
    IdentidadGoogle,
    VerificadorIdentidadGooglePort,
)
from modules.usuarios.application.services.autenticar_con_google import AutenticarConGoogleService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.domain.errors import TokenGoogleInvalidoError
from modules.usuarios.infrastructure.api.dependencies import (
    get_autenticar_con_google_service,
    requiere_login_password_habilitado,
)
from modules.usuarios.infrastructure.api.routes import router
from modules.usuarios.infrastructure.security.jwt_emisor_token import JWTEmisorToken
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.api.error_handlers import register_error_handlers

_CORREO = "ana@fundacion.org"


class _VerificadorGoogleFalso(VerificadorIdentidadGooglePort):
    """Acepta el token «valido-<correo>» y rechaza cualquier otro."""

    async def verificar(self, credencial, nonce):
        if not credencial.startswith("valido-"):
            raise TokenGoogleInvalidoError()

        return IdentidadGoogle(email=credencial.removeprefix("valido-"))


def _usuario(activo=True) -> Usuario:
    return Usuario(
        id="u1",
        email=_CORREO,
        nombre="Ana",
        apellido="Garcia",
        password_hash="no-se-usa",
        rol=RolUsuario.ADMINISTRADOR_GENERAL,
        area_id=None,
        telefono=None,
        identificacion=None,
        activo=activo,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


def _cliente(usuario=None, password_habilitado=False):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    repo = AsyncMock()
    repo.obtener_por_email.side_effect = lambda email: usuario if usuario and email == _CORREO else None
    app.dependency_overrides[get_autenticar_con_google_service] = lambda: AutenticarConGoogleService(
        repo, _VerificadorGoogleFalso(), JWTEmisorToken()
    )
    if password_habilitado:
        app.dependency_overrides[requiere_login_password_habilitado] = lambda: None

    return TestClient(app)


def _entrar(cliente, credencial, nonce="nonce-de-prueba"):
    return cliente.post("/api/usuarios/login/google", json={"credencial": credencial, "nonce": nonce})


def test_un_usuario_registrado_abre_la_sesion_por_cookie_httponly_sin_token_en_el_cuerpo():
    cliente = _cliente(_usuario())

    respuesta = _entrar(cliente, f"valido-{_CORREO}")

    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["usuario"]["email"] == _CORREO
    cookie = respuesta.headers["set-cookie"]
    assert "access_token=" in cookie and "HttpOnly" in cookie
    assert "access_token" not in respuesta.text


def test_una_cuenta_no_registrada_retorna_401_con_usr_010():
    cliente = _cliente(None)

    respuesta = _entrar(cliente, "valido-desconocido@example.com")

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "USR-010"
    assert "set-cookie" not in respuesta.headers


def test_un_usuario_desactivado_retorna_401_con_usr_010():
    cliente = _cliente(_usuario(activo=False))

    respuesta = _entrar(cliente, f"valido-{_CORREO}")

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "USR-010"


def test_un_token_invalido_retorna_401_con_usr_009():
    cliente = _cliente(_usuario())

    respuesta = _entrar(cliente, "token-falso-que-no-es-de-google")

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "USR-009"
    assert "set-cookie" not in respuesta.headers


def test_se_rechazan_los_cuerpos_mal_formados():
    cliente = _cliente(_usuario())

    assert _entrar(cliente, "corto").status_code == 422
    assert _entrar(cliente, "x" * 5000).status_code == 422
    assert _entrar(cliente, f"valido-{_CORREO}", nonce="").status_code == 422
    assert cliente.post("/api/usuarios/login/google", json={"credencial": f"valido-{_CORREO}"}).status_code == 422


def test_el_ingreso_con_contrasena_esta_deshabilitado_por_defecto():
    cliente = _cliente(_usuario())

    respuesta = cliente.post("/api/usuarios/login", json={"email": _CORREO, "password": "password123"})

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "USR-012"
    assert "set-cookie" not in respuesta.headers
