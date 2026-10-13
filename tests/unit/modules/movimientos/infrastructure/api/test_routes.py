from dataclasses import replace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.movimientos.application.ports.activo_movimiento_port import (
    ActivoMovimientoPort,
    ActivoResumenMovimiento,
)
from modules.movimientos.application.ports.generador_comprobante_port import (
    GeneradorComprobantePort,
)
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.ports.resolutor_nombres_port import (
    ActivoNombreMovimiento,
    NombresReferenciasMovimiento,
    ResolutorNombresMovimientoPort,
)
from modules.movimientos.application.ports.verificador_usuario_port import VerificadorUsuarioPort
from modules.movimientos.application.services.aprobar_movimiento import AprobarMovimientoService
from modules.movimientos.application.services.confirmar_devolucion_movimiento import (
    ConfirmarDevolucionMovimientoService,
)
from modules.movimientos.application.services.confirmar_salida_movimiento import (
    ConfirmarSalidaMovimientoService,
)
from modules.movimientos.application.services.ejecutar_baja_movimiento import (
    EjecutarBajaMovimientoService,
)
from modules.movimientos.application.services.listar_movimientos import ListarMovimientosService
from modules.movimientos.application.services.obtener_comprobante_movimiento import (
    ObtenerComprobanteMovimientoService,
)
from modules.movimientos.application.services.obtener_movimiento import ObtenerMovimientoService
from modules.movimientos.application.services.rechazar_movimiento import RechazarMovimientoService
from modules.movimientos.application.services.solicitar_devolucion_movimiento import (
    SolicitarDevolucionMovimientoService,
)
from modules.movimientos.application.services.solicitar_movimiento import (
    SolicitarMovimientoService,
)
from modules.movimientos.domain.entities import (
    ESTADOS_ITEM_ACTIVOS,
    EstadoItemMovimiento,
    Movimiento,
)
from modules.movimientos.infrastructure.api.dependencies import (
    get_aprobar_movimiento_service,
    get_confirmar_devolucion_movimiento_service,
    get_confirmar_salida_movimiento_service,
    get_ejecutar_baja_movimiento_service,
    get_listar_movimientos_service,
    get_obtener_comprobante_movimiento_service,
    get_obtener_movimiento_service,
    get_rechazar_movimiento_service,
    get_solicitar_devolucion_movimiento_service,
    get_solicitar_movimiento_service,
)
from modules.movimientos.infrastructure.api.routes import router
from shared.application.file_storage.ports import AlmacenArchivosPort, ArchivoAlmacenado
from shared.application.notifications.ports import NotificadorPort
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_usuario_autenticado,
)
from shared.infrastructure.api.error_handlers import register_error_handlers

# Usuarios
ADMIN = "admin-1"
ANA = "ana"  # responsable de A1 y A2
LUIS = "luis"  # responsable de A3
SOLICITANTE = "solicitante"
EXTRANO = "extrano"

# Activos
A1, A2, A3 = "a1", "a2", "a3"


