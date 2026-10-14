from dataclasses import replace
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.mantenimientos.application.ports.activo_resumen_port import (
    ActivoResumen,
    ActivoResumenPort,
)
from modules.mantenimientos.application.ports.buscador_activos_port import BuscadorActivosPort
from modules.mantenimientos.application.ports.mantenimiento_repository import (
    MantenimientoRepositoryPort,
)
from modules.mantenimientos.application.ports.resolutor_nombres_port import (
    ActivoNombre,
    NombresReferenciasMantenimiento,
    ResolutorNombresMantenimientoPort,
)
from modules.mantenimientos.application.ports.solicitud_estado_port import SolicitudEstadoPort
from modules.mantenimientos.application.ports.solicitud_verificador_port import (
    SolicitudVerificadorPort,
)
from modules.mantenimientos.application.ports.verificador_tecnico_port import (
    VerificadorTecnicoPort,
)
from modules.mantenimientos.application.services.cambiar_estado_mantenimiento import (
    CambiarEstadoMantenimientoService,
)
from modules.mantenimientos.application.services.crear_mantenimiento import (
    CrearMantenimientoService,
)
from modules.mantenimientos.application.services.eliminar_archivo_mantenimiento import (
    EliminarArchivoMantenimientoService,
)
from modules.mantenimientos.application.services.listar_mantenimientos import (
    ListarMantenimientosService,
)
from modules.mantenimientos.application.services.obtener_archivo_mantenimiento import (
    ObtenerArchivoMantenimientoService,
)
from modules.mantenimientos.application.services.obtener_mantenimiento import (
    ObtenerMantenimientoService,
)
from modules.mantenimientos.application.services.registrar_mantenimientos_masivo import (
    RegistrarMantenimientosMasivoService,
)
from modules.mantenimientos.application.services.subir_archivo_mantenimiento import (
    SubirArchivoMantenimientoService,
)
from modules.mantenimientos.application.services.verificar_alertas_mantenimiento import (
    VerificarAlertasMantenimientoService,
)
from modules.mantenimientos.domain.entities import Mantenimiento
from modules.mantenimientos.infrastructure.api.dependencies import (
    get_cambiar_estado_mantenimiento_service,
    get_crear_mantenimiento_service,
    get_eliminar_archivo_mantenimiento_service,
    get_listar_mantenimientos_service,
    get_obtener_archivo_mantenimiento_service,
    get_obtener_mantenimiento_service,
    get_registrar_mantenimientos_masivo_service,
    get_subir_archivo_mantenimiento_service,
    get_verificar_alertas_mantenimiento_service,
)
from modules.mantenimientos.infrastructure.api.routes import router
from shared.application.file_storage.ports import AlmacenArchivosPort, ArchivoAlmacenado
from shared.application.notifications.ports import NotificadorPort
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_usuario_autenticado,
)
from shared.infrastructure.api.error_handlers import register_error_handlers

_ACTIVO_ID = "a" * 24
_TECNICO_ID = "tecnico-1"
_ADMIN_ID = "admin-1"
_JPEG = b"\xff\xd8\xff" + b"0" * 20


class _RepositorioMantenimientoEnMemoria(MantenimientoRepositoryPort):
    def __init__(self):
        self._items: dict[str, Mantenimiento] = {}
        self._contador = 0

    async def guardar(self, mantenimiento: Mantenimiento) -> Mantenimiento:
        if mantenimiento.id is None:
            self._contador += 1
            mantenimiento = replace(mantenimiento, id=str(self._contador))
        self._items[mantenimiento.id] = mantenimiento
        return mantenimiento

    async def guardar_varios(self, mantenimientos):
        return [await self.guardar(m) for m in mantenimientos]

    async def obtener_por_id(self, id_mantenimiento: str):
        return self._items.get(id_mantenimiento)

    def _filtrados(self, activo_id, tecnico_responsable_id, estado, tipo, solicitud_id):
        return [
            m
            for m in self._items.values()
            if (activo_id is None or m.activo_id == activo_id)
            and (tecnico_responsable_id is None or m.tecnico_responsable_id == tecnico_responsable_id)
            and (estado is None or m.estado == estado)
            and (tipo is None or m.tipo == tipo)
            and (solicitud_id is None or m.solicitud_id == solicitud_id)
        ]

    async def listar(
        self, activo_id, tecnico_responsable_id, estado, tipo, solicitud_id, skip, limit
    ):
        return self._filtrados(activo_id, tecnico_responsable_id, estado, tipo, solicitud_id)[
            skip : skip + limit
        ]

    async def contar(self, activo_id, tecnico_responsable_id, estado, tipo, solicitud_id):
        return len(self._filtrados(activo_id, tecnico_responsable_id, estado, tipo, solicitud_id))

    async def listar_pendientes_de_alerta(self, limite_fecha):
        return [
            m
            for m in self._items.values()
            if not m.alerta_enviada
            and m.proxima_fecha_sugerida is not None
            and m.proxima_fecha_sugerida <= limite_fecha
        ]


