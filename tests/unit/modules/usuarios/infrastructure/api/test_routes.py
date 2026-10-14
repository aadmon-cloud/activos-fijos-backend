from dataclasses import replace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.application.services.actualizar_usuario import ActualizarUsuarioService
from modules.usuarios.application.services.autenticar_usuario import AutenticarUsuarioService
from modules.usuarios.application.services.cambiar_password import CambiarPasswordService
from modules.usuarios.application.services.desactivar_usuario import DesactivarUsuarioService
from modules.usuarios.application.services.listar_directorio_usuarios import (
    ListarDirectorioUsuariosService,
)
from modules.usuarios.application.services.listar_usuarios import ListarUsuariosService
from modules.usuarios.application.services.obtener_usuario import ObtenerUsuarioService
from modules.usuarios.application.services.reactivar_usuario import ReactivarUsuarioService
from modules.usuarios.application.services.registrar_usuario import RegistrarUsuarioService
from modules.usuarios.application.services.restablecer_password import RestablecerPasswordService
from modules.usuarios.domain.entities import Usuario
from modules.usuarios.infrastructure.api.dependencies import (
    get_actualizar_usuario_service,
    get_autenticar_usuario_service,
    get_cambiar_password_service,
    get_desactivar_usuario_service,
    get_listar_directorio_usuarios_service,
    get_listar_usuarios_service,
    requiere_login_password_habilitado,
    get_obtener_usuario_service,
    get_reactivar_usuario_service,
    get_registrar_usuario_service,
    get_restablecer_password_service,
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
    app.dependency_overrides[get_listar_directorio_usuarios_service] = (
        lambda: ListarDirectorioUsuariosService(repositorio)
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
    app.dependency_overrides[get_reactivar_usuario_service] = (
        lambda: ReactivarUsuarioService(repositorio)
    )
    app.dependency_overrides[get_restablecer_password_service] = (
        lambda: RestablecerPasswordService(repositorio, hasher)
    )
    app.dependency_overrides[get_cambiar_password_service] = (
        lambda: CambiarPasswordService(repositorio, hasher)
    )

    # El ingreso es solo con Google; en estas pruebas se reabre el de contrasena para ejercitar las sesiones.
    app.dependency_overrides[requiere_login_password_habilitado] = lambda: None

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


def test_login_con_credenciales_validas_abre_sesion_por_cookie_httponly_sin_token_en_el_cuerpo():
    cliente, _ = _crear_cliente_de_prueba()
    cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA)

    respuesta = cliente.post(
        "/api/usuarios/login",
        json={"email": "ana@example.com", "password": "password123"},
    )

    assert respuesta.status_code == 200
    assert "access_token" not in respuesta.json()["data"]
    assert respuesta.json()["data"]["usuario"]["email"] == "ana@example.com"
    cookie = respuesta.headers["set-cookie"].lower()
    assert "access_token=token-de-" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api" in cookie
    assert "max-age=10800" in cookie


def test_logout_expira_la_cookie_de_sesion():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/usuarios/logout")

    assert respuesta.status_code == 200
    cookie = respuesta.headers["set-cookie"].lower()
    assert "access_token=" in cookie
    assert "max-age=0" in cookie


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


def _login(cliente, password: str) -> int:
    return cliente.post(
        "/api/usuarios/login", json={"email": "ana@example.com", "password": password}
    ).status_code


def test_desactivar_y_reactivar_usuario_controlan_el_login():
    cliente, _ = _crear_cliente_de_prueba()
    id_usuario = cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA).json()["data"]["id"]

    cliente.delete(f"/api/usuarios/{id_usuario}")
    assert _login(cliente, "password123") == 401

    respuesta = cliente.post(f"/api/usuarios/{id_usuario}/reactivar")

    assert respuesta.status_code == 200
    assert _login(cliente, "password123") == 200


def test_reactivar_usuario_inexistente_retorna_404_con_code_usr_005():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/usuarios/999/reactivar")

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "USR-005"


def test_admin_restablece_la_password_y_el_login_usa_la_nueva():
    cliente, _ = _crear_cliente_de_prueba()
    id_usuario = cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA).json()["data"]["id"]

    respuesta = cliente.put(
        f"/api/usuarios/{id_usuario}/password", json={"password_nueva": "otra-clave-456"}
    )

    assert respuesta.status_code == 200
    assert _login(cliente, "password123") == 401
    assert _login(cliente, "otra-clave-456") == 200


