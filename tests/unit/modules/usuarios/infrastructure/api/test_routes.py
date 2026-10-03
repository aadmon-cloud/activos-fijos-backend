from dataclasses import replace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.application.services.actualizar_usuario import ActualizarUsuarioService
from modules.usuarios.application.services.autenticar_usuario import AutenticarUsuarioService
from modules.usuarios.application.services.desactivar_usuario import DesactivarUsuarioService
from modules.usuarios.application.services.listar_usuarios import ListarUsuariosService
from modules.usuarios.application.services.obtener_usuario import ObtenerUsuarioService
from modules.usuarios.application.services.registrar_usuario import RegistrarUsuarioService
from modules.usuarios.domain.entities import Usuario
from modules.usuarios.infrastructure.api.dependencies import (
    get_actualizar_usuario_service,
    get_autenticar_usuario_service,
    get_desactivar_usuario_service,
    get_listar_usuarios_service,
    get_obtener_usuario_service,
    get_registrar_usuario_service,
)
from modules.usuarios.infrastructure.api.routes import router
from modules.usuarios.infrastructure.security.bcrypt_hasher import BcryptHasher
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_usuario_autenticado,
)
from shared.infrastructure.api.error_handlers import register_error_handlers


class _EmisorTokenFalso:
    def emitir(self, usuario: Usuario) -> str:
        return f"token-de-{usuario.id}"


class _VerificadorAreaVerdadero:
    async def existe(self, area_id: str) -> bool:
        return True


class _RepositorioEnMemoria(UsuarioRepositoryPort):
    def __init__(self):
        self._usuarios: dict[str, Usuario] = {}
        self._contador = 0

    async def guardar(self, usuario: Usuario) -> Usuario:
        if usuario.id is None:
            self._contador += 1
            usuario = replace(usuario, id=str(self._contador))
        self._usuarios[usuario.id] = usuario
        return usuario

    async def obtener_por_id(self, id_usuario: str) -> Usuario | None:
        return self._usuarios.get(id_usuario)

    async def obtener_por_email(self, email: str) -> Usuario | None:
        return next((u for u in self._usuarios.values() if u.email == email), None)

    async def obtener_por_identificacion(self, identificacion: str) -> Usuario | None:
        return next(
            (u for u in self._usuarios.values() if u.identificacion == identificacion), None
        )

    async def listar(self, busqueda, skip, limit) -> list[Usuario]:
        valores = list(self._usuarios.values())
        return valores[skip : skip + limit]


_USUARIO_DE_PRUEBA = {
    "email": "ana@example.com",
    "nombre": "Ana",
    "apellido": "Garcia",
    "password": "password123",
    "rol": "empleado",
}


def _crear_cliente_de_prueba():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    repositorio = _RepositorioEnMemoria()
    hasher = BcryptHasher()
    emisor_token = _EmisorTokenFalso()
    verificador_area = _VerificadorAreaVerdadero()

    app.dependency_overrides[get_registrar_usuario_service] = (
        lambda: RegistrarUsuarioService(repositorio, hasher, verificador_area)
    )
    app.dependency_overrides[get_autenticar_usuario_service] = (
        lambda: AutenticarUsuarioService(repositorio, hasher, emisor_token)
    )
    app.dependency_overrides[get_listar_usuarios_service] = lambda: ListarUsuariosService(
        repositorio
    )
    app.dependency_overrides[get_obtener_usuario_service] = lambda: ObtenerUsuarioService(
        repositorio
    )
    app.dependency_overrides[get_actualizar_usuario_service] = (
        lambda: ActualizarUsuarioService(repositorio, verificador_area)
    )
    app.dependency_overrides[get_desactivar_usuario_service] = (
        lambda: DesactivarUsuarioService(repositorio)
    )

    identidad_admin = IdentidadUsuarioAutenticada(
        id_usuario="0", email="admin@example.com", nombre="Admin", rol="administrador_general"
    )
    app.dependency_overrides[requiere_usuario_autenticado] = lambda: identidad_admin

    return TestClient(app), repositorio


def test_registrar_listar_y_obtener_usuario_de_punta_a_punta():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta_crear = cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA)
    assert respuesta_crear.status_code == 201
    assert respuesta_crear.json()["status"] == "success"
    id_usuario = respuesta_crear.json()["data"]["id"]

    respuesta_listar = cliente.get("/api/usuarios")
    assert respuesta_listar.status_code == 200
    assert len(respuesta_listar.json()["data"]) == 1

    respuesta_obtener = cliente.get(f"/api/usuarios/{id_usuario}")
    assert respuesta_obtener.status_code == 200
    assert respuesta_obtener.json()["data"]["email"] == "ana@example.com"


def test_registrar_usuario_con_email_duplicado_retorna_409_con_code_usr_001():
    cliente, _ = _crear_cliente_de_prueba()
    cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA)

    respuesta = cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA)

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "USR-001"


def test_login_con_credenciales_validas_retorna_token():
    cliente, _ = _crear_cliente_de_prueba()
    cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA)

    respuesta = cliente.post(
        "/api/usuarios/login",
        json={"email": "ana@example.com", "password": "password123"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["access_token"]


def test_login_con_credenciales_invalidas_retorna_401_con_code_usr_004():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post(
        "/api/usuarios/login",
        json={"email": "inexistente@example.com", "password": "cualquiera"},
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "USR-004"


def test_desactivar_usuario_marca_activo_en_false():
    cliente, repositorio = _crear_cliente_de_prueba()
    respuesta_crear = cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA)
    id_usuario = respuesta_crear.json()["data"]["id"]

    respuesta = cliente.delete(f"/api/usuarios/{id_usuario}")

    assert respuesta.status_code == 200
    assert repositorio._usuarios[id_usuario].activo is False
