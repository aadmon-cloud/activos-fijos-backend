from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.mantenimientos.application.dto.crear_mantenimiento_dto import CrearMantenimientoDTO
from modules.mantenimientos.application.ports.activo_resumen_port import ActivoResumen
from modules.mantenimientos.application.services.crear_mantenimiento import (
    CrearMantenimientoService,
)
from modules.mantenimientos.domain.entities import EstadoMantenimiento, TipoMantenimiento
from modules.mantenimientos.domain.errors import (
    ActivoNoEncontradoParaMantenimientoError,
    SolicitudNoValidaParaMantenimientoError,
    TecnicoInvalidoError,
)


def _dto(**overrides) -> CrearMantenimientoDTO:
    valores = dict(
        activo_id="a1",
        tipo=TipoMantenimiento.PREVENTIVO,
        tecnico_responsable_id="u1",
        fecha=datetime(2026, 1, 1, tzinfo=UTC),
        creado_por_id="9",
        creado_por_nombre="Admin",
    )
    valores.update(overrides)
    return CrearMantenimientoDTO(**valores)


@pytest.fixture
def mantenimiento_repository_mock():
    mock = AsyncMock()
    mock.guardar.side_effect = lambda m: m
    return mock


@pytest.fixture
def activo_resumen_mock():
    mock = AsyncMock()
    mock.obtener_resumen.return_value = ActivoResumen(id="a1", responsable_id="u5", area_id="ar1")
    return mock


@pytest.fixture
def verificador_tecnico_mock():
    mock = AsyncMock()
    mock.tiene_rol_mantenimiento.return_value = True
    return mock


@pytest.fixture
def solicitud_verificador_mock():
    mock = AsyncMock()
    mock.corresponde_al_activo.return_value = True
    return mock


async def test_crear_mantenimiento_nace_programado(
    mantenimiento_repository_mock, activo_resumen_mock, verificador_tecnico_mock, solicitud_verificador_mock
):
    service = CrearMantenimientoService(
        mantenimiento_repository_mock,
        activo_resumen_mock,
        verificador_tecnico_mock,
        solicitud_verificador_mock,
        AsyncMock(),
    )

    resultado = await service.ejecutar(_dto())

    assert resultado.estado == EstadoMantenimiento.PROGRAMADO.value
    assert resultado.proxima_fecha_sugerida is None


async def test_crear_mantenimiento_calcula_proxima_fecha_sugerida(
    mantenimiento_repository_mock, activo_resumen_mock, verificador_tecnico_mock, solicitud_verificador_mock
):
    service = CrearMantenimientoService(
        mantenimiento_repository_mock,
        activo_resumen_mock,
        verificador_tecnico_mock,
        solicitud_verificador_mock,
        AsyncMock(),
    )

    resultado = await service.ejecutar(_dto(frecuencia_dias=90))

    assert resultado.proxima_fecha_sugerida == datetime(2026, 4, 1, tzinfo=UTC)


async def test_crear_mantenimiento_lanza_error_si_el_activo_no_existe(
    mantenimiento_repository_mock, activo_resumen_mock, verificador_tecnico_mock, solicitud_verificador_mock
):
    activo_resumen_mock.obtener_resumen.return_value = None
    service = CrearMantenimientoService(
        mantenimiento_repository_mock,
        activo_resumen_mock,
        verificador_tecnico_mock,
        solicitud_verificador_mock,
        AsyncMock(),
    )

    with pytest.raises(ActivoNoEncontradoParaMantenimientoError):
        await service.ejecutar(_dto())

    mantenimiento_repository_mock.guardar.assert_not_called()


async def test_crear_mantenimiento_lanza_error_si_el_tecnico_no_tiene_el_rol(
    mantenimiento_repository_mock, activo_resumen_mock, verificador_tecnico_mock, solicitud_verificador_mock
):
    verificador_tecnico_mock.tiene_rol_mantenimiento.return_value = False
    service = CrearMantenimientoService(
        mantenimiento_repository_mock,
        activo_resumen_mock,
        verificador_tecnico_mock,
        solicitud_verificador_mock,
        AsyncMock(),
    )

    with pytest.raises(TecnicoInvalidoError):
        await service.ejecutar(_dto())

    mantenimiento_repository_mock.guardar.assert_not_called()


async def test_crear_con_solicitud_asociada_valida_que_sea_del_mismo_activo(
    mantenimiento_repository_mock, activo_resumen_mock, verificador_tecnico_mock, solicitud_verificador_mock
):
    service = CrearMantenimientoService(
        mantenimiento_repository_mock,
        activo_resumen_mock,
        verificador_tecnico_mock,
        solicitud_verificador_mock,
        AsyncMock(),
    )

    resultado = await service.ejecutar(_dto(solicitud_id="s1"))

    solicitud_verificador_mock.corresponde_al_activo.assert_awaited_once_with("s1", "a1")
    assert resultado.solicitud_id == "s1"


