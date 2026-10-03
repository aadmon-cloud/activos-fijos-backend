from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.solicitudes.application.dto.cambiar_estado_solicitud_dto import (
    CambiarEstadoSolicitudDTO,
)
from modules.solicitudes.application.services.cambiar_estado_solicitud import (
    CambiarEstadoSolicitudService,
)
from modules.solicitudes.domain.entities import EstadoSolicitud, PrioridadSolicitud, Solicitud, TipoSolicitud
from modules.solicitudes.domain.errors import (
    SolicitudNoEncontradaError,
    SolicitudSinPermisoError,
    TransicionEstadoSolicitudInvalidaError,
)
from shared.domain.entities.audit import AuditPersona


def _solicitud(estado: EstadoSolicitud = EstadoSolicitud.PENDIENTE) -> Solicitud:
    return Solicitud(
        id="1",
        tipo=TipoSolicitud.MANTENIMIENTO,
        activo_id="a1",
        descripcion="desc",
        prioridad=PrioridadSolicitud.MEDIA,
        evidencias=[],
        estado=estado,
        rol_asignado="mantenimiento",
        area_id=None,
        seguimiento=[],
        creado_por=AuditPersona(id_persona="solicitante-1", nombre="Ana", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _solicitud()
    mock.guardar.side_effect = lambda solicitud: solicitud
    return mock


@pytest.fixture
def notificador_mock():
    return AsyncMock()


async def test_cambiar_estado_aplica_transicion_valida_y_agrega_seguimiento(
    repositorio_mock, notificador_mock
):
    service = CambiarEstadoSolicitudService(repositorio_mock, notificador_mock)

    resultado = await service.ejecutar(
        CambiarEstadoSolicitudDTO(
            id_solicitud="1",
            estado_nuevo=EstadoSolicitud.EN_PROCESO,
            actor_id="mantenimiento-1",
            actor_nombre="Tecnico",
            actor_rol="mantenimiento",
            actor_area_id=None,
        )
    )

    assert resultado.estado == EstadoSolicitud.EN_PROCESO.value
    assert len(resultado.seguimiento) == 1
    notificador_mock.notificar.assert_called_once()


async def test_cambiar_estado_lanza_error_si_la_transicion_es_invalida(
    repositorio_mock, notificador_mock
):
    repositorio_mock.obtener_por_id.return_value = _solicitud(EstadoSolicitud.CERRADA)
    service = CambiarEstadoSolicitudService(repositorio_mock, notificador_mock)

    with pytest.raises(TransicionEstadoSolicitudInvalidaError):
        await service.ejecutar(
            CambiarEstadoSolicitudDTO(
                id_solicitud="1",
                estado_nuevo=EstadoSolicitud.PENDIENTE,
                actor_id="solicitante-1",
                actor_nombre="Ana",
                actor_rol="empleado",
                actor_area_id=None,
            )
        )

    repositorio_mock.guardar.assert_not_called()


async def test_cambiar_estado_lanza_error_si_no_tiene_permiso(repositorio_mock, notificador_mock):
    service = CambiarEstadoSolicitudService(repositorio_mock, notificador_mock)

    with pytest.raises(SolicitudSinPermisoError):
        await service.ejecutar(
            CambiarEstadoSolicitudDTO(
                id_solicitud="1",
                estado_nuevo=EstadoSolicitud.EN_PROCESO,
                actor_id="desconocido",
                actor_nombre="X",
                actor_rol="tecnologia",
                actor_area_id="otra-area",
            )
        )

    repositorio_mock.guardar.assert_not_called()


async def test_cambiar_estado_lanza_error_si_no_existe(repositorio_mock, notificador_mock):
    repositorio_mock.obtener_por_id.return_value = None
    service = CambiarEstadoSolicitudService(repositorio_mock, notificador_mock)

    with pytest.raises(SolicitudNoEncontradaError):
        await service.ejecutar(
            CambiarEstadoSolicitudDTO(
                id_solicitud="1",
                estado_nuevo=EstadoSolicitud.EN_PROCESO,
                actor_id="solicitante-1",
                actor_nombre="Ana",
                actor_rol="empleado",
                actor_area_id=None,
            )
        )
