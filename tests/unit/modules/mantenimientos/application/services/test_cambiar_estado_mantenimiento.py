from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.mantenimientos.application.dto.cambiar_estado_mantenimiento_dto import (
    CambiarEstadoMantenimientoDTO,
)
from modules.mantenimientos.application.services.cambiar_estado_mantenimiento import (
    CambiarEstadoMantenimientoService,
)
from modules.mantenimientos.domain.entities import (
    EstadoMantenimiento,
    Mantenimiento,
    TipoMantenimiento,
)
from modules.mantenimientos.domain.errors import (
    MantenimientoNoEncontradoError,
    TransicionEstadoMantenimientoInvalidaError,
)
from shared.domain.entities.audit import AuditPersona


def _mantenimiento(estado=EstadoMantenimiento.PROGRAMADO, solicitud_id=None) -> Mantenimiento:
    return Mantenimiento(
        id="1",
        activo_id="a1",
        solicitud_id=solicitud_id,
        tipo=TipoMantenimiento.CORRECTIVO,
        tecnico_responsable_id="u1",
        fecha=datetime.now(UTC),
        observaciones=None,
        costo=None,
        documentos=[],
        evidencias=[],
        estado=estado,
        frecuencia_dias=None,
        proxima_fecha_sugerida=None,
        alerta_enviada=False,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


def _dto(estado_nuevo, **overrides) -> CambiarEstadoMantenimientoDTO:
    valores = dict(
        id_mantenimiento="1",
        estado_nuevo=estado_nuevo,
        actor_id="u1",
        actor_nombre="Tecnico",
        actor_rol="mantenimiento",
        actor_area_id=None,
    )
    valores.update(overrides)
    return CambiarEstadoMantenimientoDTO(**valores)


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _mantenimiento()
    mock.guardar.side_effect = lambda m: m
    return mock


@pytest.fixture
def solicitud_estado_mock():
    return AsyncMock()


async def test_cambiar_estado_aplica_una_transicion_valida(repositorio_mock, solicitud_estado_mock):
    service = CambiarEstadoMantenimientoService(repositorio_mock, solicitud_estado_mock)

    resultado = await service.ejecutar(_dto(EstadoMantenimiento.EN_PROCESO))

    assert resultado.estado == EstadoMantenimiento.EN_PROCESO.value
    solicitud_estado_mock.marcar_resuelta.assert_not_called()


async def test_completar_un_mantenimiento_sin_solicitud_no_llama_a_solicitudes(
    repositorio_mock, solicitud_estado_mock
):
    repositorio_mock.obtener_por_id.return_value = _mantenimiento(EstadoMantenimiento.EN_PROCESO)
    service = CambiarEstadoMantenimientoService(repositorio_mock, solicitud_estado_mock)

    await service.ejecutar(_dto(EstadoMantenimiento.COMPLETADO))

    solicitud_estado_mock.marcar_resuelta.assert_not_called()


async def test_completar_un_mantenimiento_con_solicitud_la_marca_resuelta(
    repositorio_mock, solicitud_estado_mock
):
    repositorio_mock.obtener_por_id.return_value = _mantenimiento(
        EstadoMantenimiento.EN_PROCESO, solicitud_id="sol-1"
    )
    service = CambiarEstadoMantenimientoService(repositorio_mock, solicitud_estado_mock)

    await service.ejecutar(_dto(EstadoMantenimiento.COMPLETADO))

    solicitud_estado_mock.marcar_resuelta.assert_called_once()
    assert solicitud_estado_mock.marcar_resuelta.call_args.args[0] == "sol-1"


async def test_cambiar_estado_lanza_error_si_la_transicion_es_invalida(
    repositorio_mock, solicitud_estado_mock
):
    repositorio_mock.obtener_por_id.return_value = _mantenimiento(EstadoMantenimiento.COMPLETADO)
    service = CambiarEstadoMantenimientoService(repositorio_mock, solicitud_estado_mock)

    with pytest.raises(TransicionEstadoMantenimientoInvalidaError):
        await service.ejecutar(_dto(EstadoMantenimiento.PROGRAMADO))

    repositorio_mock.guardar.assert_not_called()


async def test_cambiar_estado_lanza_error_si_no_existe(repositorio_mock, solicitud_estado_mock):
    repositorio_mock.obtener_por_id.return_value = None
    service = CambiarEstadoMantenimientoService(repositorio_mock, solicitud_estado_mock)

    with pytest.raises(MantenimientoNoEncontradoError):
        await service.ejecutar(_dto(EstadoMantenimiento.EN_PROCESO))
