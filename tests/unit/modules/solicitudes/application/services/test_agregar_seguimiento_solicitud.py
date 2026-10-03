from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.solicitudes.application.dto.agregar_seguimiento_solicitud_dto import (
    AgregarSeguimientoSolicitudDTO,
)
from modules.solicitudes.application.services.agregar_seguimiento_solicitud import (
    AgregarSeguimientoSolicitudService,
)
from modules.solicitudes.domain.entities import EstadoSolicitud, PrioridadSolicitud, Solicitud, TipoSolicitud
from modules.solicitudes.domain.errors import SolicitudNoEncontradaError, SolicitudSinPermisoError
from shared.domain.entities.audit import AuditPersona


def _solicitud() -> Solicitud:
    return Solicitud(
        id="1",
        tipo=TipoSolicitud.MANTENIMIENTO,
        activo_id="a1",
        descripcion="desc",
        prioridad=PrioridadSolicitud.MEDIA,
        evidencias=[],
        estado=EstadoSolicitud.PENDIENTE,
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


async def test_agregar_seguimiento_agrega_entrada(repositorio_mock):
    service = AgregarSeguimientoSolicitudService(repositorio_mock)

    resultado = await service.ejecutar(
        AgregarSeguimientoSolicitudDTO(
            id_solicitud="1",
            comentario="  Ya lo estamos revisando  ",
            actor_id="solicitante-1",
            actor_nombre="Ana",
            actor_rol="empleado",
            actor_area_id=None,
        )
    )

    assert len(resultado.seguimiento) == 1
    assert resultado.seguimiento[0].comentario == "Ya lo estamos revisando"


async def test_agregar_seguimiento_lanza_error_si_no_tiene_permiso(repositorio_mock):
    service = AgregarSeguimientoSolicitudService(repositorio_mock)

    with pytest.raises(SolicitudSinPermisoError):
        await service.ejecutar(
            AgregarSeguimientoSolicitudDTO(
                id_solicitud="1",
                comentario="comentario",
                actor_id="desconocido",
                actor_nombre="X",
                actor_rol="tecnologia",
                actor_area_id="otra-area",
            )
        )


async def test_agregar_seguimiento_lanza_error_si_no_existe(repositorio_mock):
    repositorio_mock.obtener_por_id.return_value = None
    service = AgregarSeguimientoSolicitudService(repositorio_mock)

    with pytest.raises(SolicitudNoEncontradaError):
        await service.ejecutar(
            AgregarSeguimientoSolicitudDTO(
                id_solicitud="1",
                comentario="comentario",
                actor_id="solicitante-1",
                actor_nombre="Ana",
                actor_rol="empleado",
                actor_area_id=None,
            )
        )