async def test_crear_con_solicitud_que_no_corresponde_falla_sin_guardar(
    mantenimiento_repository_mock, activo_resumen_mock, verificador_tecnico_mock, solicitud_verificador_mock
):
    solicitud_verificador_mock.corresponde_al_activo.return_value = False
    service = CrearMantenimientoService(
        mantenimiento_repository_mock,
        activo_resumen_mock,
        verificador_tecnico_mock,
        solicitud_verificador_mock,
        AsyncMock(),
    )

    with pytest.raises(SolicitudNoValidaParaMantenimientoError):
        await service.ejecutar(_dto(solicitud_id="s-ajena"))

    mantenimiento_repository_mock.guardar.assert_not_called()


async def test_crear_sin_solicitud_no_consulta_al_verificador(
    mantenimiento_repository_mock, activo_resumen_mock, verificador_tecnico_mock, solicitud_verificador_mock
):
    service = CrearMantenimientoService(
        mantenimiento_repository_mock,
        activo_resumen_mock,
        verificador_tecnico_mock,
        solicitud_verificador_mock,
        AsyncMock(),
    )

    await service.ejecutar(_dto())

    solicitud_verificador_mock.corresponde_al_activo.assert_not_called()


async def test_crear_un_mantenimiento_locativo_es_valido(
    mantenimiento_repository_mock, activo_resumen_mock, verificador_tecnico_mock, solicitud_verificador_mock
):
    service = CrearMantenimientoService(
        mantenimiento_repository_mock,
        activo_resumen_mock,
        verificador_tecnico_mock,
        solicitud_verificador_mock,
        AsyncMock(),
    )

    resultado = await service.ejecutar(_dto(tipo=TipoMantenimiento.LOCATIVO))

    assert resultado.tipo == "locativo"


async def test_crear_avisa_al_tecnico_y_al_responsable_del_activo(
    mantenimiento_repository_mock, activo_resumen_mock, verificador_tecnico_mock, solicitud_verificador_mock
):
    activo_resumen_mock.obtener_resumen.return_value = ActivoResumen(
        id="a1", responsable_id="u5", area_id="ar1", nombre="Lavamanos", numero_inventario="LAV-1"
    )
    notificador = AsyncMock()
    service = CrearMantenimientoService(
        mantenimiento_repository_mock,
        activo_resumen_mock,
        verificador_tecnico_mock,
        solicitud_verificador_mock,
        notificador,
    )

    await service.ejecutar(_dto(tipo=TipoMantenimiento.LOCATIVO))

    kwargs = notificador.notificar.call_args.kwargs
    assert kwargs["destinatarios"] == ["usuario:u1", "usuario:u5"]
    assert kwargs["asunto"] == "Mantenimiento programado: Lavamanos (LAV-1)"
    assert "locativo" in kwargs["cuerpo"]
    assert "01/01/2026" in kwargs["cuerpo"]
    assert "{{URL_APP}}/mantenimientos/detalle?id=" in kwargs["cuerpo"]


async def test_si_el_tecnico_es_el_responsable_del_activo_se_avisa_una_sola_vez(
    mantenimiento_repository_mock, activo_resumen_mock, verificador_tecnico_mock, solicitud_verificador_mock
):
    activo_resumen_mock.obtener_resumen.return_value = ActivoResumen(id="a1", responsable_id="u1", area_id="ar1")
    notificador = AsyncMock()
    service = CrearMantenimientoService(
        mantenimiento_repository_mock,
        activo_resumen_mock,
        verificador_tecnico_mock,
        solicitud_verificador_mock,
        notificador,
    )

    await service.ejecutar(_dto())

    assert notificador.notificar.call_args.kwargs["destinatarios"] == ["usuario:u1"]
    assert notificador.notificar.call_args.kwargs["asunto"] == "Mantenimiento programado: un activo"


async def test_si_la_creacion_falla_no_se_avisa(
    mantenimiento_repository_mock, activo_resumen_mock, verificador_tecnico_mock, solicitud_verificador_mock
):
    verificador_tecnico_mock.tiene_rol_mantenimiento.return_value = False
    notificador = AsyncMock()
    service = CrearMantenimientoService(
        mantenimiento_repository_mock,
        activo_resumen_mock,
        verificador_tecnico_mock,
        solicitud_verificador_mock,
        notificador,
    )

    with pytest.raises(TecnicoInvalidoError):
        await service.ejecutar(_dto())

    notificador.notificar.assert_not_called()
