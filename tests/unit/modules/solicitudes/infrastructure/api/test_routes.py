from dataclasses import replace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.solicitudes.application.ports.activo_resumen_port import (
    ActivoResumen,
    ActivoResumenPort,
)
from modules.solicitudes.application.ports.solicitud_repository import SolicitudRepositoryPort
from modules.solicitudes.application.services.agregar_seguimiento_solicitud import (
    AgregarSeguimientoSolicitudService,
)
from modules.solicitudes.application.services.cambiar_estado_solicitud import (
    CambiarEstadoSolicitudService,
)
from modules.solicitudes.application.services.crear_solicitud import CrearSolicitudService
from modules.solicitudes.application.services.listar_solicitudes import ListarSolicitudesService
from modules.solicitudes.application.services.obtener_solicitud import ObtenerSolicitudService
from modules.solicitudes.domain.entities import Solicitud
from modules.solicitudes.infrastructure.api.dependencies import (
    get_agregar_seguimiento_solicitud_service,
    get_cambiar_estado_solicitud_service,
    get_crear_solicitud_service,
    get_listar_solicitudes_service,
    get_obtener_solicitud_service,
)
from modules.solicitudes.infrastructure.api.routes import router
from shared.application.notifications.ports import NotificadorPort
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_usuario_autenticado,
)
from shared.infrastructure.api.error_handlers import register_error_handlers


class _RepositorioSolicitudEnMemoria(SolicitudRepositoryPort):
    def __init__(self):
        self._items: dict[str, Solicitud] = {}
        self._contador = 0

    async def guardar(self, solicitud: Solicitud) -> Solicitud:
        if solicitud.id is None:
            self._contador += 1
            solicitud = replace(solicitud, id=str(self._contador))
        self._items[solicitud.id] = solicitud
        return solicitud

    async def obtener_por_id(self, id_solicitud: str):
        return self._items.get(id_solicitud)

    async def listar(
        self, tipo, estado, activo_id, rol_asignado, area_id, creado_por_id, skip, limit
    ):
        return list(self._items.values())[skip : skip + limit]


class _ActivoResumenFalso(ActivoResumenPort):
    def __init__(self, resumen: ActivoResumen | None):
        self._resumen = resumen

    async def obtener_resumen(self, activo_id: str):
        return self._resumen


class _NotificadorFalso(NotificadorPort):
    def __init__(self):
        self.enviados = []

    async def notificar(self, destinatarios, asunto, cuerpo) -> None:
        self.enviados.append((destinatarios, asunto, cuerpo))


class _IdentidadContenedor:
    def __init__(self, identidad: IdentidadUsuarioAutenticada):
        self.valor = identidad


_ACTIVO_ID = "a" * 24
_RESPONSABLE_ID = "u1"


def _crear_cliente_de_prueba():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    repo_solicitud = _RepositorioSolicitudEnMemoria()
    activo_resumen = _ActivoResumenFalso(
        ActivoResumen(id=_ACTIVO_ID, responsable_id=_RESPONSABLE_ID, area_id="area-1")
    )
    notificador = _NotificadorFalso()

    app.dependency_overrides[get_crear_solicitud_service] = (
        lambda: CrearSolicitudService(repo_solicitud, activo_resumen, notificador)
    )
    app.dependency_overrides[get_listar_solicitudes_service] = (
        lambda: ListarSolicitudesService(repo_solicitud)
    )
    app.dependency_overrides[get_obtener_solicitud_service] = (
        lambda: ObtenerSolicitudService(repo_solicitud)
    )
    app.dependency_overrides[get_cambiar_estado_solicitud_service] = (
        lambda: CambiarEstadoSolicitudService(repo_solicitud, notificador)
    )
    app.dependency_overrides[get_agregar_seguimiento_solicitud_service] = (
        lambda: AgregarSeguimientoSolicitudService(repo_solicitud)
    )

    contenedor = _IdentidadContenedor(
        IdentidadUsuarioAutenticada(
            id_usuario=_RESPONSABLE_ID, email="u1@example.com", nombre="Responsable", rol="empleado"
        )
    )
    app.dependency_overrides[requiere_usuario_autenticado] = lambda: contenedor.valor

    return TestClient(app), contenedor, notificador


_SOLICITUD_DE_PRUEBA = {
    "tipo": "mantenimiento",
    "activo_id": _ACTIVO_ID,
    "descripcion": "El equipo hace ruido",
    "prioridad": "media",
}


def test_crear_listar_y_obtener_solicitud_de_punta_a_punta():
    cliente, _, notificador = _crear_cliente_de_prueba()

    respuesta_crear = cliente.post("/api/solicitudes", json=_SOLICITUD_DE_PRUEBA)
    assert respuesta_crear.status_code == 201
    id_solicitud = respuesta_crear.json()["data"]["id"]
    assert len(notificador.enviados) == 1

    respuesta_obtener = cliente.get(f"/api/solicitudes/{id_solicitud}")
    assert respuesta_obtener.status_code == 200
    assert respuesta_obtener.json()["data"]["rol_asignado"] == "mantenimiento"

    respuesta_listar = cliente.get("/api/solicitudes")
    assert respuesta_listar.status_code == 200
    assert len(respuesta_listar.json()["data"]) == 1


def test_crear_solicitud_sin_ser_responsable_retorna_422_con_code_sol_003():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    contenedor.valor = IdentidadUsuarioAutenticada(
        id_usuario="otro-usuario", email="x@example.com", nombre="Otro", rol="empleado"
    )

    respuesta = cliente.post("/api/solicitudes", json=_SOLICITUD_DE_PRUEBA)

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "SOL-003"


def test_cambiar_estado_y_agregar_seguimiento_de_punta_a_punta():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    id_solicitud = cliente.post("/api/solicitudes", json=_SOLICITUD_DE_PRUEBA).json()["data"]["id"]

    contenedor.valor = IdentidadUsuarioAutenticada(
        id_usuario="tecnico-1", email="t@example.com", nombre="Tecnico", rol="mantenimiento"
    )
    respuesta_estado = cliente.put(
        f"/api/solicitudes/{id_solicitud}/estado", json={"estado_nuevo": "en_proceso"}
    )
    assert respuesta_estado.status_code == 200
    assert respuesta_estado.json()["data"]["estado"] == "en_proceso"

    respuesta_seguimiento = cliente.post(
        f"/api/solicitudes/{id_solicitud}/seguimiento", json={"comentario": "Ya se esta revisando"}
    )
    assert respuesta_seguimiento.status_code == 201
    assert len(respuesta_seguimiento.json()["data"]["seguimiento"]) == 2


def test_cambiar_estado_sin_permiso_retorna_403_con_code_sol_005():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    id_solicitud = cliente.post("/api/solicitudes", json=_SOLICITUD_DE_PRUEBA).json()["data"]["id"]

    contenedor.valor = IdentidadUsuarioAutenticada(
        id_usuario="desconocido", email="d@example.com", nombre="D", rol="tecnologia"
    )
    respuesta = cliente.put(
        f"/api/solicitudes/{id_solicitud}/estado", json={"estado_nuevo": "en_proceso"}
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "SOL-005"
