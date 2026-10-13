from dataclasses import replace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.solicitudes.application.ports.activo_estado_port import ActivoEstadoPort
from modules.solicitudes.application.ports.activo_resumen_port import (
    ActivoResumen,
    ActivoResumenPort,
)
from modules.solicitudes.application.ports.resolutor_referencias import (
    ActivoNombre,
    NombresReferenciasSolicitud,
    ResolutorReferenciasPort,
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


def _visible(solicitud: Solicitud, visible_para) -> bool:
    if visible_para is None:
        return True
    return (
        solicitud.creado_por.id_persona == visible_para.actor_id
        or solicitud.rol_asignado == visible_para.rol
        or (visible_para.area_id is not None and solicitud.area_id == visible_para.area_id)
    )


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

    def _filtradas(self, estado, visible_para):
        return [
            s
            for s in self._items.values()
            if _visible(s, visible_para) and (estado is None or s.estado == estado)
        ]

    async def listar(
        self, tipo, estado, activo_id, rol_asignado, area_id, creado_por_id, visible_para, skip, limit
    ):
        return self._filtradas(estado, visible_para)[skip : skip + limit]

    async def contar(
        self, tipo, estado, activo_id, rol_asignado, area_id, creado_por_id, visible_para
    ):
        return len(self._filtradas(estado, visible_para))


class _ActivoResumenFalso(ActivoResumenPort):
    def __init__(self, resumen: ActivoResumen | None):
        self._resumen = resumen

    async def obtener_resumen(self, activo_id: str):
        return self._resumen


class _ResolutorFalso(ResolutorReferenciasPort):
    async def resolver(self, referencias):
        return NombresReferenciasSolicitud(
            activos={"a" * 24: ActivoNombre(nombre="Laptop Dell", numero_inventario="INV-001")},
            areas={"area-1": "Tecnologia"},
        )


class _ActivoEstadoFalso(ActivoEstadoPort):
    def __init__(self):
        self.estado = "disponible"

    async def obtener_estado(self, activo_id: str):
        return self.estado

    async def cambiar_estado(self, activo_id, estado_nuevo, actor_id, actor_nombre) -> bool:
        self.estado = estado_nuevo

        return True


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


def _identidad(id_usuario: str, rol: str, area: str | None = None) -> IdentidadUsuarioAutenticada:
    return IdentidadUsuarioAutenticada(
        id_usuario=id_usuario,
        email=f"{id_usuario}@example.com",
        nombre=f"Nombre {id_usuario}",
        rol=rol,
        area_id=area,
    )


def _crear_cliente_de_prueba():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    repo_solicitud = _RepositorioSolicitudEnMemoria()
    activo_resumen = _ActivoResumenFalso(
        ActivoResumen(id=_ACTIVO_ID, responsable_id=_RESPONSABLE_ID, area_id="area-1")
    )
    resolutor = _ResolutorFalso()
    notificador = _NotificadorFalso()
    activo_estado = _ActivoEstadoFalso()

    app.dependency_overrides[get_crear_solicitud_service] = (
        lambda: CrearSolicitudService(repo_solicitud, activo_resumen, notificador)
    )
    app.dependency_overrides[get_listar_solicitudes_service] = (
        lambda: ListarSolicitudesService(repo_solicitud, resolutor)
    )
    app.dependency_overrides[get_obtener_solicitud_service] = (
        lambda: ObtenerSolicitudService(repo_solicitud, resolutor)
    )
    app.dependency_overrides[get_cambiar_estado_solicitud_service] = (
        lambda: CambiarEstadoSolicitudService(repo_solicitud, notificador, activo_estado)
    )
    app.dependency_overrides[get_agregar_seguimiento_solicitud_service] = (
        lambda: AgregarSeguimientoSolicitudService(repo_solicitud)
    )

    contenedor = _IdentidadContenedor(_identidad(_RESPONSABLE_ID, "empleado"))
    app.dependency_overrides[requiere_usuario_autenticado] = lambda: contenedor.valor

    cliente = TestClient(app)
    cliente.activo_estado = activo_estado

    return cliente, contenedor, notificador


_SOLICITUD_DE_PRUEBA = {
    "tipo": "mantenimiento",
    "activo_id": _ACTIVO_ID,
    "descripcion": "El equipo hace ruido",
    "prioridad": "media",
}


def _crear(cliente) -> str:
    return cliente.post("/api/solicitudes", json=_SOLICITUD_DE_PRUEBA).json()["data"]["id"]


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


def test_el_listado_trae_total_creador_fecha_y_nombres():
    cliente, _, _ = _crear_cliente_de_prueba()
    _crear(cliente)
    _crear(cliente)

    cuerpo = cliente.get("/api/solicitudes", params={"limit": 1}).json()

    assert cuerpo["meta"] == {"total": 2, "skip": 0, "limit": 1}
    assert len(cuerpo["data"]) == 1
    solicitud = cuerpo["data"][0]
    assert solicitud["activo_nombre"] == "Laptop Dell"
    assert solicitud["activo_numero_inventario"] == "INV-001"
    assert solicitud["creado_por_id"] == _RESPONSABLE_ID
    assert solicitud["creado_por_nombre"] == "Nombre u1"
    assert solicitud["fecha_creacion"]


def test_el_detalle_informa_los_estados_permitidos_y_si_puede_comentar():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    id_solicitud = _crear(cliente)

    como_solicitante = cliente.get(f"/api/solicitudes/{id_solicitud}").json()["data"]
    contenedor.valor = _identidad("tecnico-1", "mantenimiento")
    como_tecnico = cliente.get(f"/api/solicitudes/{id_solicitud}").json()["data"]

    assert como_solicitante["estados_permitidos"] == []
    assert como_solicitante["puede_comentar"] is True
    assert como_tecnico["estados_permitidos"] == ["en_proceso", "rechazada"]


def test_crear_solicitud_sin_ser_responsable_retorna_422_con_code_sol_003():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    contenedor.valor = _identidad("otro-usuario", "empleado")

    respuesta = cliente.post("/api/solicitudes", json=_SOLICITUD_DE_PRUEBA)

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "SOL-003"


def test_un_usuario_sin_relacion_no_ve_la_solicitud_ni_en_el_listado_ni_en_el_detalle():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    id_solicitud = _crear(cliente)
    contenedor.valor = _identidad("tercero-1", "tecnologia", "area-2")

    listado = cliente.get("/api/solicitudes").json()
    detalle = cliente.get(f"/api/solicitudes/{id_solicitud}")

    assert listado["data"] == []
    assert listado["meta"]["total"] == 0
    assert detalle.status_code == 404
    assert detalle.json()["code"] == "SOL-001"


def test_el_equipo_asignado_y_el_administrador_si_la_ven():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    id_solicitud = _crear(cliente)

    for identidad in (
        _identidad("tecnico-1", "mantenimiento"),
        _identidad("admin-1", "administrador_general"),
    ):
        contenedor.valor = identidad
        assert cliente.get(f"/api/solicitudes/{id_solicitud}").status_code == 200
        assert cliente.get("/api/solicitudes").json()["meta"]["total"] == 1


def test_el_solicitante_no_puede_procesar_su_propia_solicitud_retorna_403_con_sol_005():
    cliente, _, _ = _crear_cliente_de_prueba()
    id_solicitud = _crear(cliente)

    respuesta = cliente.put(
        f"/api/solicitudes/{id_solicitud}/estado", json={"estado_nuevo": "en_proceso"}
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "SOL-005"


def test_flujo_completo_el_equipo_resuelve_y_el_solicitante_cierra():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    id_solicitud = _crear(cliente)
    url = f"/api/solicitudes/{id_solicitud}/estado"

    contenedor.valor = _identidad("tecnico-1", "mantenimiento")
    assert cliente.put(url, json={"estado_nuevo": "en_proceso"}).status_code == 200
    assert cliente.put(url, json={"estado_nuevo": "resuelta"}).status_code == 200
    # El equipo no puede cerrar lo que el mismo resolvio.
    assert cliente.put(url, json={"estado_nuevo": "cerrada"}).status_code == 403

    contenedor.valor = _identidad(_RESPONSABLE_ID, "empleado")
    cierre = cliente.put(url, json={"estado_nuevo": "cerrada"})

    assert cierre.status_code == 200
    assert cierre.json()["data"]["estado"] == "cerrada"
    # 3 cambios de estado + 2 notas automaticas del activo (al aceptar y al resolver el mantenimiento).
    assert len(cierre.json()["data"]["seguimiento"]) == 5


def test_una_transicion_invalida_retorna_422_con_sol_004():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    id_solicitud = _crear(cliente)
    contenedor.valor = _identidad("tecnico-1", "mantenimiento")

    respuesta = cliente.put(
        f"/api/solicitudes/{id_solicitud}/estado", json={"estado_nuevo": "resuelta"}
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "SOL-004"


def test_cambiar_estado_o_comentar_sin_poder_ver_la_solicitud_responde_404():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    id_solicitud = _crear(cliente)
    contenedor.valor = _identidad("tercero-1", "tecnologia", "area-2")

    estado = cliente.put(
        f"/api/solicitudes/{id_solicitud}/estado", json={"estado_nuevo": "en_proceso"}
    )
    comentario = cliente.post(
        f"/api/solicitudes/{id_solicitud}/seguimiento", json={"comentario": "hola"}
    )

    assert estado.status_code == 404
    assert comentario.status_code == 404


def test_el_solicitante_y_el_equipo_pueden_comentar():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    id_solicitud = _crear(cliente)
    url = f"/api/solicitudes/{id_solicitud}/seguimiento"

    como_solicitante = cliente.post(url, json={"comentario": "Sigue fallando"})
    contenedor.valor = _identidad("tecnico-1", "mantenimiento")
    como_tecnico = cliente.post(url, json={"comentario": "Voy en camino"})

    assert como_solicitante.status_code == 201
    assert como_tecnico.status_code == 201
    assert len(como_tecnico.json()["data"]["seguimiento"]) == 2


def test_el_activo_cambia_solo_con_el_flujo_de_un_mantenimiento():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    id_solicitud = _crear(cliente)
    url = f"/api/solicitudes/{id_solicitud}/estado"
    contenedor.valor = _identidad("tecnico-1", "mantenimiento")

    cliente.put(url, json={"estado_nuevo": "en_proceso"})
    estado_al_aceptar = cliente.activo_estado.estado
    resuelta = cliente.put(url, json={"estado_nuevo": "resuelta"})

    assert estado_al_aceptar == "en_mantenimiento"
    assert cliente.activo_estado.estado == "disponible"
    comentarios = [e["comentario"] for e in resuelta.json()["data"]["seguimiento"]]
    assert any("cambió de 'Disponible' a 'En mantenimiento'" in c for c in comentarios)
    assert any("cambió de 'En mantenimiento' a 'Disponible'" in c for c in comentarios)


def test_rechazar_una_solicitud_no_cambia_el_activo():
    cliente, contenedor, _ = _crear_cliente_de_prueba()
    id_solicitud = _crear(cliente)
    contenedor.valor = _identidad("tecnico-1", "mantenimiento")

    cliente.put(f"/api/solicitudes/{id_solicitud}/estado", json={"estado_nuevo": "rechazada"})

    assert cliente.activo_estado.estado == "disponible"