class _RepositorioMovimientoEnMemoria(MovimientoRepositoryPort):
    def __init__(self):
        self._items: dict[str, Movimiento] = {}
        self._contador = 0

    async def guardar(self, movimiento: Movimiento) -> Movimiento:
        if movimiento.id is None:
            self._contador += 1
            movimiento = replace(movimiento, id=str(self._contador))
        self._items[movimiento.id] = movimiento
        return movimiento

    async def obtener_por_id(self, id_movimiento: str):
        return self._items.get(id_movimiento)

    async def activos_ocupados(self, activo_ids):
        return {
            item.activo_id
            for m in self._items.values()
            for item in m.items
            if item.estado in ESTADOS_ITEM_ACTIVOS and item.activo_id in activo_ids
        }

    async def listar_devoluciones_por_recordar(self, limite_fecha):
        return [
            m
            for m in self._items.values()
            if m.estado.value == "en_curso"
            and m.fecha_retorno_estimada is not None
            and m.fecha_retorno_estimada <= limite_fecha
            and not m.recordatorio_devolucion_enviado
        ]

    @staticmethod
    def _visible(m, visible_para):
        if visible_para is None:
            return True
        actor = visible_para.actor_id

        return (
            m.creado_por.id_persona == actor
            or m.usuario_destino_id == actor
            or any(i.responsable_original_id == actor or i.activo_id in visible_para.activo_ids for i in m.items)
        )

    @staticmethod
    def _para_mi(m, para_mi):
        if para_mi is None:
            return True
        actor = para_mi.actor_id
        esperan_admin = {EstadoItemMovimiento.PENDIENTE_ADMIN, EstadoItemMovimiento.DEVOLUCION_SOLICITADA}

        return (
            m.usuario_destino_id == actor
            or any(i.responsable_original_id == actor or i.activo_id in para_mi.activo_ids for i in m.items)
            or (para_mi.es_administrador and any(i.estado in esperan_admin for i in m.items))
        )

    def _filtrados(self, tipo, estado, activo_id, usuario_destino_id, creado_por_id, visible_para, para_mi):
        return [
            m
            for m in reversed(list(self._items.values()))
            if self._visible(m, visible_para)
            and self._para_mi(m, para_mi)
            and (tipo is None or m.tipo == tipo)
            and (estado is None or m.estado == estado)
            and (activo_id is None or activo_id in m.activo_ids)
            and (usuario_destino_id is None or m.usuario_destino_id == usuario_destino_id)
            and (creado_por_id is None or m.creado_por.id_persona == creado_por_id)
        ]

    async def listar(self, tipo, estado, activo_id, usuario_destino_id, creado_por_id, visible_para, para_mi, skip, limit):
        return self._filtrados(tipo, estado, activo_id, usuario_destino_id, creado_por_id, visible_para, para_mi)[
            skip : skip + limit
        ]

    async def contar(self, tipo, estado, activo_id, usuario_destino_id, creado_por_id, visible_para, para_mi):
        return len(self._filtrados(tipo, estado, activo_id, usuario_destino_id, creado_por_id, visible_para, para_mi))


class _ActivosFalsos(ActivoMovimientoPort):
    """Tres activos: A1 y A2 de Ana, A3 de Luis; todos disponibles."""

    def __init__(self):
        self.activos = {
            A1: {"responsable": ANA, "estado": "disponible", "nombre": "Laptop", "inventario": "INV-1"},
            A2: {"responsable": ANA, "estado": "disponible", "nombre": "Proyector", "inventario": "INV-2"},
            A3: {"responsable": LUIS, "estado": "disponible", "nombre": "Pantalla", "inventario": "INV-3"},
        }
        self.notas: list[tuple[str, str]] = []

    def _resumen(self, activo_id):
        datos = self.activos[activo_id]

        return ActivoResumenMovimiento(
            id=activo_id,
            responsable_id=datos["responsable"],
            estado_ciclo_vida=datos["estado"],
            nombre=datos["nombre"],
            numero_inventario=datos["inventario"],
        )

    async def obtener_resumen(self, activo_id):
        return self._resumen(activo_id) if activo_id in self.activos else None

    async def obtener_resumenes(self, activo_ids):
        return {a: self._resumen(a) for a in activo_ids if a in self.activos}

    async def listar_ids_por_responsable(self, responsable_id):
        return [a for a, d in self.activos.items() if d["responsable"] == responsable_id]

    async def cambiar_responsable(self, activo_id, responsable_nuevo_id, actor_id, actor_nombre):
        self.activos[activo_id]["responsable"] = responsable_nuevo_id
        return True

    async def cambiar_estado(self, activo_id, estado_nuevo, actor_id, actor_nombre):
        self.activos[activo_id]["estado"] = estado_nuevo
        return True

    async def registrar_nota(self, activo_id, nota, movimiento_id, actor_id, actor_nombre):
        self.notas.append((activo_id, nota))


