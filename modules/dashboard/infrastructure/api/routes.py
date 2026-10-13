from typing import Annotated

from fastapi import APIRouter, Depends, Query

from modules.dashboard.application.services.obtener_dashboard import ObtenerDashboardService
from modules.dashboard.domain.entities import ResumenDashboard
from modules.dashboard.infrastructure.api.dependencies import get_obtener_dashboard_service
from modules.dashboard.infrastructure.api.schemas import (
    AuditoriaRecienteResponse,
    DashboardResponse,
    ResumenActivosResponse,
    ResumenAuditoriasResponse,
    ResumenMantenimientosResponse,
    ResumenMovimientosResponse,
    ResumenSolicitudesResponse,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import requiere_rol

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_requiere_administrador_general = requiere_rol("administrador_general")


def _a_response(resumen: ResumenDashboard) -> DashboardResponse:
    return DashboardResponse(
        activos=ResumenActivosResponse(
            total=resumen.activos.total,
            por_estado_ciclo_vida=resumen.activos.por_estado_ciclo_vida,
            por_tipo=resumen.activos.por_tipo,
        ),
        solicitudes=ResumenSolicitudesResponse(
            total=resumen.solicitudes.total,
            por_estado=resumen.solicitudes.por_estado,
            por_tipo=resumen.solicitudes.por_tipo,
            pendientes=resumen.solicitudes.pendientes,
        ),
        mantenimientos=ResumenMantenimientosResponse(
            total=resumen.mantenimientos.total,
            por_estado=resumen.mantenimientos.por_estado,
            pendientes_de_alerta=resumen.mantenimientos.pendientes_de_alerta,
        ),
        auditorias=ResumenAuditoriasResponse(
            total=resumen.auditorias.total,
            por_estado=resumen.auditorias.por_estado,
            ultimas=[
                AuditoriaRecienteResponse(
                    id=a.id,
                    usuario_auditado_id=a.usuario_auditado_id,
                    usuario_auditado_nombre=a.usuario_auditado_nombre,
                    fecha_cierre=a.fecha_cierre,
                    no_encontrados=a.no_encontrados,
                )
                for a in resumen.auditorias.ultimas
            ],
        ),
        movimientos=ResumenMovimientosResponse(
            total=resumen.movimientos.total,
            por_tipo=resumen.movimientos.por_tipo,
            por_estado=resumen.movimientos.por_estado,
            pendientes_de_aprobacion=resumen.movimientos.pendientes_de_aprobacion,
        ),
    )


@router.get(
    "",
    summary="Resumen agregado de activos, solicitudes, mantenimientos, auditorias y movimientos",
)
async def obtener_dashboard(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)],
    service: Annotated[ObtenerDashboardService, Depends(get_obtener_dashboard_service)],
    limite_auditorias_recientes: int = Query(default=5, ge=1, le=20),
):
    resumen = await service.ejecutar(limite_auditorias_recientes)
    return {"status": "success", "data": _a_response(resumen).model_dump()}
