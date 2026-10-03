from unittest.mock import AsyncMock

import pytest

from modules.solicitudes.application.dto.crear_solicitud_dto import CrearSolicitudDTO
from modules.solicitudes.application.ports.activo_resumen_port import ActivoResumen
from modules.solicitudes.application.services.crear_solicitud import CrearSolicitudService
from modules.solicitudes.domain.entities import EstadoSolicitud, PrioridadSolicitud, TipoSolicitud
from modules.solicitudes.domain.errors import (
    ActivoNoAsignadoError,
    ActivoNoEncontradoParaSolicitudError,
    DescripcionVaciaError,
)


def _dto(**overrides) -> CrearSolicitudDTO:
    valores = dict(
        tipo=TipoSolicitud.MANTENIMIENTO,
        activo_id="a1",
        descripcion="El equipo hace ruido",
        prioridad=PrioridadSolicitud.MEDIA,
        creado_por_id="u1",
        creado_por_nombre="Ana",
        creado_por_rol="empleado",
    )
    valores.update(overrides)
    return CrearSolicitudDTO(**valores)


@pytest.fixture
def solicitud_repository_mock():
    mock = AsyncMock()
    mock.guardar.side_effect = lambda solicitud: solicitud
    return mock


@pytest.fixture
def activo_resumen_mock():
    mock = AsyncMock()
    mock.obtener_resumen.return_value = ActivoResumen(id="a1", responsable_id="u1", area_id="area-1")
    return mock


@pytest.fixture
def notificador_mock():
    return AsyncMock()


async def test_crear_solicitud_de_mantenimiento_asigna_por_rol(
    solicitud_repository_mock, activo_resumen_mock, notificador_mock
):
    service = CrearSolicitudService(solicitud_repository_mock, activo_resumen_mock, notificador_mock)

    resultado = await service.ejecutar(_dto())

    assert resultado.rol_asignado == "mantenimiento"
    assert resultado.area_id is None
    assert resultado.estado == EstadoSolicitud.PENDIENTE.value
    notificador_mock.notificar.assert_called_once()


async def test_crear_solicitud_de_ajuste_asigna_por_area(
    solicitud_repository_mock, activo_resumen_mock, notificador_mock
):
    service = CrearSolicitudService(solicitud_repository_mock, activo_resumen_mock, notificador_mock)

    resultado = await service.ejecutar(_dto(tipo=TipoSolicitud.AJUSTE))

    assert resultado.rol_asignado is None
    assert resultado.area_id == "area-1"


async def test_crear_solicitud_lanza_error_si_el_activo_no_existe(
    solicitud_repository_mock, activo_resumen_mock, notificador_mock
):
    activo_resumen_mock.obtener_resumen.return_value = None
    service = CrearSolicitudService(solicitud_repository_mock, activo_resumen_mock, notificador_mock)

    with pytest.raises(ActivoNoEncontradoParaSolicitudError):
        await service.ejecutar(_dto())

    solicitud_repository_mock.guardar.assert_not_called()


async def test_crear_solicitud_lanza_error_si_el_usuario_no_es_responsable(
    solicitud_repository_mock, activo_resumen_mock, notificador_mock
):
    service = CrearSolicitudService(solicitud_repository_mock, activo_resumen_mock, notificador_mock)

    with pytest.raises(ActivoNoAsignadoError):
        await service.ejecutar(_dto(creado_por_id="otro-usuario", creado_por_rol="empleado"))

    solicitud_repository_mock.guardar.assert_not_called()


async def test_crear_solicitud_permite_a_administrador_general_sin_ser_responsable(
    solicitud_repository_mock, activo_resumen_mock, notificador_mock
):
    service = CrearSolicitudService(solicitud_repository_mock, activo_resumen_mock, notificador_mock)

    resultado = await service.ejecutar(
        _dto(creado_por_id="admin-1", creado_por_rol="administrador_general")
    )

    assert resultado is not None


async def test_crear_solicitud_lanza_error_si_la_descripcion_esta_vacia(
    solicitud_repository_mock, activo_resumen_mock, notificador_mock
):
    service = CrearSolicitudService(solicitud_repository_mock, activo_resumen_mock, notificador_mock)

    with pytest.raises(DescripcionVaciaError):
        await service.ejecutar(_dto(descripcion="   "))

    solicitud_repository_mock.guardar.assert_not_called()
