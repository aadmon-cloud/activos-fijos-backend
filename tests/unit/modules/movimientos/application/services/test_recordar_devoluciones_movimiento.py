from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from modules.movimientos.application.services.recordar_devoluciones_movimiento import (
    DIAS_AVISO_DEVOLUCION,
    RecordarDevolucionesMovimientoService,
)
from modules.movimientos.domain.entities import EstadoItemMovimiento as I
from modules.movimientos.domain.entities import EstadoMovimiento as E


def _servicio(fabrica, pendientes):
    repo = AsyncMock()
    repo.listar_devoluciones_por_recordar.return_value = pendientes
    repo.guardar.side_effect = lambda m: m
    activo_movimiento = AsyncMock()
    activo_movimiento.obtener_resumenes.return_value = {"a1": fabrica.resumen(), "a2": fabrica.resumen(id="a2")}
    notificador = AsyncMock()

    return RecordarDevolucionesMovimientoService(repo, activo_movimiento, notificador), repo, notificador


def _en_curso(fabrica, **overrides):
    return fabrica.movimiento(
        estado=E.EN_CURSO,
        fecha_retorno_estimada=datetime(2026, 5, 2, tzinfo=UTC),
        items=[fabrica.item(activo_id="a1", estado=I.EN_CURSO), fabrica.item(activo_id="a2", estado=I.EN_CURSO)],
        **overrides,
    )


async def test_recuerda_una_vez_por_movimiento_y_lo_marca(fabrica):
    service, repo, notificador = _servicio(fabrica, [_en_curso(fabrica)])

    cantidad = await service.ejecutar(ahora=datetime(2026, 5, 1, tzinfo=UTC))

    assert cantidad == 1
    notificador.notificar.assert_awaited_once()
    assert repo.guardar.call_args.args[0].recordatorio_devolucion_enviado is True


async def test_el_aviso_menciona_los_activos_del_movimiento(fabrica):
    service, _, notificador = _servicio(fabrica, [_en_curso(fabrica)])

    await service.ejecutar(ahora=datetime(2026, 5, 1, tzinfo=UTC))

    assert "Proyector" in notificador.notificar.await_args.kwargs["cuerpo"]
    assert "2 activos" in notificador.notificar.await_args.kwargs["asunto"]


async def test_consulta_hasta_el_plazo_de_aviso(fabrica):
    service, repo, _ = _servicio(fabrica, [])
    ahora = datetime(2026, 5, 1, tzinfo=UTC)

    cantidad = await service.ejecutar(ahora=ahora)

    assert cantidad == 0
    repo.listar_devoluciones_por_recordar.assert_awaited_once_with(ahora + timedelta(days=DIAS_AVISO_DEVOLUCION))
    repo.guardar.assert_not_called()