class _VerificadorUsuarioFalso(VerificadorUsuarioPort):
    async def existe(self, usuario_id: str) -> bool:
        return usuario_id in {ADMIN, ANA, LUIS, SOLICITANTE, EXTRANO}


class _ResolutorFalso(ResolutorNombresMovimientoPort):
    def __init__(self, activos: _ActivosFalsos):
        self._activos = activos

    async def resolver(self, referencias):
        return NombresReferenciasMovimiento(
            activos={
                a: ActivoNombreMovimiento(d["nombre"], d["inventario"], responsable_id=d["responsable"])
                for a, d in self._activos.activos.items()
                if a in referencias.activo_ids
            },
            usuarios={u: f"Nombre {u}" for u in referencias.usuario_ids},
        )


class _GeneradorComprobanteFalso(GeneradorComprobantePort):
    async def generar_pdf(self, movimiento, activos, usuario_destino_nombre) -> bytes:
        return ("%PDF-comprobante:" + ",".join(activos)).encode()


class _AlmacenArchivosFalso(AlmacenArchivosPort):
    def __init__(self):
        self._items: dict[str, ArchivoAlmacenado] = {}
        self._contador = 0

    async def guardar(self, propietario_id, nombre, contenido, tipo_mime) -> str:
        self._contador += 1
        archivo_id = str(self._contador)
        self._items[archivo_id] = ArchivoAlmacenado(nombre=nombre, tipo_mime=tipo_mime, contenido=contenido)
        return archivo_id

    async def obtener(self, archivo_id: str):
        return self._items.get(archivo_id)

    async def eliminar(self, archivo_id: str) -> None:
        self._items.pop(archivo_id, None)


class _NotificadorFalso(NotificadorPort):
    def __init__(self):
        self.enviados: list[tuple[list[str], str, str]] = []

    async def notificar(self, destinatarios, asunto, cuerpo) -> None:
        self.enviados.append((destinatarios, asunto, cuerpo))


def _identidad(id_usuario: str) -> IdentidadUsuarioAutenticada:
    rol = "administrador_general" if id_usuario == ADMIN else "empleado"

    return IdentidadUsuarioAutenticada(
        id_usuario=id_usuario, email=f"{id_usuario}@example.com", nombre=f"Nombre {id_usuario}", rol=rol, area_id=None
    )


class _Cliente:
    """Cliente de prueba que actua como el usuario indicado en cada llamada."""

    def __init__(self):
        app = FastAPI()
        register_error_handlers(app)
        app.include_router(router)
        self.repo = _RepositorioMovimientoEnMemoria()
        self.activos = _ActivosFalsos()
        self.notificador = _NotificadorFalso()
        resolutor = _ResolutorFalso(self.activos)
        almacen = _AlmacenArchivosFalso()
        repo, activos, notificador = self.repo, self.activos, self.notificador

        sobrescribir = app.dependency_overrides
        sobrescribir[get_solicitar_movimiento_service] = lambda: SolicitarMovimientoService(
            repo, activos, _VerificadorUsuarioFalso(), notificador
        )
        sobrescribir[get_aprobar_movimiento_service] = lambda: AprobarMovimientoService(repo, activos, notificador)
        sobrescribir[get_rechazar_movimiento_service] = lambda: RechazarMovimientoService(repo, activos, notificador)
        sobrescribir[get_confirmar_salida_movimiento_service] = lambda: ConfirmarSalidaMovimientoService(
            repo, activos, resolutor, _GeneradorComprobanteFalso(), almacen, notificador
        )
        sobrescribir[get_solicitar_devolucion_movimiento_service] = lambda: SolicitarDevolucionMovimientoService(
            repo, activos, notificador
        )
        sobrescribir[get_confirmar_devolucion_movimiento_service] = lambda: ConfirmarDevolucionMovimientoService(
            repo, activos, notificador
        )
        sobrescribir[get_ejecutar_baja_movimiento_service] = lambda: EjecutarBajaMovimientoService(
            repo, activos, notificador
        )
        sobrescribir[get_obtener_movimiento_service] = lambda: ObtenerMovimientoService(repo, resolutor, activos)
        sobrescribir[get_listar_movimientos_service] = lambda: ListarMovimientosService(repo, resolutor, activos)
        sobrescribir[get_obtener_comprobante_movimiento_service] = lambda: ObtenerComprobanteMovimientoService(
            repo, almacen, activos
        )

        self._actual = SOLICITANTE
        sobrescribir[requiere_usuario_autenticado] = lambda: _identidad(self._actual)
        self._http = TestClient(app)

    def como(self, usuario: str) -> "_Cliente":
        self._actual = usuario

        return self

    def get(self, *args, **kwargs):
        return self._http.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self._http.post(*args, **kwargs)


