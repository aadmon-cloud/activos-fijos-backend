from dataclasses import replace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.auditorias.application.ports.activos_asignados_port import (
    ActivoAsignado,
    ActivosAsignadosPort,
)
from modules.auditorias.application.ports.auditoria_repository import AuditoriaRepositoryPort
from modules.auditorias.application.ports.generador_reporte_port import GeneradorReportePort
from modules.auditorias.application.ports.historial_activo_nota_port import (
    HistorialActivoNotaPort,
)
from modules.auditorias.application.ports.usuario_auditado_port import (
    UsuarioAuditado,
    UsuarioAuditadoPort,
)
from modules.auditorias.application.services.cerrar_auditoria import CerrarAuditoriaService
from modules.auditorias.application.services.iniciar_auditoria import IniciarAuditoriaService
from modules.auditorias.application.services.listar_auditorias import ListarAuditoriasService
from modules.auditorias.application.services.obtener_auditoria import ObtenerAuditoriaService
from modules.auditorias.application.services.obtener_pdf_auditoria import (
    ObtenerPdfAuditoriaService,
)
from modules.auditorias.application.services.reenviar_notificacion_auditoria import (
    ReenviarNotificacionAuditoriaService,
)
from modules.auditorias.application.services.verificar_item_auditoria import (
    VerificarItemAuditoriaService,
)
from modules.auditorias.domain.entities import Auditoria
from modules.auditorias.infrastructure.api.dependencies import (
    get_cerrar_auditoria_service,
    get_iniciar_auditoria_service,
    get_listar_auditorias_service,
    get_obtener_auditoria_service,
    get_obtener_pdf_auditoria_service,
    get_reenviar_notificacion_auditoria_service,
    get_verificar_item_auditoria_service,
)
from modules.auditorias.infrastructure.api.routes import router
from shared.application.file_storage.ports import AlmacenArchivosPort, ArchivoAlmacenado
from shared.application.notifications.ports import NotificadorConAdjuntoPort
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_usuario_autenticado,
)
from shared.infrastructure.api.error_handlers import register_error_handlers

_USUARIO_ID = "u" * 24
_ACTIVO_ID = "a" * 24
_ADMIN_ID = "admin-1"


class _RepositorioAuditoriaEnMemoria(AuditoriaRepositoryPort):
    def __init__(self):
        self._items: dict[str, Auditoria] = {}
        self._contador = 0

    async def guardar(self, auditoria: Auditoria) -> Auditoria:
        if auditoria.id is None:
            self._contador += 1
            auditoria = replace(auditoria, id=str(self._contador))
        self._items[auditoria.id] = auditoria
        return auditoria

    async def obtener_por_id(self, id_auditoria: str):
        return self._items.get(id_auditoria)

    def _filtradas(self, usuario_auditado_id, estado, creado_por_id):
        return [
            a
            for a in self._items.values()
            if (usuario_auditado_id is None or a.usuario_auditado_id == usuario_auditado_id)
            and (estado is None or a.estado == estado)
            and (creado_por_id is None or a.creado_por.id_persona == creado_por_id)
        ]

    async def listar(self, usuario_auditado_id, estado, creado_por_id, skip, limit):
        return self._filtradas(usuario_auditado_id, estado, creado_por_id)[skip : skip + limit]

    async def contar(self, usuario_auditado_id, estado, creado_por_id):
        return len(self._filtradas(usuario_auditado_id, estado, creado_por_id))


class _ActivosAsignadosFalso(ActivosAsignadosPort):
    def __init__(self, activos: list[ActivoAsignado]):
        self._activos = activos

    async def listar_por_responsable(self, usuario_id: str):
        return self._activos if usuario_id == _USUARIO_ID else []


class _UsuarioAuditadoFalso(UsuarioAuditadoPort):
    def __init__(self, usuarios: dict[str, UsuarioAuditado]):
        self._usuarios = usuarios

    async def obtener(self, usuario_id: str):
        return self._usuarios.get(usuario_id)


class _HistorialActivoNotaFalso(HistorialActivoNotaPort):
    def __init__(self):
        self.notas = []

    async def registrar_nota(self, activo_id, nota, auditoria_id, auditor) -> None:
        self.notas.append((activo_id, nota, auditoria_id, auditor))


