from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.solicitudes.application.services.obtener_solicitud import ObtenerSolicitudService
from modules.solicitudes.domain.entities import EstadoSolicitud, PrioridadSolicitud, Solicitud, TipoSolicitud
from modules.solicitudes.domain.errors import SolicitudNoEncontradaError
from shared.domain.entities.audit import AuditPersona


async def test_obtener_solicitud_retorna_el_dto_si_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = Solicitud(
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
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    service = ObtenerSolicitudService(repositorio_mock)

    resultado = await service.ejecutar("1")

    assert resultado.descripcion == "desc"


async def test_obtener_solicitud_lanza_error_si_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    service = ObtenerSolicitudService(repositorio_mock)

    with pytest.raises(SolicitudNoEncontradaError):
        await service.ejecutar("1")