def _solicitar(cliente, usuario=SOLICITANTE, **cuerpo) -> str:
    valores = {
        "tipo": "prestamo",
        "sentido": "solicitar",
        "activo_ids": [A1],
        "descripcion": "Los necesito",
    }
    valores.update(cuerpo)
    respuesta = cliente.como(usuario).post("/api/movimientos", json=valores)
    assert respuesta.status_code == 201, respuesta.text

    return respuesta.json()["data"]["id"]


def _estados_items(respuesta) -> dict[str, str]:
    return {i["activo_id"]: i["estado"] for i in respuesta.json()["data"]["items"]}


# --- solicitar ---


def test_solicitar_un_prestamo_con_varios_activos_de_distintos_responsables():
    cliente = _Cliente()

    respuesta = cliente.post(
        "/api/movimientos",
        json={"tipo": "prestamo", "sentido": "solicitar", "activo_ids": [A1, A3], "descripcion": "Para la reunion"},
    )

    assert respuesta.status_code == 201
    datos = respuesta.json()["data"]
    assert datos["estado"] == "solicitado"
    assert datos["usuario_destino_id"] == SOLICITANTE
    assert [i["responsable_original_id"] for i in datos["items"]] == [ANA, LUIS]
    assert [i["estado"] for i in datos["items"]] == ["pendiente_responsable"] * 2


