from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.almacen_fotos import AlmacenFotosPort, FotoAlmacenada
from modules.activos.application.ports.resolutor_nombres import (
    CondicionResuelta,
    NombresReferencias,
    ResolutorNombresPort,
)
from modules.activos.application.ports.historial_activo_repository import (
    HistorialActivoRepositoryPort,
)
from modules.activos.application.services.actualizar_activo import ActualizarActivoService
from modules.activos.application.services.cambiar_estado_activo import (
    CambiarEstadoActivoService,
)
from modules.activos.application.services.crear_activo import CrearActivoService
from modules.activos.application.services.eliminar_foto_activo import EliminarFotoActivoService
from modules.activos.application.services.listar_activos import ListarActivosService
from modules.activos.application.services.obtener_foto_activo import ObtenerFotoActivoService
from modules.activos.application.services.subir_foto_activo import SubirFotoActivoService
from modules.activos.application.services.obtener_activo import ObtenerActivoService
from modules.activos.application.services.obtener_historial_activo import (
    ObtenerHistorialActivoService,
)
from modules.activos.domain.entities import Activo, EntradaHistorialActivo
from modules.activos.infrastructure.api.dependencies import (
    get_actualizar_activo_service,
    get_cambiar_estado_activo_service,
    get_crear_activo_service,
    get_eliminar_foto_activo_service,
    get_listar_activos_service,
    get_obtener_activo_service,
    get_obtener_foto_activo_service,
    get_obtener_historial_activo_service,
    get_subir_foto_activo_service,
)
from modules.activos.infrastructure.api.routes import router
from shared.domain.entities.audit import AuditPersona
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


    async def contar(
        self,
        area_id,
        categoria_id,
        responsable_id,
        condicion_id,
        sede_id,
        lugar_id,
        estado_ciclo_vida,
        busqueda,
    ):
        valores = list(self._items.values())
        if area_id:
            valores = [a for a in valores if a.area_id == area_id]
        return len(valores)


class _AlmacenFotosEnMemoria(AlmacenFotosPort):
    def __init__(self):
        self._fotos: dict[str, FotoAlmacenada] = {}

    async def guardar(self, activo_id, contenido, tipo_mime):
        self._fotos[activo_id] = FotoAlmacenada(contenido=contenido, tipo_mime=tipo_mime)

    async def obtener(self, activo_id):
        return self._fotos.get(activo_id)

    async def eliminar(self, activo_id):
        self._fotos.pop(activo_id, None)


class _ResolutorEnMemoria(ResolutorNombresPort):
    async def resolver(self, referencias):
        return NombresReferencias(
            categorias={"c1": "Computo"},
            areas={"a1": "Tecnologia"},
            responsables={"u1": "Ana Gomez"},
            condiciones={"cond1": CondicionResuelta(nombre="Bueno", color="#4CAF50")},
            sedes={"s1": "Prado"},
            lugares={"l1": "BANO1"},
        )


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
}


