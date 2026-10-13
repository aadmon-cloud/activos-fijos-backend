from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.activos.application.dto.actualizar_activo_dto import ActualizarActivoDTO
from modules.activos.application.dto.complemento_dto import ComplementoDTO
from modules.activos.application.services.actualizar_activo import ActualizarActivoService
from modules.activos.domain.entities import Activo, EstadoCicloVida, TipoActivo
from modules.activos.domain.errors import (
    ActivoNoEncontradoError,
    ComplementoCantidadInvalidaError,
)
from shared.domain.entities.audit import AuditPersona


def _activo(**overrides) -> Activo:
    valores = dict(
        id="1",
        nombre="Laptop",
        numero_inventario="INV-001",
        tipo=TipoActivo.ACTIVO_FIJO,
        marca=None,
        modelo=None,
        serie=None,
        descripcion=None,
        categoria_id="c1",
        area_id="a1",
        responsable_id="u1",
        condicion_id="cond1",
        estado_ciclo_vida=EstadoCicloVida.DISPONIBLE,
        sede_id="s1",
        lugar_id="l1",
        complementos=[],
        observaciones=None,
        foto_url=None,
        ficha_tecnica_url=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Activo(**valores)


@pytest.fixture
def activo_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _activo()
    mock.guardar.side_effect = lambda activo: activo
    return mock


@pytest.fixture
def historial_repository_mock():
    return AsyncMock()


async def test_actualizar_activo_cambia_el_nombre(
    activo_repository_mock, historial_repository_mock
):
    service = ActualizarActivoService(activo_repository_mock, historial_repository_mock)

    resultado = await service.ejecutar(
        ActualizarActivoDTO(
            id_activo="1",
            nombre="Laptop Actualizada",
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
        )
    )

    assert resultado.nombre == "Laptop Actualizada"
    historial_repository_mock.registrar.assert_not_called()


async def test_actualizar_activo_registra_historial_si_cambia_el_responsable(
    activo_repository_mock, historial_repository_mock
):
    service = ActualizarActivoService(activo_repository_mock, historial_repository_mock)

    await service.ejecutar(
        ActualizarActivoDTO(
            id_activo="1",
            responsable_id="u2",
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
        )
    )

    historial_repository_mock.registrar.assert_called_once()
    entrada = historial_repository_mock.registrar.call_args.args[0]
    assert entrada.campo == "responsable_id"
    assert entrada.valor_anterior == "u1"
    assert entrada.valor_nuevo == "u2"


async def test_actualizar_activo_lanza_error_si_no_existe(
    activo_repository_mock, historial_repository_mock
):
    activo_repository_mock.obtener_por_id.return_value = None
    service = ActualizarActivoService(activo_repository_mock, historial_repository_mock)

    with pytest.raises(ActivoNoEncontradoError):
        await service.ejecutar(
            ActualizarActivoDTO(
                id_activo="1", actualizado_por_id="9", actualizado_por_nombre="Admin"
            )
        )