class _ActivoResumenFalso(ActivoResumenPort):
    def __init__(self, resumen: ActivoResumen):
        self._resumen = resumen

    async def obtener_resumen(self, activo_id: str):
        if activo_id != self._resumen.id:
            return None
        return self._resumen


class _VerificadorTecnicoFalso(VerificadorTecnicoPort):
    async def tiene_rol_mantenimiento(self, usuario_id: str) -> bool:
        return usuario_id == _TECNICO_ID


class _ResolutorFalso(ResolutorNombresMantenimientoPort):
    async def resolver(self, referencias):
        return NombresReferenciasMantenimiento(
            activos={_ACTIVO_ID: ActivoNombre(nombre="Laptop Dell", numero_inventario="INV-001")},
            tecnicos={_TECNICO_ID: "Tecnico Uno"},
        )


_SOLICITUD_ID = "b" * 24


class _SolicitudVerificadorFalso(SolicitudVerificadorPort):
    async def corresponde_al_activo(self, solicitud_id: str, activo_id: str) -> bool:
        return solicitud_id == _SOLICITUD_ID and activo_id == _ACTIVO_ID


class _BuscadorActivosFalso(BuscadorActivosPort):
    async def buscar_por_codigo(self, codigos):
        existentes = {"INV-001": _ACTIVO_ID, "LAVAMANOS1": "d" * 24}

        return {codigo: existentes[codigo] for codigo in codigos if codigo in existentes}


class _SolicitudEstadoFalso(SolicitudEstadoPort):
    def __init__(self):
        self.resueltas = []

    async def marcar_resuelta(self, solicitud_id, actor) -> None:
        self.resueltas.append((solicitud_id, actor))


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


class _NotificadorFalso(NotificadorPort):
    def __init__(self):
        self.enviados = []

    async def notificar(self, destinatarios, asunto, cuerpo) -> None:
        self.enviados.append((destinatarios, asunto, cuerpo))


class _IdentidadContenedor:
    def __init__(self, identidad: IdentidadUsuarioAutenticada):
        self.valor = identidad


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

    repo = _RepositorioMantenimientoEnMemoria()
    activo_resumen = _ActivoResumenFalso(
        ActivoResumen(id=_ACTIVO_ID, responsable_id="responsable-1", area_id="area-1")
    )
    verificador_tecnico = _VerificadorTecnicoFalso()
    resolutor = _ResolutorFalso()
    solicitud_estado = _SolicitudEstadoFalso()
    solicitud_verificador = _SolicitudVerificadorFalso()
    buscador_activos = _BuscadorActivosFalso()
    almacen_archivos = _AlmacenArchivosFalso()
    notificador = _NotificadorFalso()

    app.dependency_overrides[get_crear_mantenimiento_service] = (
        lambda: CrearMantenimientoService(
            repo, activo_resumen, verificador_tecnico, solicitud_verificador, notificador
        )
    )
    app.dependency_overrides[get_registrar_mantenimientos_masivo_service] = (
        lambda: RegistrarMantenimientosMasivoService(repo, buscador_activos, verificador_tecnico)
    )
    app.dependency_overrides[get_listar_mantenimientos_service] = (
        lambda: ListarMantenimientosService(repo, resolutor)
    )
    app.dependency_overrides[get_obtener_mantenimiento_service] = (
        lambda: ObtenerMantenimientoService(repo, resolutor)
    )
    app.dependency_overrides[get_cambiar_estado_mantenimiento_service] = (
        lambda: CambiarEstadoMantenimientoService(repo, solicitud_estado)
    )
    app.dependency_overrides[get_subir_archivo_mantenimiento_service] = (
        lambda: SubirArchivoMantenimientoService(repo, almacen_archivos)
    )
    app.dependency_overrides[get_obtener_archivo_mantenimiento_service] = (
        lambda: ObtenerArchivoMantenimientoService(repo, almacen_archivos)
    )
    app.dependency_overrides[get_eliminar_archivo_mantenimiento_service] = (
        lambda: EliminarArchivoMantenimientoService(repo, almacen_archivos)
    )
    app.dependency_overrides[get_verificar_alertas_mantenimiento_service] = (
        lambda: VerificarAlertasMantenimientoService(repo, activo_resumen, notificador)
    )

    contenedor = _IdentidadContenedor(_identidad(_TECNICO_ID, "mantenimiento"))
    app.dependency_overrides[requiere_usuario_autenticado] = lambda: contenedor.valor

    cliente = TestClient(app)
    cliente.solicitud_estado = solicitud_estado
    cliente.repo = repo

    return cliente, contenedor