def test_solicitar_baja_sin_rol_admin_retorna_403_con_mov_010():
    cliente = _Cliente()

    respuesta = cliente.post(
        "/api/movimientos", json={"tipo": "baja", "activo_ids": [A1], "descripcion": "Esta dañado"}
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "MOV-010"


def test_un_empleado_no_presta_activos_de_otro_mov_019():
    cliente = _Cliente()

    respuesta = cliente.post(
        "/api/movimientos",
        json={"tipo": "prestamo", "sentido": "prestar", "activo_ids": [A1], "usuario_destino_id": LUIS, "descripcion": "x"},
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "MOV-019"


def test_un_empleado_no_elige_otro_destinatario_mov_020():
    cliente = _Cliente()

    respuesta = cliente.post(
        "/api/movimientos",
        json={"tipo": "prestamo", "sentido": "solicitar", "activo_ids": [A1], "usuario_destino_id": LUIS, "descripcion": "x"},
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "MOV-020"


def test_solicitar_un_activo_que_ya_esta_en_otro_movimiento_retorna_409_con_mov_004():
    cliente = _Cliente()
    _solicitar(cliente)

    respuesta = cliente.post(
        "/api/movimientos",
        json={"tipo": "prestamo", "sentido": "solicitar", "activo_ids": [A1, A2], "descripcion": "x"},
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "MOV-004"


def test_solicitar_con_usuario_destino_inexistente_retorna_404_con_mov_002():
    cliente = _Cliente().como(ANA)

    respuesta = cliente.post(
        "/api/movimientos",
        json={"tipo": "prestamo", "sentido": "prestar", "activo_ids": [A1], "usuario_destino_id": "nadie", "descripcion": "x"},
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "MOV-002"


def test_validaciones_de_la_solicitud():
    cliente = _Cliente()
    base = {"tipo": "prestamo", "sentido": "solicitar", "activo_ids": [A1], "descripcion": "x"}

    casos = [
        ({**base, "descripcion": "  "}, "MOV-012"),
        ({**base, "activo_ids": []}, "MOV-016"),
        ({**base, "sentido": None}, "MOV-018"),
        ({**base, "tipo": "salida_evento", "evento_nombre": " "}, "MOV-014"),
        (
            {**base, "fecha_salida_estimada": "2026-01-10T00:00:00Z", "fecha_retorno_estimada": "2026-01-01T00:00:00Z"},
            "MOV-015",
        ),
    ]
    for cuerpo, codigo in casos:
        respuesta = cliente.post("/api/movimientos", json=cuerpo)
        assert respuesta.status_code == 400, (codigo, respuesta.text)
        assert respuesta.json()["code"] == codigo


def test_un_cuerpo_con_demasiados_activos_se_rechaza():
    cliente = _Cliente()

    respuesta = cliente.post(
        "/api/movimientos",
        json={"tipo": "prestamo", "sentido": "solicitar", "activo_ids": [f"a{n}" for n in range(500)], "descripcion": "x"},
    )

    assert respuesta.status_code == 422


# --- flujo con dos aprobaciones ---


def test_flujo_completo_cada_responsable_aprueba_administracion_elige_y_se_devuelve_con_novedad():
    cliente = _Cliente()
    id_mov = _solicitar(cliente, activo_ids=[A1, A3])

    # Ana aprueba el suyo: el movimiento sigue esperando a Luis.
    respuesta = cliente.como(ANA).post(f"/api/movimientos/{id_mov}/aprobar")
    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["estado"] == "solicitado"
    assert _estados_items(respuesta) == {A1: "pendiente_admin", A3: "pendiente_responsable"}

    # Luis aprueba el suyo: ahora espera a administracion.
    respuesta = cliente.como(LUIS).post(f"/api/movimientos/{id_mov}/aprobar")
    assert respuesta.json()["data"]["estado"] == "aprobado_responsable"

    # Administracion elige solo uno de los dos.
    respuesta = cliente.como(ADMIN).post(
        f"/api/movimientos/{id_mov}/confirmar-salida", json={"activo_ids": [A1], "motivo_no_incluidos": "Solo hay uno"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["estado"] == "en_curso"
    assert _estados_items(respuesta) == {A1: "en_curso", A3: "rechazado"}
    assert cliente.activos.activos[A1]["estado"] == "prestado"
    assert cliente.activos.activos[A1]["responsable"] == SOLICITANTE
    assert cliente.activos.activos[A3]["estado"] == "disponible"

    # Quien lo tiene pide devolverlo.
    respuesta = cliente.como(SOLICITANTE).post(f"/api/movimientos/{id_mov}/solicitar-devolucion")
    assert respuesta.status_code == 200
    assert _estados_items(respuesta)[A1] == "devolucion_solicitada"

    # Administracion lo recibe con una novedad.
    respuesta = cliente.como(ADMIN).post(
        f"/api/movimientos/{id_mov}/confirmar-devolucion",
        json={"recibos": [{"activo_id": A1, "con_novedad": True, "observacion": "Pantalla rayada"}]},
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()["data"]
    assert datos["estado"] == "devuelto"
    assert datos["items"][0]["novedad_devolucion"] == "Pantalla rayada"
    assert cliente.activos.activos[A1]["estado"] == "disponible"
    assert cliente.activos.activos[A1]["responsable"] == ANA
    assert [a for a, _ in cliente.activos.notas] == [A1]


def test_prestar_un_activo_propio_solo_espera_a_administracion():
    cliente = _Cliente()
    id_mov = _solicitar(cliente, usuario=ANA, sentido="prestar", usuario_destino_id=SOLICITANTE)

    detalle = cliente.como(ADMIN).get(f"/api/movimientos/{id_mov}")

    assert detalle.json()["data"]["estado"] == "aprobado_responsable"
    assert _estados_items(detalle) == {A1: "pendiente_admin"}

    cliente.post(f"/api/movimientos/{id_mov}/confirmar-salida")
    assert cliente.activos.activos[A1]["responsable"] == SOLICITANTE


def test_solo_administracion_confirma_la_salida_y_la_devolucion():
    cliente = _Cliente()
    id_mov = _solicitar(cliente)
    cliente.como(ANA).post(f"/api/movimientos/{id_mov}/aprobar")

    assert cliente.como(ANA).post(f"/api/movimientos/{id_mov}/confirmar-salida").status_code == 403
    assert cliente.como(SOLICITANTE).post(f"/api/movimientos/{id_mov}/confirmar-devolucion").status_code == 403


def test_un_responsable_no_aprueba_los_activos_de_otro_mov_007():
    cliente = _Cliente()
    id_mov = _solicitar(cliente, activo_ids=[A1, A3])

    respuesta = cliente.como(ANA).post(f"/api/movimientos/{id_mov}/aprobar", json={"activo_ids": [A3]})

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "MOV-007"


def test_aprobar_solo_algunos_de_sus_activos():
    cliente = _Cliente()
    id_mov = _solicitar(cliente, activo_ids=[A1, A2])

    respuesta = cliente.como(ANA).post(f"/api/movimientos/{id_mov}/aprobar", json={"activo_ids": [A2]})

    assert _estados_items(respuesta) == {A1: "pendiente_responsable", A2: "pendiente_admin"}


def test_rechazar_requiere_motivo_y_lo_guarda_por_activo():
    cliente = _Cliente()
    id_mov = _solicitar(cliente, activo_ids=[A1, A3])

    sin_motivo = cliente.como(ANA).post(f"/api/movimientos/{id_mov}/rechazar", json={"motivo_rechazo": "   "})
    assert sin_motivo.status_code == 400
    assert sin_motivo.json()["code"] == "MOV-009"

    respuesta = cliente.post(f"/api/movimientos/{id_mov}/rechazar", json={"motivo_rechazo": "Lo uso yo"})
    assert respuesta.status_code == 200
    item = respuesta.json()["data"]["items"][0]
    assert item["estado"] == "rechazado"
    assert item["motivo_rechazo"] == "Lo uso yo"
    assert item["etapa_rechazo"] == "responsable"


def test_la_novedad_exige_describirla_mov_023():
    cliente = _Cliente()
    id_mov = _solicitar(cliente)
    cliente.como(ANA).post(f"/api/movimientos/{id_mov}/aprobar")
    cliente.como(ADMIN).post(f"/api/movimientos/{id_mov}/confirmar-salida")

    respuesta = cliente.post(
        f"/api/movimientos/{id_mov}/confirmar-devolucion",
        json={"recibos": [{"activo_id": A1, "con_novedad": True, "observacion": ""}]},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "MOV-023"


def test_administracion_recibe_sin_cuerpo_todo_lo_que_esta_fuera():
    cliente = _Cliente()
    id_mov = _solicitar(cliente, activo_ids=[A1, A2])
    cliente.como(ANA).post(f"/api/movimientos/{id_mov}/aprobar")
    cliente.como(ADMIN).post(f"/api/movimientos/{id_mov}/confirmar-salida")

    respuesta = cliente.post(f"/api/movimientos/{id_mov}/confirmar-devolucion")

    assert respuesta.json()["data"]["estado"] == "devuelto"
    assert {i["estado"] for i in respuesta.json()["data"]["items"]} == {"devuelto"}


# --- salida a evento y comprobante ---


def test_la_salida_a_evento_genera_el_comprobante_y_lo_descarga_quien_puede_verla():
    cliente = _Cliente()
    id_mov = _solicitar(cliente, tipo="salida_evento", sentido=None, activo_ids=[A1, A2], evento_nombre="Feria")
    cliente.como(ANA).post(f"/api/movimientos/{id_mov}/aprobar")

    sin_generar = cliente.como(SOLICITANTE).get(f"/api/movimientos/{id_mov}/comprobante")
    assert sin_generar.status_code == 404
    assert sin_generar.json()["code"] == "MOV-008"

    cliente.como(ADMIN).post(f"/api/movimientos/{id_mov}/confirmar-salida")

    descarga = cliente.como(SOLICITANTE).get(f"/api/movimientos/{id_mov}/comprobante")
    assert descarga.status_code == 200
    assert descarga.content.startswith(b"%PDF-comprobante:")
    assert b"INV-1" in descarga.content and b"INV-2" in descarga.content
    assert cliente.como(EXTRANO).get(f"/api/movimientos/{id_mov}/comprobante").status_code == 404


# --- baja ---


def test_flujo_completo_de_baja():
    cliente = _Cliente()
    id_mov = _solicitar(cliente, usuario=ADMIN, tipo="baja", sentido=None, descripcion="Obsoleto")

    aprobada = cliente.post(f"/api/movimientos/{id_mov}/aprobar")
    assert aprobada.json()["data"]["estado"] == "aprobado"

    ejecutada = cliente.post(f"/api/movimientos/{id_mov}/ejecutar-baja")
    assert ejecutada.json()["data"]["estado"] == "ejecutado"
    assert cliente.activos.activos[A1]["estado"] == "dado_de_baja"


# --- consultas: visibilidad, "para mi" y acciones permitidas ---


def test_un_usuario_sin_relacion_no_ve_el_movimiento_ni_puede_actuar_sobre_el():
    cliente = _Cliente()
    id_mov = _solicitar(cliente)

    assert cliente.como(EXTRANO).get(f"/api/movimientos/{id_mov}").status_code == 404
    assert cliente.get("/api/movimientos").json()["data"] == []
    assert cliente.post(f"/api/movimientos/{id_mov}/aprobar").status_code == 404
    assert cliente.post(f"/api/movimientos/{id_mov}/rechazar", json={"motivo_rechazo": "x"}).status_code == 404
    assert cliente.post(f"/api/movimientos/{id_mov}/solicitar-devolucion").status_code == 404


def test_un_movimiento_inexistente_retorna_404_con_mov_005():
    cliente = _Cliente()

    respuesta = cliente.get("/api/movimientos/999")

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "MOV-005"


def test_el_detalle_incluye_nombres_y_acciones_por_activo():
    cliente = _Cliente()
    id_mov = _solicitar(cliente, activo_ids=[A1, A3])

    datos = cliente.como(ANA).get(f"/api/movimientos/{id_mov}").json()["data"]

    assert datos["usuario_destino_nombre"] == f"Nombre {SOLICITANTE}"
    assert [i["activo_nombre"] for i in datos["items"]] == ["Laptop", "Pantalla"]
    assert datos["items"][0]["responsable_original_nombre"] == f"Nombre {ANA}"
    assert datos["items"][0]["acciones_permitidas"] == ["aprobar", "rechazar"]
    assert datos["items"][1]["acciones_permitidas"] == []
    assert datos["acciones_permitidas"] == ["aprobar", "rechazar"]


def test_las_acciones_cambian_con_cada_etapa():
    cliente = _Cliente()
    id_mov = _solicitar(cliente)

    def acciones(usuario):
        return cliente.como(usuario).get(f"/api/movimientos/{id_mov}").json()["data"]["acciones_permitidas"]

    assert acciones(ANA) == ["aprobar", "rechazar"]
    assert acciones(ADMIN) == [] and acciones(SOLICITANTE) == []

    cliente.como(ANA).post(f"/api/movimientos/{id_mov}/aprobar")
    assert acciones(ANA) == []
    assert acciones(ADMIN) == ["confirmar_salida", "rechazar"]

    cliente.como(ADMIN).post(f"/api/movimientos/{id_mov}/confirmar-salida")
    assert acciones(SOLICITANTE) == ["solicitar_devolucion"]
    assert acciones(ADMIN) == ["confirmar_devolucion"]
    assert acciones(ANA) == []


def test_para_mi_incluye_lo_que_le_concierne_como_responsable_y_como_destinatario():
    cliente = _Cliente()
    id_mov = _solicitar(cliente, activo_ids=[A1, A3])

    def para_mi(usuario):
        respuesta = cliente.como(usuario).get("/api/movimientos", params={"para_mi": "true"})
        return [m["id"] for m in respuesta.json()["data"]]

    # Responsables de los activos y destinatario: si.
    assert para_mi(ANA) == [id_mov]
    assert para_mi(LUIS) == [id_mov]
    assert para_mi(SOLICITANTE) == [id_mov]
    # Ajeno: no. Administrador: no tiene nada pendiente todavia.
    assert para_mi(EXTRANO) == []
    assert para_mi(ADMIN) == []


def test_para_mi_del_administrador_incluye_lo_que_espera_su_accion_y_sus_propios_activos():
    cliente = _Cliente()
    cliente.activos.activos[A2]["responsable"] = ADMIN
    id_mov = _solicitar(cliente, activo_ids=[A1])
    otro = _solicitar(cliente, activo_ids=[A2])

    def para_mi_admin():
        respuesta = cliente.como(ADMIN).get("/api/movimientos", params={"para_mi": "true"})
        return {m["id"] for m in respuesta.json()["data"]}

    # El de A2 le concierne al administrador como responsable de ese activo; el de A1 todavia no.
    assert para_mi_admin() == {otro}

    cliente.como(ANA).post(f"/api/movimientos/{id_mov}/aprobar")
    assert para_mi_admin() == {id_mov, otro}


def test_el_listado_filtra_y_da_el_total():
    cliente = _Cliente()
    _solicitar(cliente, activo_ids=[A1])
    _solicitar(cliente, activo_ids=[A3])

    respuesta = cliente.como(ADMIN).get("/api/movimientos", params={"activo_id": A3, "limit": 10})

    cuerpo = respuesta.json()
    assert cuerpo["meta"] == {"total": 1, "skip": 0, "limit": 10}
    assert cuerpo["data"][0]["items"][0]["activo_id"] == A3


def test_el_listado_informa_las_acciones_permitidas():
    cliente = _Cliente()
    _solicitar(cliente)

    datos = cliente.como(ANA).get("/api/movimientos").json()["data"]

    assert datos[0]["acciones_permitidas"] == ["aprobar", "rechazar"]


# --- avisos ---


def test_cada_etapa_avisa_a_quien_corresponde():
    cliente = _Cliente()
    id_mov = _solicitar(cliente, activo_ids=[A1, A3])
    # 1) solicitud: a los dos responsables
    assert cliente.notificador.enviados[-1][0] == [f"usuario:{ANA}", f"usuario:{LUIS}"]

    cliente.como(ANA).post(f"/api/movimientos/{id_mov}/aprobar")
    cliente.como(LUIS).post(f"/api/movimientos/{id_mov}/aprobar")
    # 3) cuando ya aprobaron todos: a administracion y a quien lo pidio
    assert cliente.notificador.enviados[-1][0] == ["rol:administrador_general", f"usuario:{SOLICITANTE}"]

    cliente.como(ADMIN).post(f"/api/movimientos/{id_mov}/confirmar-salida")
    assert "Salida confirmada" in cliente.notificador.enviados[-1][1]

    cliente.como(SOLICITANTE).post(f"/api/movimientos/{id_mov}/solicitar-devolucion")
    assert "Devolucion solicitada" in cliente.notificador.enviados[-1][1]

    cliente.como(ADMIN).post(f"/api/movimientos/{id_mov}/confirmar-devolucion")
    assert "Devolucion confirmada" in cliente.notificador.enviados[-1][1]
    assert len(cliente.notificador.enviados) == 6


def test_una_accion_que_falla_no_avisa():
    cliente = _Cliente()
    id_mov = _solicitar(cliente)
    enviados = len(cliente.notificador.enviados)

    cliente.como(EXTRANO).post(f"/api/movimientos/{id_mov}/aprobar")
    cliente.como(ANA).post(f"/api/movimientos/{id_mov}/rechazar", json={"motivo_rechazo": ""})

    assert len(cliente.notificador.enviados) == enviados
