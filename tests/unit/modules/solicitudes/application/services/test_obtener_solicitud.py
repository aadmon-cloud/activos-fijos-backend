from datetime import UTC, datetime

from modules.solicitudes.domain.entities import (
    EstadoSolicitud,
    PrioridadSolicitud,
    Solicitud,
    TipoSolicitud,
)
from shared.domain.entities.audit import AuditPersona


def _solicitud(**overrides) -> Solicitud:
    valores = dict(
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
    valores.update(overrides)
    return Solicitud(**valores)

from unittest.mock import AsyncMock

import pytest

from modules.solicitudes.application.dto.obtener_solicitud_dto import ObtenerSolicitudDTO
from modules.solicitudes.application.ports.resolutor_referencias import (
    ActivoNombre,
    NombresReferenciasSolicitud,
)
from modules.solicitudes.application.services.obtener_solicitud import ObtenerSolicitudService
from modules.solicitudes.domain.errors import SolicitudNoEncontradaError


def _servicio(solicitud):
    repositorio = AsyncMock()
    repositorio.obtener_por_id.return_value = solicitud
    resolutor = AsyncMock()
    resolutor.resolver.return_value = NombresReferenciasSolicitud(
        activos={"a1": ActivoNombre(nombre="Laptop", numero_inventario="INV-001")}
    )

    return ObtenerSolicitudService(repositorio, resolutor)


def _dto(actor_id="solicitante-1", rol="empleado", area=None) -> ObtenerSolicitudDTO:
    return ObtenerSolicitudDTO(id_solicitud="1", actor_id=actor_id, actor_rol=rol, actor_area_id=area)


async def test_el_solicitante_ve_el_detalle_con_nombres_y_puede_comentar():
    resultado = await _servicio(_solicitud()).ejecutar(_dto())

    assert resultado.descripcion == "desc"
    assert resultado.activo_nombre == "Laptop"
    assert resultado.puede_comentar is True


async def test_el_detalle_informa_los_estados_que_este_usuario_puede_aplicar():
    servicio = _servicio(_solicitud())

    tecnico = await servicio.ejecutar(_dto("tecnico-1", "mantenimiento"))
    solicitante = await servicio.ejecutar(_dto())

    assert tecnico.estados_permitidos == ["en_proceso", "rechazada"]
    assert solicitante.estados_permitidos == []


async def test_el_solicitante_puede_cerrar_una_resuelta():
    resultado = await _servicio(_solicitud(estado=EstadoSolicitud.RESUELTA)).ejecutar(_dto())

    assert resultado.estados_permitidos == ["cerrada"]


async def test_un_usuario_sin_relacion_recibe_no_encontrada_igual_que_una_inexistente():
    with pytest.raises(SolicitudNoEncontradaError):
        await _servicio(_solicitud()).ejecutar(_dto("tercero-1", "tecnologia", "area-2"))


async def test_obtener_lanza_error_si_no_existe():
    with pytest.raises(SolicitudNoEncontradaError):
        await _servicio(None).ejecutar(_dto())