_MANTENIMIENTO_DE_PRUEBA = {
    "activo_id": _ACTIVO_ID,
    "tipo": "correctivo",
    "tecnico_responsable_id": _TECNICO_ID,
    "fecha": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
}


def _crear(cliente) -> str:
    respuesta = cliente.post("/api/mantenimientos", json=_MANTENIMIENTO_DE_PRUEBA)
    return respuesta.json()["data"]["id"]


def test_crear_listar_y_obtener_mantenimiento_de_punta_a_punta():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta_crear = cliente.post("/api/mantenimientos", json=_MANTENIMIENTO_DE_PRUEBA)
    assert respuesta_crear.status_code == 201
    id_mantenimiento = respuesta_crear.json()["data"]["id"]

    respuesta_obtener = cliente.get(f"/api/mantenimientos/{id_mantenimiento}")
    assert respuesta_obtener.status_code == 200
    assert respuesta_obtener.json()["data"]["estado"] == "programado"

    respuesta_listar = cliente.get("/api/mantenimientos")
    assert respuesta_listar.status_code == 200
    cuerpo = respuesta_listar.json()
    assert cuerpo["meta"] == {"total": 1, "skip": 0, "limit": 100}
    assert cuerpo["data"][0]["activo_nombre"] == "Laptop Dell"
    assert cuerpo["data"][0]["tecnico_nombre"] == "Tecnico Uno"


