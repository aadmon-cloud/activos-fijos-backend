import asyncio

from modules.dashboard.application.ports.activos_resumen_port import ActivosResumenPort
from modules.dashboard.application.ports.auditorias_resumen_port import AuditoriasResumenPort
from modules.dashboard.application.ports.mantenimientos_resumen_port import (
    MantenimientosResumenPort,
)
from modules.dashboard.application.ports.movimientos_resumen_port import MovimientosResumenPort
from modules.dashboard.application.ports.solicitudes_resumen_port import SolicitudesResumenPort
from modules.dashboard.domain.entities import ResumenDashboard

_LIMITE_AUDITORIAS_RECIENTES_DEFECTO = 5


class ObtenerDashboardService:
    def __init__(
        self,
        activos: ActivosResumenPort,
        solicitudes: SolicitudesResumenPort,
        mantenimientos: MantenimientosResumenPort,
        auditorias: AuditoriasResumenPort,
        movimientos: MovimientosResumenPort,
    ):
        self._activos = activos
        self._solicitudes = solicitudes
        self._mantenimientos = mantenimientos
        self._auditorias = auditorias
        self._movimientos = movimientos

    async def ejecutar(
        self, limite_auditorias_recientes: int = _LIMITE_AUDITORIAS_RECIENTES_DEFECTO
    ) -> ResumenDashboard:
        activos, solicitudes, mantenimientos, auditorias, movimientos = await asyncio.gather(
            self._activos.obtener(),
            self._solicitudes.obtener(),
            self._mantenimientos.obtener(),
            self._auditorias.obtener(limite_auditorias_recientes),
            self._movimientos.obtener(),
        )
        return ResumenDashboard(
            activos=activos,
            solicitudes=solicitudes,
            mantenimientos=mantenimientos,
            auditorias=auditorias,
            movimientos=movimientos,
        )