class _GeneradorReporteFalso(GeneradorReportePort):
    async def generar_pdf(self, auditoria, usuario) -> bytes:
        return b"%PDF-contenido-de-prueba"


class _AlmacenArchivosFalso(AlmacenArchivosPort):
    def __init__(self):
        self._items: dict[str, ArchivoAlmacenado] = {}
        self._contador = 0

    async def guardar(self, propietario_id, nombre, contenido, tipo_mime) -> str:
        self._contador += 1
        archivo_id = str(self._contador)
        self._items[archivo_id] = ArchivoAlmacenado(
            nombre=nombre, tipo_mime=tipo_mime, contenido=contenido
        )
        return archivo_id

    async def obtener(self, archivo_id: str):
        return self._items.get(archivo_id)

    async def eliminar(self, archivo_id: str) -> None:
        self._items.pop(archivo_id, None)


class _NotificadorFalso(NotificadorConAdjuntoPort):
    def __init__(self, falla: bool = False):
        self.enviados = []
        self._falla = falla

    async def enviar(self, destinatarios, asunto, cuerpo, adjuntos) -> None:
        if self._falla:
            raise RuntimeError("smtp caido")
        self.enviados.append((destinatarios, asunto, cuerpo, adjuntos))


class _IdentidadContenedor:
    def __init__(self, identidad: IdentidadUsuarioAutenticada):
        self.valor = identidad


def _identidad(id_usuario: str, rol: str) -> IdentidadUsuarioAutenticada:
    return IdentidadUsuarioAutenticada(
        id_usuario=id_usuario, email=f"{id_usuario}@example.com", nombre=f"Nombre {id_usuario}",
        rol=rol, area_id=None,
    )


def _crear_cliente_de_prueba(notificador_falla: bool = False):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    repo = _RepositorioAuditoriaEnMemoria()
    activos_asignados = _ActivosAsignadosFalso(
        [
            ActivoAsignado(
                id=_ACTIVO_ID,
                nombre="Laptop Dell",
                numero_inventario="INV-001",
                tipo="activo_fijo",
                descripcion="Dell Latitude",
                serie="SN1",
                estado_ciclo_vida="disponible",
            )
        ]
    )
    usuario_auditado = _UsuarioAuditadoFalso(
        {
            _USUARIO_ID: UsuarioAuditado(
                id=_USUARIO_ID,
                nombre_completo="Camilo Perez",
                identificacion="102425103",
                email="camilo@x.com",
                activo=True,
            ),
            _ADMIN_ID: UsuarioAuditado(
                id=_ADMIN_ID,
                nombre_completo="Admin General",
                identificacion="1",
                email="admin@x.com",
                activo=True,
            ),
        }
    )
    historial_nota = _HistorialActivoNotaFalso()
    generador_reporte = _GeneradorReporteFalso()
    almacen_archivos = _AlmacenArchivosFalso()
    notificador = _NotificadorFalso(falla=notificador_falla)

    app.dependency_overrides[get_iniciar_auditoria_service] = (
        lambda: IniciarAuditoriaService(repo, usuario_auditado, activos_asignados)
    )
    app.dependency_overrides[get_verificar_item_auditoria_service] = (
        lambda: VerificarItemAuditoriaService(repo)
    )
    app.dependency_overrides[get_cerrar_auditoria_service] = (
        lambda: CerrarAuditoriaService(
            repo, usuario_auditado, historial_nota, generador_reporte, almacen_archivos, notificador
        )
    )
    app.dependency_overrides[get_reenviar_notificacion_auditoria_service] = (
        lambda: ReenviarNotificacionAuditoriaService(
            repo, usuario_auditado, almacen_archivos, notificador
        )
    )
    app.dependency_overrides[get_obtener_auditoria_service] = (
        lambda: ObtenerAuditoriaService(repo, usuario_auditado)
    )
    app.dependency_overrides[get_listar_auditorias_service] = (
        lambda: ListarAuditoriasService(repo, usuario_auditado)
    )
    app.dependency_overrides[get_obtener_pdf_auditoria_service] = (
        lambda: ObtenerPdfAuditoriaService(repo, almacen_archivos)
    )

    contenedor = _IdentidadContenedor(_identidad(_ADMIN_ID, "administrador_general"))
    app.dependency_overrides[requiere_usuario_autenticado] = lambda: contenedor.valor

    cliente = TestClient(app)
    cliente.notificador = notificador
    cliente.historial_nota = historial_nota

    return cliente, contenedor