def test_usuario_cambia_su_propia_password_con_la_actual():
    cliente, _ = _crear_cliente_de_prueba()
    id_usuario = cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA).json()["data"]["id"]
    cliente.app.dependency_overrides[requiere_usuario_autenticado] = lambda: (
        IdentidadUsuarioAutenticada(
            id_usuario=id_usuario, email="ana@example.com", nombre="Ana", rol="empleado"
        )
    )

    respuesta = cliente.put(
        "/api/usuarios/me/password",
        json={"password_actual": "password123", "password_nueva": "otra-clave-456"},
    )

    assert respuesta.status_code == 200
    assert _login(cliente, "otra-clave-456") == 200


def test_cambiar_password_con_actual_incorrecta_retorna_400_con_code_usr_007():
    cliente, _ = _crear_cliente_de_prueba()
    id_usuario = cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA).json()["data"]["id"]
    cliente.app.dependency_overrides[requiere_usuario_autenticado] = lambda: (
        IdentidadUsuarioAutenticada(
            id_usuario=id_usuario, email="ana@example.com", nombre="Ana", rol="empleado"
        )
    )

    respuesta = cliente.put(
        "/api/usuarios/me/password",
        json={"password_actual": "incorrecta", "password_nueva": "otra-clave-456"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "USR-007"


def test_me_password_no_se_confunde_con_la_ruta_de_restablecer_de_otro_usuario():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.put(
        "/api/usuarios/me/password",
        json={"password_actual": "x", "password_nueva": "otra-clave-456"},
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "USR-005"


def test_el_directorio_lo_ve_cualquier_usuario_autenticado_y_solo_trae_nombres():
    cliente, _ = _crear_cliente_de_prueba()
    cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA)
    cliente.app.dependency_overrides[requiere_usuario_autenticado] = lambda: (
        IdentidadUsuarioAutenticada(
            id_usuario="x", email="e@example.com", nombre="Empleado", rol="empleado"
        )
    )

    respuesta = cliente.get("/api/usuarios/directorio")

    assert respuesta.status_code == 200
    personas = respuesta.json()["data"]
    assert len(personas) == 1
    assert set(personas[0]) == {"id", "nombre", "apellido"}


def test_el_listado_completo_de_usuarios_sigue_siendo_solo_del_administrador():
    cliente, _ = _crear_cliente_de_prueba()
    cliente.app.dependency_overrides[requiere_usuario_autenticado] = lambda: (
        IdentidadUsuarioAutenticada(
            id_usuario="x", email="e@example.com", nombre="Empleado", rol="empleado"
        )
    )

    assert cliente.get("/api/usuarios").status_code == 403


def test_el_ingreso_con_contrasena_esta_deshabilitado_por_defecto():
    cliente, _ = _crear_cliente_de_prueba()
    del cliente.app.dependency_overrides[requiere_login_password_habilitado]

    respuesta = cliente.post("/api/usuarios/login", json={"email": "a@example.com", "password": "password123"})

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "USR-012"


def test_un_usuario_se_registra_sin_contrasena_y_no_puede_entrar_con_una_inventada():
    cliente, _ = _crear_cliente_de_prueba()
    sin_password = {k: v for k, v in _USUARIO_DE_PRUEBA.items() if k != "password"}

    respuesta = cliente.post("/api/usuarios", json=sin_password)

    assert respuesta.status_code == 201
    assert _login(cliente, "password123") == 401



# Permisos en la sesion y proteccion del rol de Super administrador


def _como(cliente, rol: str, id_usuario: str = "0"):
    cliente.app.dependency_overrides[requiere_usuario_autenticado] = lambda: IdentidadUsuarioAutenticada(
        id_usuario=id_usuario, email="x@example.com", nombre="X", rol=rol
    )


def test_me_devuelve_las_funciones_habilitadas_para_su_rol():
    from shared.domain.permisos import permisos_por_defecto

    cliente, _ = _crear_cliente_de_prueba()
    cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA)  # id "1", rol empleado
    _como(cliente, "empleado", id_usuario="1")

    datos = cliente.get("/api/usuarios/me").json()["data"]

    assert datos["email"] == "ana@example.com"
    assert datos["permisos"] == sorted(permisos_por_defecto("empleado"))
    assert "usuarios-ver" not in datos["permisos"]


def test_el_login_tambien_devuelve_las_funciones_del_rol():
    from shared.domain.permisos import permisos_por_defecto

    cliente, _ = _crear_cliente_de_prueba()
    cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA)

    respuesta = cliente.post(
        "/api/usuarios/login", json={"email": "ana@example.com", "password": "password123"}
    )

    assert respuesta.json()["data"]["usuario"]["permisos"] == sorted(permisos_por_defecto("empleado"))


def test_los_listados_de_usuarios_no_llevan_permisos():
    cliente, _ = _crear_cliente_de_prueba()
    cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA)

    assert "permisos" not in cliente.get("/api/usuarios").json()["data"][0]


