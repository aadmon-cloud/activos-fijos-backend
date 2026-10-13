from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.dashboard.application.ports.activos_resumen_port import ActivosResumenPort
from modules.dashboard.application.ports.auditorias_resumen_port import AuditoriasResumenPort
from modules.dashboard.application.ports.mantenimientos_resumen_port import (
    MantenimientosResumenPort,
)
from modules.dashboard.application.ports.movimientos_resumen_port import MovimientosResumenPort
from modules.dashboard.application.ports.solicitudes_resumen_port import SolicitudesResumenPort
from modules.dashboard.application.services.obtener_dashboard import ObtenerDashboardService
from modules.dashboard.domain.entities import (
    AuditoriaReciente,
    ResumenActivos,
    ResumenAuditorias,
    ResumenMantenimientos,
    ResumenMovimientos,
    ResumenSolicitudes,
)
from modules.dashboard.infrastructure.api.dependencies import get_obtener_dashboard_service
from modules.dashboard.infrastructure.api.routes import router
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_usuario_autenticado,
)
from shared.infrastructure.api.error_handlers import register_error_handlers


class _ActivosResumenFalso(ActivosResumenPort):
    async def obtener(self):
        return ResumenActivos(
            total=10, por_estado_ciclo_vida={"disponible": 8, "prestado": 2}, por_tipo={"activo_fijo": 10}
        )


class _SolicitudesResumenFalso(SolicitudesResumenPort):
    async def obtener(self):
        return ResumenSolicitudes(
            total=4, por_estado={"pendiente": 1, "resuelta": 3}, por_tipo={"mantenimiento": 4}, pendientes=1
        )


class _MantenimientosResumenFalso(MantenimientosResumenPort):
    async def obtener(self):
        return ResumenMantenimientos(total=3, por_estado={"programado": 3}, pendientes_de_alerta=1)


class _AuditoriasResumenFalso(AuditoriasResumenPort):
    def __init__(self):
        self.limite_recibido = None

    async def obtener(self, limite_recientes: int):
        self.limite_recibido = limite_recientes
        return ResumenAuditorias(
            total=2,
            por_estado={"notificada": 2},
            ultimas=[
                AuditoriaReciente(
                    id="aud-1",
                    usuario_auditado_id="u1",
                    usuario_auditado_nombre="Camilo Perez",
                    fecha_cierre=datetime(2026, 1, 1, tzinfo=UTC),
                    no_encontrados=1,
                )
            ],
        )


class _MovimientosResumenFalso(MovimientosResumenPort):
    async def obtener(self):
        return ResumenMovimientos(
            total=6, por_tipo={"prestamo": 6}, por_estado={"solicitado": 2}, pendientes_de_aprobacion=2
        )


class _IdentidadContenedor:
    def __init__(self, identidad: IdentidadUsuarioAutenticada):
        self.valor = identidad


def _identidad(id_usuario: str, rol: str) -> IdentidadUsuarioAutenticada:
    return IdentidadUsuarioAutenticada(
        id_usuario=id_usuario, email=f"{id_usuario}@example.com", nombre=f"Nombre {id_usuario}",
        rol=rol, area_id=None,
    )


def _crear_cliente_de_prueba():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    auditorias_resumen = _AuditoriasResumenFalso()
    app.dependency_overrides[get_obtener_dashboard_service] = lambda: ObtenerDashboardService(
        _ActivosResumenFalso(),
        _SolicitudesResumenFalso(),
        _MantenimientosResumenFalso(),
        auditorias_resumen,
        _MovimientosResumenFalso(),
    )

    contenedor = _IdentidadContenedor(_identidad("admin-1", "administrador_general"))
    app.dependency_overrides[requiere_usuario_autenticado] = lambda: contenedor.valor

    cliente = TestClient(app)
    cliente.auditorias_resumen = auditorias_resumen

    return cliente, contenedor


def test_obtener_dashboard_combina_los_5_resumenes():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.get("/api/dashboard")

    assert respuesta.status_code == 200
    data = respuesta.json()["data"]
    assert data["activos"]["total"] == 10
    assert data["solicitudes"]["pendientes"] == 1
    assert data["mantenimientos"]["pendientes_de_alerta"] == 1
    assert data["auditorias"]["ultimas"][0]["usuario_auditado_nombre"] == "Camilo Perez"
    assert data["movimientos"]["pendientes_de_aprobacion"] == 2


def test_obtener_dashboard_sin_rol_administrador_general_retorna_403():
    cliente, contenedor = _crear_cliente_de_prueba()
    contenedor.valor = _identidad("empleado-1", "empleado")

    respuesta = cliente.get("/api/dashboard")

    assert respuesta.status_code == 403


def test_obtener_dashboard_usa_el_limite_de_auditorias_recientes_por_defecto():
    cliente, _ = _crear_cliente_de_prueba()

    cliente.get("/api/dashboard")

    assert cliente.auditorias_resumen.limite_recibido == 5


def test_obtener_dashboard_respeta_el_limite_de_auditorias_recientes_pedido():
    cliente, _ = _crear_cliente_de_prueba()

    cliente.get("/api/dashboard", params={"limite_auditorias_recientes": 15})

    assert cliente.auditorias_resumen.limite_recibido == 15


def test_obtener_dashboard_rechaza_un_limite_fuera_de_rango():
    cliente, _ = _crear_cliente_de_prueba()

    respuesta = cliente.get("/api/dashboard", params={"limite_auditorias_recientes": 100})

    assert respuesta.status_code == 422
