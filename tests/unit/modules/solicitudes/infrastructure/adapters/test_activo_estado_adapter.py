from unittest.mock import AsyncMock

import pytest

from modules.activos.application.dto.cambiar_estado_activo_dto import CambiarEstadoActivoDTO
from modules.activos.domain.entities import EstadoCicloVida
from modules.activos.domain.errors import ActivoNoEncontradoError, TransicionEstadoInvalidaError
from modules.solicitudes.infrastructure.adapters.activo_estado_adapter import ActivoEstadoAdapter


def _adaptador(activo=None, servicio=None):
    repositorio = AsyncMock()
    repositorio.obtener_por_id.return_value = activo

    return ActivoEstadoAdapter(repositorio, servicio or AsyncMock())


class _Activo:
    estado_ciclo_vida = EstadoCicloVida.PRESTADO


async def test_obtener_estado_devuelve_el_valor_del_ciclo_de_vida():
    assert await _adaptador(_Activo()).obtener_estado("a1") == "prestado"


async def test_obtener_estado_devuelve_none_si_el_activo_no_existe():
    assert await _adaptador(None).obtener_estado("a1") is None


async def test_cambiar_estado_delega_en_el_servicio_de_activos_y_confirma():
    servicio = AsyncMock()

    resultado = await _adaptador(servicio=servicio).cambiar_estado("a1", "en_mantenimiento", "u1", "Ana")

    assert resultado is True
    servicio.ejecutar.assert_awaited_once_with(
        CambiarEstadoActivoDTO(
            id_activo="a1",
            estado_nuevo=EstadoCicloVida.EN_MANTENIMIENTO,
            actualizado_por_id="u1",
            actualizado_por_nombre="Ana",
        )
    )


@pytest.mark.parametrize(
    "error",
    [TransicionEstadoInvalidaError("prestado", "en_mantenimiento"), ActivoNoEncontradoError("a1")],
)
async def test_cambiar_estado_devuelve_false_si_activos_lo_rechaza(error):
    servicio = AsyncMock()
    servicio.ejecutar.side_effect = error

    assert await _adaptador(servicio=servicio).cambiar_estado("a1", "en_mantenimiento", "u1", "Ana") is False


async def test_otros_errores_no_se_ocultan():
    servicio = AsyncMock()
    servicio.ejecutar.side_effect = RuntimeError("base de datos caida")

    with pytest.raises(RuntimeError):
        await _adaptador(servicio=servicio).cambiar_estado("a1", "en_mantenimiento", "u1", "Ana")
