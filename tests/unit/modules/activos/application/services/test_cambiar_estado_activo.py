from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from modules.activos.application.dto.cambiar_estado_activo_dto import CambiarEstadoActivoDTO
from modules.activos.application.services.cambiar_estado_activo import (
    CambiarEstadoActivoService,
)
from modules.activos.domain.entities import Activo, EstadoCicloVida, TipoActivo
from modules.activos.domain.errors import ActivoNoEncontradoError, TransicionEstadoInvalidaError
from shared.domain.entities.audit import AuditPersona


def _activo(estado: EstadoCicloVida = EstadoCicloVida.DISPONIBLE) -> Activo:
    return Activo(
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
        estado_ciclo_vida=estado,
        sede_id="s1",
        lugar_id="l1",
        complementos=[],
        observaciones=None,
        foto_url=None,
        ficha_tecnica_url=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


@pytest.fixture
def activo_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _activo()
    mock.guardar.side_effect = lambda activo: activo
    return mock


@pytest.fixture
def historial_repository_mock():
    return AsyncMock()


async def test_cambiar_estado_aplica_una_transicion_valida(
    activo_repository_mock, historial_repository_mock
):
    service = CambiarEstadoActivoService(activo_repository_mock, historial_repository_mock)

    resultado = await service.ejecutar(
        CambiarEstadoActivoDTO(
            id_activo="1",
            estado_nuevo=EstadoCicloVida.PRESTADO,
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
        )
    )

    assert resultado.estado_ciclo_vida == EstadoCicloVida.PRESTADO.value
    historial_repository_mock.registrar.assert_called_once()
    entrada = historial_repository_mock.registrar.call_args.args[0]
    assert entrada.campo == "estado_ciclo_vida"
    assert entrada.valor_anterior == "disponible"
    assert entrada.valor_nuevo == "prestado"


async def test_cambiar_estado_lanza_error_si_la_transicion_es_invalida(
    activo_repository_mock, historial_repository_mock
):
    activo_repository_mock.obtener_por_id.return_value = _activo(EstadoCicloVida.DADO_DE_BAJA)
    service = CambiarEstadoActivoService(activo_repository_mock, historial_repository_mock)

    with pytest.raises(TransicionEstadoInvalidaError):
        await service.ejecutar(
            CambiarEstadoActivoDTO(
                id_activo="1",
                estado_nuevo=EstadoCicloVida.DISPONIBLE,
                actualizado_por_id="9",
                actualizado_por_nombre="Admin",
            )
        )

    activo_repository_mock.guardar.assert_not_called()
    historial_repository_mock.registrar.assert_not_called()


async def test_cambiar_estado_lanza_error_si_el_activo_no_existe(
    activo_repository_mock, historial_repository_mock
):
    activo_repository_mock.obtener_por_id.return_value = None
    service = CambiarEstadoActivoService(activo_repository_mock, historial_repository_mock)

    with pytest.raises(ActivoNoEncontradoError):
        await service.ejecutar(
            CambiarEstadoActivoDTO(
                id_activo="1",
                estado_nuevo=EstadoCicloVida.PRESTADO,
                actualizado_por_id="9",
                actualizado_por_nombre="Admin",
            )
        )