def _iniciar(cliente) -> str:
    return cliente.post("/api/auditorias", json={"usuario_auditado_id": _USUARIO_ID}).json()["data"]["id"]


def test_iniciar_toma_el_snapshot_y_queda_en_progreso():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/auditorias", json={"usuario_auditado_id": _USUARIO_ID})

    assert respuesta.status_code == 201
    data = respuesta.json()["data"]
    assert data["estado"] == "en_progreso"
    assert data["total"] == 1
    assert data["pendientes"] == 1
    assert data["items"][0]["activo_id"] == _ACTIVO_ID


def test_iniciar_con_usuario_inexistente_retorna_404_con_aud_001():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/auditorias", json={"usuario_auditado_id": "no-existe"})

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "AUD-001"


def test_iniciar_sin_rol_administrador_general_retorna_403():
    cliente, contenedor = _crear_cliente_de_prueba()
    contenedor.valor = _identidad("empleado-1", "empleado")

    respuesta = cliente.post("/api/auditorias", json={"usuario_auditado_id": _USUARIO_ID})

    assert respuesta.status_code == 403


def test_verificar_item_encontrado_lo_marca_y_actualiza_el_resumen():
    cliente, _ = _crear_cliente_de_prueba()
    id_auditoria = _iniciar(cliente)

    respuesta = cliente.put(
        f"/api/auditorias/{id_auditoria}/items/{_ACTIVO_ID}", json={"resultado": "encontrado"}
    )

    assert respuesta.status_code == 200
    data = respuesta.json()["data"]
    assert data["items"][0]["resultado"] == "encontrado"
    assert data["encontrados"] == 1
    assert data["pendientes"] == 0


