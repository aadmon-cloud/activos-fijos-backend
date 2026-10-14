from dataclasses import replace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.permisos.application.ports.permisos_repository import PermisosRolRepositoryPort
from modules.permisos.application.services.actualizar_permisos_rol import ActualizarPermisosRolService
from modules.permisos.application.services.listar_historial import ListarHistorialPermisosService
from modules.permisos.application.services.obtener_matriz import ObtenerMatrizPermisosService
from modules.permisos.application.services.restablecer_permisos_rol import RestablecerPermisosRolService
from modules.permisos.infrastructure.api.dependencies import (
    get_actualizar_permisos_rol_service,
    get_listar_historial_service,
    get_obtener_matriz_service,
    get_restablecer_permisos_rol_service,
)
from modules.permisos.infrastructure.api.routes import router
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.domain.permisos import CLAVES_BASE, CLAVES_FUNCIONES, permisos_por_defecto
from shared.infrastructure.api.dependencies.user_authentication import requiere_usuario_autenticado
from shared.infrastructure.api.error_handlers import register_error_handlers

_BASE = sorted(CLAVES_BASE)


class _RepositorioEnMemoria(PermisosRolRepositoryPort):
    def __init__(self):
        self.documentos = {}
        self.historial = []

    async def obtener(self, rol):
        return self.documentos.get(rol)

    async def listar(self):
        return list(self.documentos.values())

    async def guardar(self, permisos_rol):
        guardado = replace(permisos_rol, id=permisos_rol.id or f"id-{permisos_rol.rol}")
        self.documentos[guardado.rol] = guardado
        return guardado

    async def registrar_cambios(self, cambios):
        self.historial.extend(cambios)

    async def listar_historial(self, rol, skip, limit):
        cambios = [c for c in reversed(self.historial) if rol is None or c.rol == rol]
        return cambios[skip : skip + limit]


class _Escenario:
    def __init__(self):
        self.rol = "super_administrador"
        self.repo = _RepositorioEnMemoria()

    def como(self, rol: str) -> "_Escenario":
        self.rol = rol
        return self


def _crear_cliente():
    escenario = _Escenario()
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    actualizar = ActualizarPermisosRolService(escenario.repo)
    app.dependency_overrides[get_obtener_matriz_service] = lambda: ObtenerMatrizPermisosService(escenario.repo)
    app.dependency_overrides[get_actualizar_permisos_rol_service] = lambda: actualizar
    app.dependency_overrides[get_restablecer_permisos_rol_service] = lambda: RestablecerPermisosRolService(actualizar)
    app.dependency_overrides[get_listar_historial_service] = lambda: ListarHistorialPermisosService(escenario.repo)
    app.dependency_overrides[requiere_usuario_autenticado] = lambda: IdentidadUsuarioAutenticada(
        id_usuario="9", email="ana@example.com", nombre="Ana Super", rol=escenario.rol
    )

    return TestClient(app), escenario


# Quien puede entrar


def test_solo_el_super_administrador_puede_usar_estas_rutas():
    cliente, escenario = _crear_cliente()
    escenario.como("administrador_general")

    assert cliente.get("/api/permisos/matriz").status_code == 403
    assert cliente.put("/api/permisos/roles/empleado", json={"permisos": _BASE}).status_code == 403
    assert cliente.post("/api/permisos/roles/empleado/restablecer").status_code == 403
    assert cliente.get("/api/permisos/historial").status_code == 403


def test_un_empleado_tampoco_puede():
    cliente, escenario = _crear_cliente()
    escenario.como("empleado")

    assert cliente.get("/api/permisos/matriz").json()["code"] == "AUTH-003"


# Matriz


def test_la_matriz_trae_el_catalogo_y_los_roles():
    cliente, _ = _crear_cliente()

    respuesta = cliente.get("/api/permisos/matriz")

    assert respuesta.status_code == 200
    datos = respuesta.json()["data"]
    assert {f["clave"] for f in datos["funciones"]} == CLAVES_FUNCIONES
    assert [r["rol"] for r in datos["roles"]][0] == "super_administrador"
    assert datos["roles"][0]["editable"] is False
    empleado = next(r for r in datos["roles"] if r["rol"] == "empleado")
    assert set(empleado["permisos"]) == permisos_por_defecto("empleado")
    assert empleado["etiqueta"] == "Empleado"


