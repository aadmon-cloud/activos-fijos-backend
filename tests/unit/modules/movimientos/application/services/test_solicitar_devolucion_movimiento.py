from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.acciones_movimiento_dto import SolicitarDevolucionDTO
from modules.movimientos.application.services.solicitar_devolucion_movimiento import (
    SolicitarDevolucionMovimientoService,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento as I,
)
from modules.movimientos.domain.entities import (
    EstadoMovimiento as E,
)
from modules.movimientos.domain.errors import (
    MovimientoNoEncontradoError,
    PermisoAprobacionError,
    TransicionEstadoMovimientoInvalidaError,
)


def _dto(actor_id="u2", rol="empleado", activo_ids=None) -> SolicitarDevolucionDTO:
    return SolicitarDevolucionDTO(
        id_movimiento="m1", actor_id=actor_id, actor_nombre="Quien lo tiene", actor_rol=rol, activo_ids=activo_ids
    )


def _movimiento_en_curso(fabrica):
    return fabrica.movimiento(
        estado=E.EN_CURSO,
        usuario_destino_id="u2",
        items=[
            fabrica.item(activo_id="a1", estado=I.EN_CURSO),
            fabrica.item(activo_id="a2", estado=I.EN_CURSO),
        ],
    )


def _servicio(fabrica, movimiento):
    repo = AsyncMock()
    repo.obtener_por_id.return_value = movimiento
    repo.guardar.side_effect = lambda m: m
    activo_movimiento = AsyncMock()
    # Tras la salida, quien tiene los activos es su responsable actual.
    activo_movimiento.obtener_resumenes.return_value = {
        item.activo_id: fabrica.resumen(id=item.activo_id, responsable_id="u2", estado_ciclo_vida="prestado")
        for item in movimiento.items
    }
    notificador = AsyncMock()

    return SolicitarDevolucionMovimientoService(repo, activo_movimiento, notificador), repo, notificador


async def test_quien_tiene_los_activos_pide_devolverlos_todos(fabrica):
    service, repo, notificador = _servicio(fabrica, _movimiento_en_curso(fabrica))

    await service.ejecutar(_dto())

    guardado = repo.guardar.call_args.args[0]
    assert [i.estado for i in guardado.items] == [I.DEVOLUCION_SOLICITADA] * 2
    assert guardado.item("a1").devolucion_solicitada_por.id_persona == "u2"
    assert guardado.estado == E.EN_CURSO
    assert "rol:administrador_general" in notificador.notificar.await_args.kwargs["destinatarios"]


async def test_puede_pedir_devolver_solo_algunos(fabrica):
    service, repo, _ = _servicio(fabrica, _movimiento_en_curso(fabrica))

    await service.ejecutar(_dto(activo_ids=["a2"]))

    guardado = repo.guardar.call_args.args[0]
    assert guardado.item("a1").estado == I.EN_CURSO
    assert guardado.item("a2").estado == I.DEVOLUCION_SOLICITADA


async def test_el_responsable_original_no_puede_pedir_la_devolucion(fabrica):
    movimiento = _movimiento_en_curso(fabrica)
    service, repo, _ = _servicio(fabrica, movimiento)

    # u1 es el responsable original: ve el movimiento pero no tiene los activos.
    with pytest.raises(PermisoAprobacionError):
        await service.ejecutar(_dto("u1"))

    repo.guardar.assert_not_called()


async def test_el_administrador_que_no_tiene_los_activos_no_los_pide(fabrica):
    service, _, _ = _servicio(fabrica, _movimiento_en_curso(fabrica))

    with pytest.raises(PermisoAprobacionError):
        await service.ejecutar(_dto("u7", rol="administrador_general"))


async def test_no_se_pide_de_nuevo_lo_que_ya_se_pidio(fabrica):
    movimiento = fabrica.movimiento(
        estado=E.EN_CURSO,
        items=[fabrica.item(activo_id="a1", estado=I.DEVOLUCION_SOLICITADA)],
    )
    service, _, _ = _servicio(fabrica, movimiento)

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto())


async def test_un_movimiento_sin_activos_fuera_no_admite_devolucion(fabrica):
    service, _, _ = _servicio(fabrica, fabrica.movimiento())

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto("u1"))


async def test_quien_no_ve_el_movimiento_recibe_no_encontrado(fabrica):
    service, _, _ = _servicio(fabrica, _movimiento_en_curso(fabrica))

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto("u9"))
