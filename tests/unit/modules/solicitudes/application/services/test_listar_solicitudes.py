from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.solicitudes.application.dto.listar_solicitudes_dto import ListarSolicitudesDTO
from modules.solicitudes.application.services.listar_solicitudes import ListarSolicitudesService
from modules.solicitudes.domain.entities import EstadoSolicitud, PrioridadSolicitud, Solicitud, TipoSolicitud
from shared.domain.entities.audit import AuditPersona


def _solicitud(id_: str) -> Solicitud:
    return Solicitud(
        id=id_,
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


async def test_listar_solicitudes_retorna_los_dtos_del_repositorio():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar.return_value = [_solicitud("1"), _solicitud("2")]
    service = ListarSolicitudesService(repositorio_mock)

    resultado = await service.ejecutar(ListarSolicitudesDTO())

    assert len(resultado) == 2


async def test_listar_solicitudes_limita_el_limit_maximo():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar.return_value = []
    service = ListarSolicitudesService(repositorio_mock)

    await service.ejecutar(ListarSolicitudesDTO(limit=5000))

    _, kwargs = repositorio_mock.listar.call_args
    assert kwargs["limit"] == 1000