def test_cada_funcion_indica_si_es_basica():
    cliente, _ = _crear_cliente()

    funciones = cliente.get("/api/permisos/matriz").json()["data"]["funciones"]

    assert {f["clave"] for f in funciones if f["es_base"]} == CLAVES_BASE


# Actualizar


def test_habilitar_una_funcion_a_un_rol_se_refleja_en_la_matriz_y_en_el_historial():
    cliente, _ = _crear_cliente()

    respuesta = cliente.put("/api/permisos/roles/empleado", json={"permisos": [*_BASE, "usuarios-ver"]})

    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["permisos"] == sorted([*_BASE, "usuarios-ver"])

    matriz = cliente.get("/api/permisos/matriz").json()["data"]
    empleado = next(r for r in matriz["roles"] if r["rol"] == "empleado")
    assert "usuarios-ver" in empleado["permisos"]

    historial = cliente.get("/api/permisos/historial").json()["data"]
    assert any(c["permiso"] == "usuarios-ver" and c["accion"] == "habilitado" for c in historial)
    assert historial[0]["por_nombre"] == "Ana Super"


def test_actualizar_una_funcion_inexistente_responde_400():
    cliente, _ = _crear_cliente()

    respuesta = cliente.put("/api/permisos/roles/empleado", json={"permisos": [*_BASE, "usuarios-volar"]})

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "PER-003"


def test_no_se_puede_quitar_una_funcion_base():
    cliente, _ = _crear_cliente()

    respuesta = cliente.put("/api/permisos/roles/empleado", json={"permisos": ["home-ver"]})

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "PER-004"


def test_no_se_pueden_editar_los_permisos_del_super_administrador():
    cliente, _ = _crear_cliente()

    respuesta = cliente.put("/api/permisos/roles/super_administrador", json={"permisos": _BASE})

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "PER-002"


def test_actualizar_un_rol_inexistente_responde_404():
    cliente, _ = _crear_cliente()

    respuesta = cliente.put("/api/permisos/roles/rol-inventado", json={"permisos": _BASE})

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "PER-001"


def test_actualizar_sin_el_campo_permisos_responde_422_de_validacion():
    cliente, _ = _crear_cliente()

    assert cliente.put("/api/permisos/roles/empleado", json={}).status_code == 422


def test_un_cuerpo_con_demasiadas_funciones_se_rechaza():
    cliente, _ = _crear_cliente()

    assert cliente.put("/api/permisos/roles/empleado", json={"permisos": ["x"] * 101}).status_code == 422


# Restablecer


def test_restablecer_devuelve_el_rol_a_la_matriz_de_fabrica():
    cliente, _ = _crear_cliente()
    cliente.put("/api/permisos/roles/empleado", json={"permisos": [*_BASE, "usuarios-ver"]})

    respuesta = cliente.post("/api/permisos/roles/empleado/restablecer")

    assert respuesta.status_code == 200
    assert set(respuesta.json()["data"]["permisos"]) == permisos_por_defecto("empleado")


def test_restablecer_al_super_administrador_responde_422():
    cliente, _ = _crear_cliente()

    assert cliente.post("/api/permisos/roles/super_administrador/restablecer").status_code == 422


# Historial


def test_el_historial_se_filtra_por_rol_y_valida_el_rol():
    cliente, _ = _crear_cliente()
    cliente.put("/api/permisos/roles/empleado", json={"permisos": [*_BASE, "usuarios-ver"]})
    cliente.put("/api/permisos/roles/jefe_area", json={"permisos": [*_BASE, "catalogos-ver"]})

    filtrado = cliente.get("/api/permisos/historial", params={"rol": "jefe_area"}).json()["data"]

    assert {c["rol"] for c in filtrado} == {"jefe_area"}
    assert cliente.get("/api/permisos/historial", params={"rol": "rol-inventado"}).status_code == 404


def test_el_historial_valida_los_limites_de_paginacion():
    cliente, _ = _crear_cliente()

    assert cliente.get("/api/permisos/historial", params={"limit": 0}).status_code == 422
    assert cliente.get("/api/permisos/historial", params={"limit": 501}).status_code == 422
    assert cliente.get("/api/permisos/historial", params={"skip": -1}).status_code == 422