def test_el_super_administrador_recibe_todas_las_funciones_y_la_de_administracion():
    cliente, _ = _crear_cliente_de_prueba()
    _como(cliente, "super_administrador")
    cliente.post("/api/usuarios", json={**_USUARIO_DE_PRUEBA, "rol": "super_administrador"})  # id "1"
    _como(cliente, "super_administrador", id_usuario="1")

    permisos = cliente.get("/api/usuarios/me").json()["data"]["permisos"]

    assert "administracion-ver" in permisos
    assert "usuarios-crear" in permisos


def test_un_administrador_general_no_puede_crear_a_un_super_administrador():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/usuarios", json={**_USUARIO_DE_PRUEBA, "rol": "super_administrador"})

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "USR-013"


def test_un_administrador_general_no_puede_ascender_a_nadie_a_super_administrador():
    cliente, _ = _crear_cliente_de_prueba()
    cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA)

    respuesta = cliente.put("/api/usuarios/1", json={"rol": "super_administrador"})

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "USR-013"


def test_un_super_administrador_si_puede_crear_y_ascender():
    cliente, _ = _crear_cliente_de_prueba()
    _como(cliente, "super_administrador")

    assert cliente.post("/api/usuarios", json={**_USUARIO_DE_PRUEBA, "rol": "super_administrador"}).status_code == 201
    cliente.post("/api/usuarios", json={**_USUARIO_DE_PRUEBA, "email": "otra@example.com"})  # id "2"

    respuesta = cliente.put("/api/usuarios/2", json={"rol": "super_administrador"})

    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["rol"] == "super_administrador"


def test_un_administrador_general_no_puede_gestionar_a_un_super_administrador():
    cliente, _ = _crear_cliente_de_prueba()
    _como(cliente, "super_administrador")
    cliente.post("/api/usuarios", json={**_USUARIO_DE_PRUEBA, "rol": "super_administrador"})  # id "1"
    cliente.delete("/api/usuarios/1")
    _como(cliente, "administrador_general")

    assert cliente.delete("/api/usuarios/1").status_code == 403
    assert cliente.post("/api/usuarios/1/reactivar").status_code == 403
    assert cliente.put("/api/usuarios/1/password", json={"password_nueva": "otra-clave-123"}).status_code == 403
    assert cliente.put("/api/usuarios/1", json={"nombre": "Otro"}).status_code == 403


# El efecto de la matriz de permisos en las rutas


def _con_matriz(monkeypatch, permisos_por_rol: dict[str, list[str]]):
    from shared.infrastructure.security.consulta_permisos_rol_mongo import (
        ConsultaPermisosRolMongo,
        consulta_permisos_rol,
    )

    async def _leer(self, rol):
        return {"permisos": permisos_por_rol[rol]} if rol in permisos_por_rol else None

    monkeypatch.setattr(ConsultaPermisosRolMongo, "_leer_documento", _leer)
    consulta_permisos_rol.invalidar()


def test_quitarle_una_funcion_a_un_rol_bloquea_esa_ruta_de_inmediato(monkeypatch):
    from shared.domain.permisos import permisos_por_defecto

    cliente, _ = _crear_cliente_de_prueba()  # Administrador General
    assert cliente.get("/api/usuarios").status_code == 200

    _con_matriz(monkeypatch, {"administrador_general": sorted(permisos_por_defecto("administrador_general") - {"usuarios-ver"})})

    assert cliente.get("/api/usuarios").status_code == 403
    assert cliente.get("/api/usuarios").json()["code"] == "AUTH-003"
    # Las demas funciones del rol siguen funcionando
    assert cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA).status_code == 201


def test_darle_una_funcion_a_otro_rol_habilita_esa_ruta(monkeypatch):
    cliente, _ = _crear_cliente_de_prueba()
    _como(cliente, "empleado")
    assert cliente.get("/api/usuarios").status_code == 403

    _con_matriz(monkeypatch, {"empleado": ["home-ver", "cuenta-ver", "usuarios-ver"]})

    assert cliente.get("/api/usuarios").status_code == 200
    # Solo esa: crear sigue prohibido
    assert cliente.post("/api/usuarios", json=_USUARIO_DE_PRUEBA).status_code == 403


def test_el_super_administrador_conserva_todo_aunque_la_matriz_quede_vacia(monkeypatch):
    cliente, _ = _crear_cliente_de_prueba()
    _como(cliente, "super_administrador")
    _con_matriz(monkeypatch, {rol: ["home-ver", "cuenta-ver"] for rol in ("administrador_general", "empleado")})

    assert cliente.get("/api/usuarios").status_code == 200