def test_obtener_un_mantenimiento_inexistente_retorna_404_con_mnt_001():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.get("/api/mantenimientos/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "MNT-001"


def test_crear_con_activo_inexistente_retorna_404_con_mnt_002():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post(
        "/api/mantenimientos",
        json={**_MANTENIMIENTO_DE_PRUEBA, "activo_id": "c" * 24},
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "MNT-002"


def test_crear_con_tecnico_sin_rol_de_mantenimiento_retorna_422_con_mnt_003():
    cliente, contenedor = _crear_cliente_de_prueba()
    contenedor.valor = _identidad("admin-1", "administrador_general")

    respuesta = cliente.post(
        "/api/mantenimientos",
        json={**_MANTENIMIENTO_DE_PRUEBA, "tecnico_responsable_id": "sin-rol"},
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "MNT-003"


def test_crear_sin_el_rol_de_mantenimiento_o_administrador_retorna_403():
    cliente, contenedor = _crear_cliente_de_prueba()
    contenedor.valor = _identidad("empleado-1", "empleado")

    respuesta = cliente.post("/api/mantenimientos", json=_MANTENIMIENTO_DE_PRUEBA)

    assert respuesta.status_code == 403


def test_cambiar_estado_con_transicion_invalida_retorna_422_con_mnt_004():
    cliente, _ = _crear_cliente_de_prueba()
    id_mantenimiento = _crear(cliente)

    respuesta = cliente.put(
        f"/api/mantenimientos/{id_mantenimiento}/estado", json={"estado_nuevo": "completado"}
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "MNT-004"


def test_completar_un_mantenimiento_con_solicitud_asociada_la_marca_resuelta():
    cliente, _ = _crear_cliente_de_prueba()
    id_mantenimiento = _crear(cliente)
    cliente.repo._items[id_mantenimiento] = replace(
        cliente.repo._items[id_mantenimiento], solicitud_id="sol-1"
    )
    url = f"/api/mantenimientos/{id_mantenimiento}/estado"

    assert cliente.put(url, json={"estado_nuevo": "en_proceso"}).status_code == 200
    respuesta = cliente.put(url, json={"estado_nuevo": "completado"})

    assert respuesta.status_code == 200
    assert cliente.solicitud_estado.resueltas == [("sol-1", cliente.solicitud_estado.resueltas[0][1])]


def test_subir_un_documento_y_descargarlo():
    cliente, _ = _crear_cliente_de_prueba()
    id_mantenimiento = _crear(cliente)

    respuesta_subir = cliente.post(
        f"/api/mantenimientos/{id_mantenimiento}/documentos",
        params={"nombre": "factura.jpg"},
        content=_JPEG,
    )
    assert respuesta_subir.status_code == 201
    archivo_id = respuesta_subir.json()["data"]["documentos"][0]["archivo_id"]

    respuesta_descargar = cliente.get(
        f"/api/mantenimientos/{id_mantenimiento}/archivos/{archivo_id}"
    )
    assert respuesta_descargar.status_code == 200
    assert respuesta_descargar.content == _JPEG
    assert respuesta_descargar.headers["content-type"] == "image/jpeg"


def test_subir_un_archivo_con_contenido_no_soportado_retorna_400_con_mnt_005():
    cliente, _ = _crear_cliente_de_prueba()
    id_mantenimiento = _crear(cliente)

    respuesta = cliente.post(
        f"/api/mantenimientos/{id_mantenimiento}/evidencias",
        params={"nombre": "nota.txt"},
        content=b"contenido no soportado",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "MNT-005"


def test_eliminar_un_archivo_lo_quita_del_mantenimiento():
    cliente, _ = _crear_cliente_de_prueba()
    id_mantenimiento = _crear(cliente)
    subida = cliente.post(
        f"/api/mantenimientos/{id_mantenimiento}/evidencias",
        params={"nombre": "foto.jpg"},
        content=_JPEG,
    )
    archivo_id = subida.json()["data"]["evidencias"][0]["archivo_id"]

    respuesta = cliente.delete(f"/api/mantenimientos/{id_mantenimiento}/archivos/{archivo_id}")

    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["evidencias"] == []


def test_descargar_un_archivo_que_no_existe_retorna_404_con_mnt_007():
    cliente, _ = _crear_cliente_de_prueba()
    id_mantenimiento = _crear(cliente)

    respuesta = cliente.get(f"/api/mantenimientos/{id_mantenimiento}/archivos/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "MNT-007"


def test_verificar_alertas_requiere_rol_administrador_general():
    cliente, contenedor = _crear_cliente_de_prueba()

    respuesta_tecnico = cliente.post("/api/mantenimientos/verificar-alertas")
    assert respuesta_tecnico.status_code == 403

    contenedor.valor = _identidad(_ADMIN_ID, "administrador_general")
    respuesta_admin = cliente.post("/api/mantenimientos/verificar-alertas")
    assert respuesta_admin.status_code == 200
    assert respuesta_admin.json()["data"]["notificaciones_enviadas"] == 0


# ---------------------------------------------------------------------------
# Acceso exclusivo, detalle enriquecido, carga masiva y validaciones
# ---------------------------------------------------------------------------


def test_solo_mantenimiento_y_administrador_pueden_consultar():
    cliente, contenedor = _crear_cliente_de_prueba()
    id_mantenimiento = _crear(cliente)
    subida = cliente.post(
        f"/api/mantenimientos/{id_mantenimiento}/documentos", params={"nombre": "f.jpg"}, content=_JPEG
    )
    archivo_id = subida.json()["data"]["documentos"][0]["archivo_id"]

    for identidad in (_identidad(_TECNICO_ID, "mantenimiento"), _identidad(_ADMIN_ID, "administrador_general")):
        contenedor.valor = identidad
        assert cliente.get("/api/mantenimientos").status_code == 200
        assert cliente.get(f"/api/mantenimientos/{id_mantenimiento}").status_code == 200
        assert cliente.get(f"/api/mantenimientos/{id_mantenimiento}/archivos/{archivo_id}").status_code == 200


def test_los_demas_roles_no_pueden_listar_ver_ni_descargar_archivos():
    cliente, contenedor = _crear_cliente_de_prueba()
    id_mantenimiento = _crear(cliente)
    subida = cliente.post(
        f"/api/mantenimientos/{id_mantenimiento}/documentos", params={"nombre": "f.jpg"}, content=_JPEG
    )
    archivo_id = subida.json()["data"]["documentos"][0]["archivo_id"]

    for rol in ("empleado", "tecnologia", "jefe_area", "administrativo"):
        contenedor.valor = _identidad("otro-1", rol)
        assert cliente.get("/api/mantenimientos").status_code == 403
        assert cliente.get(f"/api/mantenimientos/{id_mantenimiento}").status_code == 403
        assert cliente.get(f"/api/mantenimientos/{id_mantenimiento}/archivos/{archivo_id}").status_code == 403


def test_el_detalle_trae_nombres_creador_y_estados_permitidos():
    cliente, _ = _crear_cliente_de_prueba()
    id_mantenimiento = _crear(cliente)

    detalle = cliente.get(f"/api/mantenimientos/{id_mantenimiento}").json()["data"]

    assert detalle["activo_nombre"] == "Laptop Dell"
    assert detalle["activo_numero_inventario"] == "INV-001"
    assert detalle["tecnico_nombre"] == "Tecnico Uno"
    assert detalle["creado_por_id"] == _TECNICO_ID
    assert detalle["creado_por_nombre"] == f"Nombre {_TECNICO_ID}"
    assert detalle["fecha_creacion"]
    assert detalle["alerta_enviada"] is False
    assert detalle["estados_permitidos"] == ["en_proceso", "cancelado"]


def test_los_estados_permitidos_siguen_el_ciclo_de_vida():
    cliente, _ = _crear_cliente_de_prueba()
    id_mantenimiento = _crear(cliente)
    url = f"/api/mantenimientos/{id_mantenimiento}"

    cliente.put(f"{url}/estado", json={"estado_nuevo": "en_proceso"})
    en_proceso = cliente.get(url).json()["data"]["estados_permitidos"]
    cliente.put(f"{url}/estado", json={"estado_nuevo": "completado"})
    completado = cliente.get(url).json()["data"]["estados_permitidos"]

    assert en_proceso == ["completado", "cancelado"]
    assert completado == []


def test_crear_un_mantenimiento_locativo():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/mantenimientos", json={**_MANTENIMIENTO_DE_PRUEBA, "tipo": "locativo"})

    assert respuesta.status_code == 201
    id_mantenimiento = respuesta.json()["data"]["id"]
    assert cliente.get(f"/api/mantenimientos/{id_mantenimiento}").json()["data"]["tipo"] == "locativo"


def test_crear_con_una_solicitud_ajena_o_inexistente_retorna_422_con_mnt_008():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post(
        "/api/mantenimientos", json={**_MANTENIMIENTO_DE_PRUEBA, "solicitud_id": "e" * 24}
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "MNT-008"


def test_crear_con_la_solicitud_del_mismo_activo_la_asocia():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post(
        "/api/mantenimientos", json={**_MANTENIMIENTO_DE_PRUEBA, "solicitud_id": _SOLICITUD_ID}
    )

    assert respuesta.status_code == 201
    id_mantenimiento = respuesta.json()["data"]["id"]
    assert cliente.get(f"/api/mantenimientos/{id_mantenimiento}").json()["data"]["solicitud_id"] == _SOLICITUD_ID


def test_las_observaciones_demasiado_largas_se_rechazan():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post(
        "/api/mantenimientos", json={**_MANTENIMIENTO_DE_PRUEBA, "observaciones": "x" * 2001}
    )

    assert respuesta.status_code == 422


_MASIVO = {
    "codigos": ["inv-001", "lavamanos1"],
    "tipo": "locativo",
    "tecnico_responsable_id": _TECNICO_ID,
    "fecha": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
    "observaciones": "Cambio de empaques",
}


def test_la_carga_masiva_registra_un_mantenimiento_completado_por_codigo():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/mantenimientos/masivo", json=_MASIVO)

    assert respuesta.status_code == 200
    datos = respuesta.json()["data"]
    # Los codigos se normalizan a mayusculas, como los guarda el modulo activos.
    assert [r["codigo"] for r in datos["registrados"]] == ["INV-001", "LAVAMANOS1"]
    assert datos["no_encontrados"] == []
    listado = cliente.get("/api/mantenimientos").json()
    assert listado["meta"]["total"] == 2
    assert {m["estado"] for m in listado["data"]} == {"completado"}
    assert {m["tipo"] for m in listado["data"]} == {"locativo"}
    assert {m["observaciones"] for m in listado["data"]} == {"Cambio de empaques"}


def test_la_carga_masiva_informa_los_codigos_inexistentes():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post(
        "/api/mantenimientos/masivo", json={**_MASIVO, "codigos": ["INV-001", "no-existe"]}
    )

    datos = respuesta.json()["data"]
    assert [r["codigo"] for r in datos["registrados"]] == ["INV-001"]
    assert datos["no_encontrados"] == ["NO-EXISTE"]


def test_la_carga_masiva_con_codigos_vacios_retorna_400_con_mnt_009():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/mantenimientos/masivo", json={**_MASIVO, "codigos": ["  ", ""]})

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "MNT-009"


def test_la_carga_masiva_sin_lista_o_con_demasiados_codigos_se_rechaza():
    cliente, _ = _crear_cliente_de_prueba()

    sin_lista = cliente.post("/api/mantenimientos/masivo", json={**_MASIVO, "codigos": []})
    demasiados = cliente.post(
        "/api/mantenimientos/masivo", json={**_MASIVO, "codigos": [f"INV-{i}" for i in range(201)]}
    )
    codigo_largo = cliente.post("/api/mantenimientos/masivo", json={**_MASIVO, "codigos": ["x" * 51]})

    assert sin_lista.status_code == 422
    assert demasiados.status_code == 422
    assert codigo_largo.status_code == 422


def test_la_carga_masiva_con_tecnico_sin_rol_retorna_422_con_mnt_003():
    cliente, contenedor = _crear_cliente_de_prueba()
    contenedor.valor = _identidad("admin-1", "administrador_general")

    respuesta = cliente.post(
        "/api/mantenimientos/masivo", json={**_MASIVO, "tecnico_responsable_id": "sin-rol"}
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "MNT-003"


def test_la_carga_masiva_requiere_el_rol_de_mantenimiento_o_administrador():
    cliente, contenedor = _crear_cliente_de_prueba()
    contenedor.valor = _identidad("empleado-1", "empleado")

    assert cliente.post("/api/mantenimientos/masivo", json=_MASIVO).status_code == 403


# Elegir el tecnico es una funcion de la matriz de permisos (mantenimientos-tecnico)


def test_quien_no_puede_elegir_el_tecnico_solo_se_registra_a_si_mismo():
    cliente, _ = _crear_cliente_de_prueba()  # el usuario es el tecnico y tiene rol de mantenimiento

    assert cliente.post("/api/mantenimientos", json=_MANTENIMIENTO_DE_PRUEBA).status_code == 201


def test_quien_no_puede_elegir_el_tecnico_no_puede_asignar_a_otra_persona():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post(
        "/api/mantenimientos", json={**_MANTENIMIENTO_DE_PRUEBA, "tecnico_responsable_id": "otro-tecnico"}
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "AUTH-003"


def test_la_carga_masiva_tampoco_deja_asignar_a_otra_persona_sin_la_funcion():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.post(
        "/api/mantenimientos/masivo", json={**_MASIVO, "tecnico_responsable_id": "otro-tecnico"}
    )

    assert respuesta.status_code == 403


def test_el_administrador_si_puede_asignar_a_otro_tecnico():
    cliente, contenedor = _crear_cliente_de_prueba()
    contenedor.valor = _identidad("admin-1", "administrador_general")

    respuesta = cliente.post("/api/mantenimientos", json=_MANTENIMIENTO_DE_PRUEBA)  # tecnico = _TECNICO_ID

    assert respuesta.status_code == 201


def test_si_a_un_rol_se_le_da_la_funcion_de_elegir_tecnico_puede_asignar_a_otro(monkeypatch):
    from shared.infrastructure.security.consulta_permisos_rol_mongo import (
        ConsultaPermisosRolMongo,
        consulta_permisos_rol,
    )

    async def _con_tecnico(self, rol):
        return {"permisos": ["home-ver", "cuenta-ver", "mantenimientos-ver", "mantenimientos-gestionar", "mantenimientos-tecnico"]}

    monkeypatch.setattr(ConsultaPermisosRolMongo, "_leer_documento", _con_tecnico)
    consulta_permisos_rol.invalidar()
    cliente, _ = _crear_cliente_de_prueba()  # rol mantenimiento, ahora con la funcion

    respuesta = cliente.post(
        "/api/mantenimientos", json={**_MANTENIMIENTO_DE_PRUEBA, "tecnico_responsable_id": "sin-rol"}
    )

    assert respuesta.status_code == 422  # llega al servicio, que rechaza a quien no es tecnico (MNT-003)
    assert respuesta.json()["code"] == "MNT-003"