def _crear_cliente_de_prueba():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    repo_activo = _RepositorioActivoEnMemoria()
    repo_historial = _RepositorioHistorialEnMemoria()
    almacen_fotos = _AlmacenFotosEnMemoria()

    app.dependency_overrides[get_crear_activo_service] = lambda: CrearActivoService(repo_activo)
    app.dependency_overrides[get_listar_activos_service] = lambda: ListarActivosService(
        repo_activo, _ResolutorEnMemoria()
    )
    app.dependency_overrides[get_obtener_activo_service] = lambda: ObtenerActivoService(
        repo_activo, _ResolutorEnMemoria()
    )
    app.dependency_overrides[get_actualizar_activo_service] = (
        lambda: ActualizarActivoService(repo_activo, repo_historial)
    )
    app.dependency_overrides[get_cambiar_estado_activo_service] = (
        lambda: CambiarEstadoActivoService(repo_activo, repo_historial)
    )
    app.dependency_overrides[get_obtener_historial_activo_service] = (
        lambda: ObtenerHistorialActivoService(repo_activo, repo_historial, _ResolutorEnMemoria())
    )

    app.dependency_overrides[get_subir_foto_activo_service] = (
        lambda: SubirFotoActivoService(repo_activo, almacen_fotos)
    )
    app.dependency_overrides[get_obtener_foto_activo_service] = (
        lambda: ObtenerFotoActivoService(almacen_fotos)
    )
    app.dependency_overrides[get_eliminar_foto_activo_service] = (
        lambda: EliminarFotoActivoService(repo_activo, almacen_fotos)
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
    assert respuesta_obtener.json()["data"]["responsable_nombre"] == "Ana Gomez"
    assert respuesta_obtener.json()["data"]["fecha_ingreso"]
    assert "valor" not in respuesta_obtener.json()["data"]
    assert "fecha_adquisicion" not in respuesta_obtener.json()["data"]

    respuesta_listar = cliente.get("/api/activos", params={"area_id": "a1"})
    assert respuesta_listar.status_code == 200
    assert len(respuesta_listar.json()["data"]) == 1


def test_listar_activos_incluye_total_y_nombres_de_las_referencias():
    cliente = _crear_cliente_de_prueba()
    cliente.post("/api/activos", json=_ACTIVO_DE_PRUEBA)
    cliente.post("/api/activos", json={**_ACTIVO_DE_PRUEBA, "numero_inventario": "INV-002"})

    respuesta = cliente.get("/api/activos", params={"limit": 1})

    cuerpo = respuesta.json()
    assert cuerpo["meta"] == {"total": 2, "skip": 0, "limit": 1}
    assert len(cuerpo["data"]) == 1
    activo = cuerpo["data"][0]
    assert activo["categoria_nombre"] == "Computo"
    assert activo["area_nombre"] == "Tecnologia"
    assert activo["responsable_nombre"] == "Ana Gomez"
    assert activo["condicion_nombre"] == "Bueno"
    assert activo["condicion_color"] == "#4CAF50"
    assert activo["sede_nombre"] == "Prado"
    assert activo["lugar_nombre"] == "BANO1"


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


def test_el_historial_devuelve_las_notas_sin_campo_ni_valores():
    # Una novedad de auditoria queda como nota; antes hacia fallar el endpoint con un 500.
    cliente = _crear_cliente_de_prueba()
    id_activo = cliente.post("/api/activos", json=_ACTIVO_DE_PRUEBA).json()["data"]["id"]
    autor = AuditPersona(id_persona="0", nombre="Admin", fecha=datetime.now(UTC))
    repo_notas = _RepositorioHistorialEnMemoria()
    repo_notas._items.append(
        EntradaHistorialActivo(
            id="9",
            activo_id=id_activo,
            tipo="nota",
            nota="Pantalla rayada",
            auditoria_id="au1",
            modificado_por=autor,
        )
    )
    activos = AsyncMock()
    activos.obtener_por_id.return_value = object()
    cliente.app.dependency_overrides[get_obtener_historial_activo_service] = (
        lambda: ObtenerHistorialActivoService(activos, repo_notas, _ResolutorEnMemoria())
    )

    respuesta = cliente.get(f"/api/activos/{id_activo}/historial")

    assert respuesta.status_code == 200
    entrada = respuesta.json()["data"][0]
    assert entrada["tipo"] == "nota"
    assert entrada["nota"] == "Pantalla rayada"
    assert entrada["campo"] is None
    assert entrada["modificado_por_nombre"] == "Admin"


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


_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
_ENCABEZADO_IMAGEN = {"Content-Type": "image/jpeg"}


def _activo_creado(cliente) -> str:
    return cliente.post("/api/activos", json=_ACTIVO_DE_PRUEBA).json()["data"]["id"]


def test_subir_y_descargar_la_foto_de_un_activo():
    cliente = _crear_cliente_de_prueba()
    id_activo = _activo_creado(cliente)

    subida = cliente.put(
        f"/api/activos/{id_activo}/foto", content=_JPEG, headers=_ENCABEZADO_IMAGEN
    )

    assert subida.status_code == 200
    descarga = cliente.get(f"/api/activos/{id_activo}/foto")
    assert descarga.status_code == 200
    assert descarga.content == _JPEG
    assert descarga.headers["content-type"] == "image/jpeg"
    assert "private" in descarga.headers["cache-control"]
    assert cliente.get(f"/api/activos/{id_activo}").json()["data"]["foto_url"] == (
        f"/api/activos/{id_activo}/foto"
    )


def test_el_tipo_lo_decide_el_contenido_no_el_content_type_declarado():
    cliente = _crear_cliente_de_prueba()
    id_activo = _activo_creado(cliente)

    respuesta = cliente.put(
        f"/api/activos/{id_activo}/foto",
        content=b"<svg onload='alert(1)'/>",
        headers={"Content-Type": "image/png"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "ACT-006"
    assert cliente.get(f"/api/activos/{id_activo}/foto").status_code == 404


def test_una_foto_demasiado_grande_se_rechaza_con_act_007():
    cliente = _crear_cliente_de_prueba()
    id_activo = _activo_creado(cliente)
    grande = b"\xff\xd8\xff" + b"\x00" * (5 * 1024 * 1024)

    respuesta = cliente.put(
        f"/api/activos/{id_activo}/foto", content=grande, headers=_ENCABEZADO_IMAGEN
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "ACT-007"


def test_subir_foto_a_un_activo_inexistente_retorna_404_con_act_002():
    cliente = _crear_cliente_de_prueba()

    respuesta = cliente.put("/api/activos/999/foto", content=_JPEG, headers=_ENCABEZADO_IMAGEN)

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "ACT-002"


def test_descargar_la_foto_de_un_activo_sin_foto_retorna_404_con_act_008():
    cliente = _crear_cliente_de_prueba()
    id_activo = _activo_creado(cliente)

    respuesta = cliente.get(f"/api/activos/{id_activo}/foto")

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "ACT-008"


def test_reemplazar_la_foto_deja_la_ultima():
    cliente = _crear_cliente_de_prueba()
    id_activo = _activo_creado(cliente)
    nueva = b"\x89PNG\r\n\x1a\n" + b"\x01" * 32

    cliente.put(f"/api/activos/{id_activo}/foto", content=_JPEG, headers=_ENCABEZADO_IMAGEN)
    cliente.put(f"/api/activos/{id_activo}/foto", content=nueva, headers={"Content-Type": "image/png"})

    descarga = cliente.get(f"/api/activos/{id_activo}/foto")
    assert descarga.content == nueva
    assert descarga.headers["content-type"] == "image/png"


def test_eliminar_la_foto_limpia_el_activo():
    cliente = _crear_cliente_de_prueba()
    id_activo = _activo_creado(cliente)
    cliente.put(f"/api/activos/{id_activo}/foto", content=_JPEG, headers=_ENCABEZADO_IMAGEN)

    respuesta = cliente.delete(f"/api/activos/{id_activo}/foto")

    assert respuesta.status_code == 200
    assert cliente.get(f"/api/activos/{id_activo}/foto").status_code == 404
    assert cliente.get(f"/api/activos/{id_activo}").json()["data"]["foto_url"] is None