def test_verificar_item_con_novedad_sin_observacion_retorna_422_con_aud_004():
    cliente, _ = _crear_cliente_de_prueba()
    id_auditoria = _iniciar(cliente)

    respuesta = cliente.put(
        f"/api/auditorias/{id_auditoria}/items/{_ACTIVO_ID}",
        json={"resultado": "encontrado_con_novedad"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "AUD-004"


def test_verificar_un_activo_fuera_del_snapshot_retorna_404_con_aud_003():
    cliente, _ = _crear_cliente_de_prueba()
    id_auditoria = _iniciar(cliente)

    respuesta = cliente.put(
        f"/api/auditorias/{id_auditoria}/items/{'z' * 24}", json={"resultado": "encontrado"}
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "AUD-003"


def test_cerrar_marca_pendientes_como_no_encontrados_y_notifica():
    cliente, _ = _crear_cliente_de_prueba()
    id_auditoria = _iniciar(cliente)

    respuesta = cliente.post(f"/api/auditorias/{id_auditoria}/cerrar")

    assert respuesta.status_code == 200
    data = respuesta.json()["data"]
    assert data["estado"] == "notificada"
    assert data["no_encontrados"] == 1
    assert data["pdf_archivo_id"] is not None
    assert len(cliente.notificador.enviados) == 1
    destinatarios = cliente.notificador.enviados[0][0]
    assert "camilo@x.com" in destinatarios
    assert "admin@x.com" in destinatarios
    assert len(cliente.historial_nota.notas) == 1


def test_cerrar_una_auditoria_ya_cerrada_retorna_422_con_aud_002():
    cliente, _ = _crear_cliente_de_prueba()
    id_auditoria = _iniciar(cliente)
    cliente.post(f"/api/auditorias/{id_auditoria}/cerrar")

    respuesta = cliente.post(f"/api/auditorias/{id_auditoria}/cerrar")

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "AUD-002"


def test_cerrar_con_fallo_de_correo_queda_en_error_notificacion():
    cliente, _ = _crear_cliente_de_prueba(notificador_falla=True)
    id_auditoria = _iniciar(cliente)

    respuesta = cliente.post(f"/api/auditorias/{id_auditoria}/cerrar")

    assert respuesta.status_code == 200
    data = respuesta.json()["data"]
    assert data["estado"] == "error_notificacion"
    assert data["pdf_archivo_id"] is not None


def test_verificar_o_cerrar_una_auditoria_inexistente_retorna_404_con_aud_005():
    cliente, _ = _crear_cliente_de_prueba()

    estado = cliente.put(f"/api/auditorias/no-existe/items/{_ACTIVO_ID}", json={"resultado": "encontrado"})
    cierre = cliente.post("/api/auditorias/no-existe/cerrar")

    assert estado.status_code == 404
    assert estado.json()["code"] == "AUD-005"
    assert cierre.status_code == 404
    assert cierre.json()["code"] == "AUD-005"


def test_reenviar_notificacion_tras_un_error_queda_notificada():
    cliente, _ = _crear_cliente_de_prueba(notificador_falla=True)
    id_auditoria = _iniciar(cliente)
    cliente.post(f"/api/auditorias/{id_auditoria}/cerrar")
    cliente.notificador._falla = False

    respuesta = cliente.post(f"/api/auditorias/{id_auditoria}/reenviar-notificacion")

    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["estado"] == "notificada"


def test_reenviar_notificacion_de_una_auditoria_en_progreso_retorna_422():
    cliente, _ = _crear_cliente_de_prueba()
    id_auditoria = _iniciar(cliente)

    respuesta = cliente.post(f"/api/auditorias/{id_auditoria}/reenviar-notificacion")

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "AUD-002"


def test_obtener_incluye_los_datos_del_usuario_auditado():
    cliente, _ = _crear_cliente_de_prueba()
    id_auditoria = _iniciar(cliente)

    respuesta = cliente.get(f"/api/auditorias/{id_auditoria}")

    assert respuesta.status_code == 200
    data = respuesta.json()["data"]
    assert data["usuario_nombre"] == "Camilo Perez"
    assert data["usuario_identificacion"] == "102425103"


def test_obtener_una_auditoria_inexistente_retorna_404():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.get("/api/auditorias/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "AUD-005"


def test_listar_filtra_por_usuario_auditado_y_trae_meta():
    cliente, _ = _crear_cliente_de_prueba()
    _iniciar(cliente)
    _iniciar(cliente)

    respuesta = cliente.get("/api/auditorias", params={"usuario_auditado_id": _USUARIO_ID, "limit": 1})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["meta"] == {"total": 2, "skip": 0, "limit": 1}
    assert len(cuerpo["data"]) == 1
    assert cuerpo["data"][0]["usuario_nombre"] == "Camilo Perez"


def test_listar_funciona_como_historial_del_usuario_sin_coleccion_nueva():
    cliente, _ = _crear_cliente_de_prueba()
    id_auditoria = _iniciar(cliente)
    cliente.post(f"/api/auditorias/{id_auditoria}/cerrar")

    respuesta = cliente.get("/api/auditorias", params={"usuario_auditado_id": _USUARIO_ID})

    assert respuesta.json()["meta"]["total"] == 1


def test_descargar_el_pdf_de_una_auditoria_cerrada():
    cliente, _ = _crear_cliente_de_prueba()
    id_auditoria = _iniciar(cliente)
    cliente.post(f"/api/auditorias/{id_auditoria}/cerrar")

    respuesta = cliente.get(f"/api/auditorias/{id_auditoria}/pdf")

    assert respuesta.status_code == 200
    assert respuesta.content == b"%PDF-contenido-de-prueba"
    assert respuesta.headers["content-type"] == "application/pdf"


def test_descargar_el_pdf_de_una_auditoria_en_progreso_retorna_404_con_aud_006():
    cliente, _ = _crear_cliente_de_prueba()
    id_auditoria = _iniciar(cliente)

    respuesta = cliente.get(f"/api/auditorias/{id_auditoria}/pdf")

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "AUD-006"


def test_verificar_item_con_una_observacion_demasiado_larga_se_rechaza():
    cliente, _ = _crear_cliente_de_prueba()
    id_auditoria = _iniciar(cliente)

    respuesta = cliente.put(
        f"/api/auditorias/{id_auditoria}/items/{_ACTIVO_ID}",
        json={"resultado": "encontrado_con_novedad", "observacion": "x" * 1001},
    )

    assert respuesta.status_code == 422
