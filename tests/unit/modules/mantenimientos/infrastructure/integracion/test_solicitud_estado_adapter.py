from unittest.mock import AsyncMock, patch

import pytest

from modules.mantenimientos.application.ports.solicitud_estado_port import ActorSolicitud
from modules.mantenimientos.infrastructure.integracion.solicitud_estado_adapter import (
    SolicitudEstadoAdapter,
)
from modules.solicitudes.domain.entities import EstadoSolicitud
from modules.solicitudes.domain.errors import (
    SolicitudNoEncontradaError,
    SolicitudSinPermisoError,
    TransicionEstadoSolicitudInvalidaError,
)

_RUTA_GETTER = (
    "modules.mantenimientos.infrastructure.integracion.solicitud_estado_adapter."
    "get_cambiar_estado_solicitud_service"
)
_ACTOR = ActorSolicitud(id="u1", nombre="Tecnico", rol="mantenimiento", area_id=None)


@patch(_RUTA_GETTER)
async def test_marcar_resuelta_llama_al_servicio_real_con_estado_resuelta(getter_mock):
    servicio_mock = AsyncMock()
    getter_mock.return_value = servicio_mock
    adapter = SolicitudEstadoAdapter()

    await adapter.marcar_resuelta("sol-1", _ACTOR)

    servicio_mock.ejecutar.assert_called_once()
    dto = servicio_mock.ejecutar.call_args.args[0]
    assert dto.id_solicitud == "sol-1"
    assert dto.estado_nuevo == EstadoSolicitud.RESUELTA
    assert dto.actor_id == "u1"


@pytest.mark.parametrize(
    "excepcion",
    [
        SolicitudNoEncontradaError("sol-1"),
        SolicitudSinPermisoError("sol-1"),
        TransicionEstadoSolicitudInvalidaError("pendiente", "resuelta"),
    ],
)
@patch(_RUTA_GETTER)
async def test_marcar_resuelta_no_propaga_errores_de_sincronizacion(getter_mock, excepcion):
    servicio_mock = AsyncMock()
    servicio_mock.ejecutar.side_effect = excepcion
    getter_mock.return_value = servicio_mock
    adapter = SolicitudEstadoAdapter()

    await adapter.marcar_resuelta("sol-1", _ACTOR)
