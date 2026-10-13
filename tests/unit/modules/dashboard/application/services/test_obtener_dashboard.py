from unittest.mock import AsyncMock

from modules.dashboard.application.services.obtener_dashboard import ObtenerDashboardService
from modules.dashboard.domain.entities import (
    ResumenActivos,
    ResumenAuditorias,
    ResumenMantenimientos,
    ResumenMovimientos,
    ResumenSolicitudes,
)


def _servicio():
    activos = AsyncMock()
    activos.obtener.return_value = ResumenActivos(total=1, por_estado_ciclo_vida={}, por_tipo={})
    solicitudes = AsyncMock()
    solicitudes.obtener.return_value = ResumenSolicitudes(
        total=2, por_estado={}, por_tipo={}, pendientes=0
    )
    mantenimientos = AsyncMock()
    mantenimientos.obtener.return_value = ResumenMantenimientos(
        total=3, por_estado={}, pendientes_de_alerta=0
    )
    auditorias = AsyncMock()
    auditorias.obtener.return_value = ResumenAuditorias(total=4, por_estado={}, ultimas=[])
    movimientos = AsyncMock()
    movimientos.obtener.return_value = ResumenMovimientos(
        total=5, por_tipo={}, por_estado={}, pendientes_de_aprobacion=0
    )
    service = ObtenerDashboardService(activos, solicitudes, mantenimientos, auditorias, movimientos)
    return service, activos, solicitudes, mantenimientos, auditorias, movimientos


async def test_ejecutar_combina_los_5_resumenes():
    service, *_ = _servicio()

    resultado = await service.ejecutar()

    assert resultado.activos.total == 1
    assert resultado.solicitudes.total == 2
    assert resultado.mantenimientos.total == 3
    assert resultado.auditorias.total == 4
    assert resultado.movimientos.total == 5


async def test_ejecutar_propaga_el_limite_de_auditorias_recientes():
    service, _, _, _, auditorias, _ = _servicio()

    await service.ejecutar(limite_auditorias_recientes=10)

    auditorias.obtener.assert_awaited_once_with(10)


async def test_ejecutar_usa_el_limite_por_defecto():
    service, _, _, _, auditorias, _ = _servicio()

    await service.ejecutar()

    auditorias.obtener.assert_awaited_once_with(5)
