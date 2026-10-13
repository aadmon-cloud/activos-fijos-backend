from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.mantenimientos.application.ports.activo_resumen_port import ActivoResumen
from modules.mantenimientos.application.services.verificar_alertas_mantenimiento import (
    VerificarAlertasMantenimientoService,
)
from modules.mantenimientos.domain.entities import (
    EstadoMantenimiento,
    Mantenimiento,
    TipoMantenimiento,
)
from shared.domain.entities.audit import AuditPersona


def _mantenimiento(**overrides) -> Mantenimiento:
    valores = dict(
        id="1",
        activo_id="a1",
        solicitud_id=None,
        tipo=TipoMantenimiento.PREVENTIVO,
        tecnico_responsable_id="u1",
        fecha=datetime(2026, 1, 1, tzinfo=UTC),
        observaciones=None,
        costo=None,
        documentos=[],
        evidencias=[],
        estado=EstadoMantenimiento.COMPLETADO,
        frecuencia_dias=90,
        proxima_fecha_sugerida=datetime(2026, 4, 1, tzinfo=UTC),
        alerta_enviada=False,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Mantenimiento(**valores)


async def test_verificar_alertas_notifica_y_marca_como_enviada():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar_pendientes_de_alerta.return_value = [_mantenimiento()]
    activo_resumen_mock = AsyncMock()
    activo_resumen_mock.obtener_resumen.return_value = ActivoResumen(
        id="a1", responsable_id="u5", area_id="ar1"
    )
    notificador_mock = AsyncMock()
    service = VerificarAlertasMantenimientoService(
        repositorio_mock, activo_resumen_mock, notificador_mock
    )

    cantidad = await service.ejecutar()

    assert cantidad == 1
    notificador_mock.notificar.assert_called_once()
    destinatarios = notificador_mock.notificar.call_args.kwargs["destinatarios"]
    assert "rol:mantenimiento" in destinatarios
    assert "usuario:u5" in destinatarios

    mantenimiento_guardado = repositorio_mock.guardar.call_args.args[0]
    assert mantenimiento_guardado.alerta_enviada is True


async def test_verificar_alertas_sin_pendientes_no_notifica():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar_pendientes_de_alerta.return_value = []
    activo_resumen_mock = AsyncMock()
    notificador_mock = AsyncMock()
    service = VerificarAlertasMantenimientoService(
        repositorio_mock, activo_resumen_mock, notificador_mock
    )

    cantidad = await service.ejecutar()

    assert cantidad == 0
    notificador_mock.notificar.assert_not_called()
    repositorio_mock.guardar.assert_not_called()


async def test_verificar_alertas_notifica_aunque_el_activo_ya_no_exista():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar_pendientes_de_alerta.return_value = [_mantenimiento()]
    activo_resumen_mock = AsyncMock()
    activo_resumen_mock.obtener_resumen.return_value = None
    notificador_mock = AsyncMock()
    service = VerificarAlertasMantenimientoService(
        repositorio_mock, activo_resumen_mock, notificador_mock
    )

    await service.ejecutar()

    destinatarios = notificador_mock.notificar.call_args.kwargs["destinatarios"]
    assert destinatarios == ["rol:mantenimiento"]


async def test_el_aviso_va_al_responsable_al_area_y_a_mantenimiento_y_nombra_el_activo():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar_pendientes_de_alerta.return_value = [_mantenimiento()]
    activo_resumen_mock = AsyncMock()
    activo_resumen_mock.obtener_resumen.return_value = ActivoResumen(
        id="a1", responsable_id="u5", area_id="ar1", nombre="Lavamanos", numero_inventario="LAV-1"
    )
    notificador_mock = AsyncMock()
    service = VerificarAlertasMantenimientoService(repositorio_mock, activo_resumen_mock, notificador_mock)

    await service.ejecutar()

    kwargs = notificador_mock.notificar.call_args.kwargs
    assert kwargs["destinatarios"] == ["rol:mantenimiento", "usuario:u5", "area:ar1"]
    assert kwargs["asunto"] == "Proximo mantenimiento: Lavamanos (LAV-1)"
    assert "01/04/2026" in kwargs["cuerpo"]
    assert "{{URL_APP}}/mantenimientos/detalle?id=1" in kwargs["cuerpo"]


async def test_si_el_activo_ya_no_existe_el_aviso_va_solo_a_mantenimiento():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar_pendientes_de_alerta.return_value = [_mantenimiento()]
    activo_resumen_mock = AsyncMock()
    activo_resumen_mock.obtener_resumen.return_value = None
    notificador_mock = AsyncMock()
    service = VerificarAlertasMantenimientoService(repositorio_mock, activo_resumen_mock, notificador_mock)

    await service.ejecutar()

    kwargs = notificador_mock.notificar.call_args.kwargs
    assert kwargs["destinatarios"] == ["rol:mantenimiento"]
    assert kwargs["asunto"] == "Proximo mantenimiento: un activo"
