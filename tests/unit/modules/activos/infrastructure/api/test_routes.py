from dataclasses import replace
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.historial_activo_repository import (
    HistorialActivoRepositoryPort,
)
from modules.activos.application.services.actualizar_activo import ActualizarActivoService
from modules.activos.application.services.cambiar_estado_activo import (
    CambiarEstadoActivoService,
)
from modules.activos.application.services.crear_activo import CrearActivoService
from modules.activos.application.services.listar_activos import ListarActivosService
from modules.activos.application.services.obtener_activo import ObtenerActivoService
from modules.activos.application.services.obtener_historial_activo import (
    ObtenerHistorialActivoService,
)
from modules.activos.domain.entities import Activo, EntradaHistorialActivo
from modules.activos.infrastructure.api.dependencies import (
    get_actualizar_activo_service,
    get_cambiar_estado_activo_service,
    get_crear_activo_service,
    get_listar_activos_service,
    get_obtener_activo_service,
    get_obtener_historial_activo_service,
)
from modules.activos.infrastructure.api.routes import router
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_usuario_autenticado,
)
from shared.infrastructure.api.error_handlers import register_error_handlers


class _RepositorioActivoEnMemoria(ActivoRepositoryPort):
    def __init__(self):
        self._items: dict[str, Activo] = {}
        self._contador = 0

    async def guardar(self, activo: Activo) -> Activo:
        if activo.id is None:
            self._contador += 1
            activo = replace(activo, id=str(self._contador))
        self._items[activo.id] = activo
        return activo

    async def obtener_por_id(self, id_activo: str):
        return self._items.get(id_activo)

    async def obtener_por_numero_inventario(self, numero_inventario: str):
        return next(
            (a for a in self._items.values() if a.numero_inventario == numero_inventario), None
        )

    async def listar(
        self,
        area_id,
        categoria_id,
        responsable_id,
        condicion_id,
        sede_id,
        lugar_id,
        estado_ciclo_vida,
        busqueda,
        skip,
        limit,
    ):
        valores = list(self._items.values())
        if area_id:
            valores = [a for a in valores if a.area_id == area_id]
        return valores[skip : skip + limit]


class _RepositorioHistorialEnMemoria(HistorialActivoRepositoryPort):
    def __init__(self):
        self._items: list[EntradaHistorialActivo] = []
        self._contador = 0

    async def registrar(self, entrada: EntradaHistorialActivo) -> EntradaHistorialActivo:
        self._contador += 1
        entrada = replace(entrada, id=str(self._contador))
        self._items.append(entrada)
        return entrada

    async def listar_por_activo(self, activo_id: str):
        return [e for e in self._items if e.activo_id == activo_id]


_ACTIVO_DE_PRUEBA = {
    "nombre": "Laptop Dell",
    "numero_inventario": "INV-001",
    "tipo": "activo_fijo",
    "categoria_id": "c1",
    "area_id": "a1",
    "responsable_id": "u1",
    "condicion_id": "cond1",
    "sede_id": "s1",
    "lugar_id": "l1",
    "valor": "1500000",
    "fecha_adquisicion": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
}


def _crear_cliente_de_prueba():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    repo_activo = _RepositorioActivoEnMemoria()
    repo_historial = _RepositorioHistorialEnMemoria()

    app.dependency_overrides[get_crear_activo_service] = lambda: CrearActivoService(repo_activo)
    app.dependency_overrides[get_listar_activos_service] = lambda: ListarActivosService(
        repo_activo
    )
    app.dependency_overrides[get_obtener_activo_service] = lambda: ObtenerActivoService(
        repo_activo
    )
    app.dependency_overrides[get_actualizar_activo_service] = (
        lambda: ActualizarActivoService(repo_activo, repo_historial)
    )
    app.dependency_overrides[get_cambiar_estado_activo_service] = (
        lambda: CambiarEstadoActivoService(repo_activo, repo_historial)
    )
    app.dependency_overrides[get_obtener_historial_activo_service] = (
        lambda: ObtenerHistorialActivoService(repo_activo, repo_historial)
    )

    identidad_admin = IdentidadUsuarioAutenticada(
        id_usuario="0", email="admin@example.com", nombre="Admin", rol="administrador_general"
    )
    app.dependency_overrides[requiere_usuario_autenticado] = lambda: identidad_admin

    return TestClient(app)


def test_crear_obtener_y_listar_activo_de_punta_a_punta():
    cliente = _crear_cliente_de_prueba()

    respuesta_crear = cliente.post("/api/activos", json=_ACTIVO_DE_PRUEBA)
    assert respuesta_crear.status_code == 201
    id_activo = respuesta_crear.json()["data"]["id"]

    respuesta_obtener = cliente.get(f"/api/activos/{id_activo}")
    assert respuesta_obtener.status_code == 200
    assert respuesta_obtener.json()["data"]["estado_ciclo_vida"] == "disponible"
    assert respuesta_obtener.json()["data"]["numero_inventario"] == "INV-001"

    respuesta_listar = cliente.get("/api/activos", params={"area_id": "a1"})
    assert respuesta_listar.status_code == 200
    assert len(respuesta_listar.json()["data"]) == 1


def test_crear_activo_con_numero_inventario_duplicado_retorna_409_con_code_act_001():
    cliente = _crear_cliente_de_prueba()
    cliente.post("/api/activos", json=_ACTIVO_DE_PRUEBA)

    respuesta = cliente.post("/api/activos", json=_ACTIVO_DE_PRUEBA)

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "ACT-001"


def test_actualizar_activo_registra_historial_y_queda_consultable():
    cliente = _crear_cliente_de_prueba()
    id_activo = cliente.post("/api/activos", json=_ACTIVO_DE_PRUEBA).json()["data"]["id"]

    respuesta_actualizar = cliente.put(
        f"/api/activos/{id_activo}", json={"responsable_id": "u2"}
    )
    assert respuesta_actualizar.status_code == 200
    assert respuesta_actualizar.json()["data"]["responsable_id"] == "u2"

    respuesta_historial = cliente.get(f"/api/activos/{id_activo}/historial")
    assert respuesta_historial.status_code == 200
    entradas = respuesta_historial.json()["data"]
    assert len(entradas) == 1
    assert entradas[0]["campo"] == "responsable_id"


def test_cambiar_estado_con_transicion_valida():
    cliente = _crear_cliente_de_prueba()
    id_activo = cliente.post("/api/activos", json=_ACTIVO_DE_PRUEBA).json()["data"]["id"]

    respuesta = cliente.put(
        f"/api/activos/{id_activo}/estado", json={"estado_nuevo": "prestado"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["estado_ciclo_vida"] == "prestado"


def test_cambiar_estado_con_transicion_invalida_retorna_422_con_code_act_003():
    cliente = _crear_cliente_de_prueba()
    id_activo = cliente.post("/api/activos", json=_ACTIVO_DE_PRUEBA).json()["data"]["id"]
    cliente.put(f"/api/activos/{id_activo}/estado", json={"estado_nuevo": "dado_de_baja"})

    respuesta = cliente.put(
        f"/api/activos/{id_activo}/estado", json={"estado_nuevo": "disponible"}
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "ACT-003"
