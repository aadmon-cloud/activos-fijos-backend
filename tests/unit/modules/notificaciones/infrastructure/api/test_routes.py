from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.notificaciones.application.ports.notificacion_repository import (
    NotificacionRepositoryPort,
)
from modules.notificaciones.application.services.listar_notificaciones import (
    ListarNotificacionesService,
)
from modules.notificaciones.application.services.procesar_recordatorios import (
    ProcesarRecordatoriosService,
)
from modules.notificaciones.application.services.reenviar_notificacion import (
    ReenviarNotificacionService,
)
from modules.notificaciones.domain.entities import EstadoNotificacion, Notificacion
from modules.notificaciones.infrastructure.api.dependencies import (
    get_configuracion_correo,
    get_listar_notificaciones_service,
    get_procesar_recordatorios_service,
    get_reenviar_notificacion_service,
)
from modules.notificaciones.infrastructure.api.routes import router
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_usuario_autenticado,
)
from shared.infrastructure.api.error_handlers import register_error_handlers

_AHORA = datetime(2026, 1, 1, tzinfo=UTC)


class _RepositorioEnMemoria(NotificacionRepositoryPort):
    def __init__(self):
        self._items: dict[str, Notificacion] = {}

    async def guardar(self, notificacion):
        if notificacion.id is None:
            notificacion = replace(notificacion, id=str(len(self._items) + 1))
        self._items[notificacion.id] = notificacion

        return notificacion

    async def obtener_por_id(self, id_notificacion):
        return self._items.get(id_notificacion)

    def _filtradas(self, estado):
        return [n for n in self._items.values() if estado is None or n.estado == estado]

    async def listar(self, estado, skip, limit):
        return self._filtradas(estado)[skip : skip + limit]

    async def contar(self, estado):
        return len(self._filtradas(estado))


def _notificacion(id_, estado) -> Notificacion:
    return Notificacion(
        id=id_,
        destinatarios=["usuario:1"],
        correos=[],
        asunto=f"Asunto {id_}",
        cuerpo="Cuerpo",
        estado=estado,
        detalle="fallo" if estado == EstadoNotificacion.FALLIDA else None,
        intentos=1,
        creada_en=_AHORA,
        actualizada_en=_AHORA,
    )


def _identidad(rol: str) -> IdentidadUsuarioAutenticada:
    return IdentidadUsuarioAutenticada(id_usuario="1", email="a@x.com", nombre="Ana", rol=rol, area_id=None)


class _Contenedor:
    def __init__(self):
        self.valor = _identidad("administrador_general")


def _crear_cliente():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    repo = _RepositorioEnMemoria()
    resolutor = AsyncMock()
    resolutor.resolver.return_value = ["ana@x.com"]
    configuracion = MagicMock()
    configuracion.esta_configurado.return_value = True
    configuracion.remitente.return_value = "sistema@org.com"
    configuracion.url_aplicacion.return_value = None
    correo = AsyncMock()
    tarea_mantenimientos, tarea_devoluciones = AsyncMock(), AsyncMock()
    tarea_mantenimientos.ejecutar.return_value = 3
    tarea_devoluciones.ejecutar.return_value = 2
    contenedor = _Contenedor()

    app.dependency_overrides[get_listar_notificaciones_service] = lambda: ListarNotificacionesService(repo)
    app.dependency_overrides[get_reenviar_notificacion_service] = lambda: ReenviarNotificacionService(
        repo, resolutor, configuracion, correo
    )
    app.dependency_overrides[get_configuracion_correo] = lambda: configuracion
    app.dependency_overrides[get_procesar_recordatorios_service] = lambda: ProcesarRecordatoriosService(
        tarea_mantenimientos, tarea_devoluciones
    )
    app.dependency_overrides[requiere_usuario_autenticado] = lambda: contenedor.valor

    cliente = TestClient(app)
    cliente.repo = repo
    cliente.contenedor = contenedor
    cliente.configuracion = configuracion
    cliente.correo = correo

    return cliente


async def _sembrar(cliente):
    await cliente.repo.guardar(_notificacion(None, EstadoNotificacion.FALLIDA))
    await cliente.repo.guardar(_notificacion(None, EstadoNotificacion.ENVIADA))
    await cliente.repo.guardar(_notificacion(None, EstadoNotificacion.OMITIDA))


