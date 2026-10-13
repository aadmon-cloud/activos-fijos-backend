from functools import lru_cache

from modules.dashboard.application.ports.activos_resumen_port import ActivosResumenPort
from modules.dashboard.application.ports.auditorias_resumen_port import AuditoriasResumenPort
from modules.dashboard.application.ports.mantenimientos_resumen_port import (
    MantenimientosResumenPort,
)
from modules.dashboard.application.ports.movimientos_resumen_port import MovimientosResumenPort
from modules.dashboard.application.ports.solicitudes_resumen_port import SolicitudesResumenPort
from modules.dashboard.application.services.obtener_dashboard import ObtenerDashboardService
from modules.dashboard.infrastructure.persistence.mongo.activos_resumen_adapter import (
    MongoActivosResumenAdapter,
)
from modules.dashboard.infrastructure.persistence.mongo.auditorias_resumen_adapter import (
    MongoAuditoriasResumenAdapter,
)
from modules.dashboard.infrastructure.persistence.mongo.mantenimientos_resumen_adapter import (
    MongoMantenimientosResumenAdapter,
)
from modules.dashboard.infrastructure.persistence.mongo.movimientos_resumen_adapter import (
    MongoMovimientosResumenAdapter,
)
from modules.dashboard.infrastructure.persistence.mongo.solicitudes_resumen_adapter import (
    MongoSolicitudesResumenAdapter,
)


@lru_cache(maxsize=1)
def get_activos_resumen() -> ActivosResumenPort:
    return MongoActivosResumenAdapter()


@lru_cache(maxsize=1)
def get_solicitudes_resumen() -> SolicitudesResumenPort:
    return MongoSolicitudesResumenAdapter()


@lru_cache(maxsize=1)
def get_mantenimientos_resumen() -> MantenimientosResumenPort:
    return MongoMantenimientosResumenAdapter()


@lru_cache(maxsize=1)
def get_auditorias_resumen() -> AuditoriasResumenPort:
    return MongoAuditoriasResumenAdapter()


@lru_cache(maxsize=1)
def get_movimientos_resumen() -> MovimientosResumenPort:
    return MongoMovimientosResumenAdapter()


def get_obtener_dashboard_service() -> ObtenerDashboardService:
    return ObtenerDashboardService(
        activos=get_activos_resumen(),
        solicitudes=get_solicitudes_resumen(),
        mantenimientos=get_mantenimientos_resumen(),
        auditorias=get_auditorias_resumen(),
        movimientos=get_movimientos_resumen(),
    )
