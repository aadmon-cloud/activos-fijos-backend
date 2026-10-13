from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.actor_movimiento_dto import ActorMovimientoDTO
from modules.movimientos.application.services.ejecutar_baja_movimiento import (
    EjecutarBajaMovimientoService,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento as I,
)
from modules.movimientos.domain.entities import (
    EstadoMovimiento as E,
)
from modules.movimientos.domain.entities import TipoMovimiento
from modules.movimientos.domain.errors import (
    MovimientoNoEncontradoError,
    OperacionSobreActivoFallidaError,
    TransicionEstadoMovimientoInvalidaError,
)


def _dto() -> ActorMovimientoDTO:
    return ActorMovimientoDTO(id_movimiento="m1", actor_id="u7", actor_nombre="Admin")


def _baja(fabrica, **overrides):
    valores = dict(
        tipo=TipoMovimiento.BAJA,
        usuario_destino_id=None,
        estado=E.APROBADO,
        items=[fabrica.item(estado=I.PENDIENTE_ADMIN)],
    )
    valores.update(overrides)
    return fabrica.movimiento(**valores)


def _servicio(fabrica, movimiento, cambia=True):
    repo = AsyncMock()
    repo.obtener_por_id.return_value = movimiento
    repo.guardar.side_effect = lambda m: m
    activo_movimiento = AsyncMock()
    activo_movimiento.cambiar_estado.return_value = cambia
    activo_movimiento.obtener_resumenes.return_value = {"a1": fabrica.resumen()}
    notificador = AsyncMock()

    return EjecutarBajaMovimientoService(repo, activo_movimiento, notificador), repo, activo_movimiento, notificador


async def test_ejecutar_la_baja_deja_el_activo_dado_de_baja(fabrica):
    service, repo, activo_movimiento, notificador = _servicio(fabrica, _baja(fabrica))

    await service.ejecutar(_dto())

    activo_movimiento.cambiar_estado.assert_awaited_once_with("a1", "dado_de_baja", "u7", "Admin")
    guardado = repo.guardar.call_args.args[0]
    assert guardado.estado == E.EJECUTADO
    assert guardado.items[0].estado == I.EJECUTADO
    notificador.notificar.assert_awaited_once()


async def test_una_baja_sin_aprobar_no_se_ejecuta(fabrica):
    service, repo, _, _ = _servicio(fabrica, _baja(fabrica, estado=E.SOLICITADO))

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto())

    repo.guardar.assert_not_called()


async def test_un_prestamo_no_se_ejecuta_como_baja(fabrica):
    service, _, _, _ = _servicio(fabrica, fabrica.movimiento(estado=E.APROBADO))

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto())


async def test_si_falla_el_cambio_del_activo_no_se_guarda(fabrica):
    service, repo, _, _ = _servicio(fabrica, _baja(fabrica), cambia=False)

    with pytest.raises(OperacionSobreActivoFallidaError):
        await service.ejecutar(_dto())

    repo.guardar.assert_not_called()


async def test_un_movimiento_inexistente_falla(fabrica):
    service, repo, _, _ = _servicio(fabrica, _baja(fabrica))
    repo.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto())