def test_el_administrador_lista_el_historial_con_total_y_filtra_por_estado():
    import asyncio

    cliente = _crear_cliente()
    asyncio.run(_sembrar(cliente))

    todas = cliente.get("/api/notificaciones").json()
    fallidas = cliente.get("/api/notificaciones", params={"estado": "fallida"}).json()

    assert todas["meta"] == {"total": 3, "skip": 0, "limit": 100}
    assert fallidas["meta"]["total"] == 1
    assert fallidas["data"][0]["estado"] == "fallida"
    assert fallidas["data"][0]["detalle"] == "fallo"


def test_el_historial_y_el_estado_del_correo_son_solo_del_administrador():
    cliente = _crear_cliente()

    for rol in ("empleado", "mantenimiento", "tecnologia", "jefe_area"):
        cliente.contenedor.valor = _identidad(rol)

        assert cliente.get("/api/notificaciones").status_code == 403
        assert cliente.get("/api/notificaciones/estado-correo").status_code == 403
        assert cliente.post("/api/notificaciones/1/reenviar").status_code == 403


def test_el_estado_del_correo_informa_si_esta_configurado_sin_exponer_secretos():
    cliente = _crear_cliente()

    cuerpo = cliente.get("/api/notificaciones/estado-correo").json()["data"]

    assert cuerpo == {"configurado": True, "remitente": "sistema@org.com"}


def test_reenviar_una_fallida_la_deja_enviada():
    import asyncio

    cliente = _crear_cliente()
    asyncio.run(_sembrar(cliente))

    respuesta = cliente.post("/api/notificaciones/1/reenviar")

    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["estado"] == "enviada"
    assert respuesta.json()["data"]["intentos"] == 2
    assert respuesta.json()["data"]["correos"] == ["ana@x.com"]
    cliente.correo.enviar.assert_awaited_once()


def test_reenviar_una_ya_enviada_responde_422_con_ntf_002():
    import asyncio

    cliente = _crear_cliente()
    asyncio.run(_sembrar(cliente))

    respuesta = cliente.post("/api/notificaciones/2/reenviar")

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "NTF-002"


def test_reenviar_una_inexistente_responde_404_con_ntf_001():
    respuesta = _crear_cliente().post("/api/notificaciones/999/reenviar")

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "NTF-001"


_PLANIFICADOR = "shared.infrastructure.api.dependencies.planificador"


def _acceso(cliente, planificador: bool):
    """Parchea el acceso de `requiere_admin_o_planificador` (que llama a la sesion directamente)."""
    from contextlib import ExitStack

    async def sesion(request, authorization):
        return cliente.contenedor.valor

    pila = ExitStack()
    pila.enter_context(patch(f"{_PLANIFICADOR}._es_planificador_autorizado", return_value=planificador))
    pila.enter_context(patch(f"{_PLANIFICADOR}.requiere_usuario_autenticado", sesion))

    return pila


def test_procesar_recordatorios_devuelve_los_conteos():
    cliente = _crear_cliente()

    with _acceso(cliente, planificador=False):
        respuesta = cliente.post("/api/notificaciones/procesar-recordatorios")

    assert respuesta.status_code == 200
    assert respuesta.json()["data"] == {
        "mantenimientos_avisados": 3,
        "devoluciones_recordadas": 2,
        "errores": [],
    }


def test_un_usuario_que_no_es_administrador_no_puede_procesar_recordatorios():
    cliente = _crear_cliente()
    cliente.contenedor.valor = _identidad("empleado")

    with _acceso(cliente, planificador=False):
        respuesta = cliente.post("/api/notificaciones/procesar-recordatorios")

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "AUTH-003"


def test_el_planificador_autorizado_puede_procesar_recordatorios_sin_ser_usuario():
    cliente = _crear_cliente()
    cliente.contenedor.valor = _identidad("empleado")

    with _acceso(cliente, planificador=True):
        respuesta = cliente.post("/api/notificaciones/procesar-recordatorios")

    assert respuesta.status_code == 200
