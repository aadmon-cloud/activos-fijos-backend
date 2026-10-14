from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.chequeo_movimiento_dto import ChequearItemDTO
from modules.movimientos.application.services.chequear_item_movimiento import (
    ChequearItemMovimientoService,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento as I,
)
from modules.movimientos.domain.entities import (
    EstadoMovimiento as E,
)
from modules.movimientos.domain.entities import ResultadoChequeo as R
from modules.movimientos.domain.errors import (
    ActivoNoPerteneceAlMovimientoError,
    ChequeoNoDisponibleError,
    MovimientoNoEncontradoError,
    ObservacionDeNovedadObligatoriaError,
)

ADMIN = "administrador_general"


def _dto(resultado=R.ENCONTRADO, observacion=None, activo_id="a1", actor_id="u7", rol=ADMIN) -> ChequearItemDTO:
    return ChequearItemDTO(
        id_movimiento="m1",
        activo_id=activo_id,
        resultado=resultado,
        observacion=observacion,
        actor_id=actor_id,
        actor_nombre="Admin",
        actor_rol=rol,
    )


def _servicio(fabrica, estado_item=I.PENDIENTE_ADMIN, **item):
    movimiento = fabrica.movimiento(
        items=[fabrica.item(activo_id="a1", estado=estado_item, **item)],
        usuario_destino_id="u2",
        estado=E.APROBADO_RESPONSABLE,
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = movimiento
    repo.guardar.side_effect = lambda m: m
    activo_movimiento = AsyncMock()
    activo_movimiento.obtener_resumenes.return_value = {"a1": fabrica.resumen(responsable_id="u1")}

    return ChequearItemMovimientoService(repo, activo_movimiento), repo


async def test_un_activo_que_espera_la_salida_se_chequea_para_la_salida(fabrica):
    service, repo = _servicio(fabrica)

    dto = await service.ejecutar(_dto(R.CON_NOVEDAD, "  Falta el cable  "))

    guardado = repo.guardar.call_args.args[0]
    chequeo = guardado.item("a1").chequeo_salida
    assert (chequeo.resultado, chequeo.observacion, chequeo.por.id_persona) == (R.CON_NOVEDAD, "Falta el cable", "u7")
    assert guardado.item("a1").chequeo_ingreso is None
    assert dto.items[0].chequeo_salida.por_nombre == "Admin"
    assert guardado.actualizado_por.id_persona == "u7"


@pytest.mark.parametrize("estado", [I.EN_CURSO, I.DEVOLUCION_SOLICITADA])
async def test_un_activo_que_esta_fuera_se_chequea_para_el_ingreso(fabrica, estado):
    service, repo = _servicio(fabrica, estado)

    await service.ejecutar(_dto(R.NO_ENCONTRADO))

    guardado = repo.guardar.call_args.args[0]
    assert guardado.item("a1").chequeo_ingreso.resultado == R.NO_ENCONTRADO
    assert guardado.item("a1").chequeo_salida is None


async def test_el_chequeo_se_puede_corregir(fabrica):
    service, repo = _servicio(fabrica, chequeo_salida=fabrica.chequeo(R.NO_ENCONTRADO))

    await service.ejecutar(_dto(R.ENCONTRADO))

    assert repo.guardar.call_args.args[0].item("a1").chequeo_salida.resultado == R.ENCONTRADO


async def test_con_novedad_exige_la_observacion(fabrica):
    service, repo = _servicio(fabrica)

    with pytest.raises(ObservacionDeNovedadObligatoriaError):
        await service.ejecutar(_dto(R.CON_NOVEDAD, "   "))

    repo.guardar.assert_not_called()


async def test_no_encontrado_no_exige_observacion_y_la_vacia_queda_sin_texto(fabrica):
    service, repo = _servicio(fabrica)

    await service.ejecutar(_dto(R.NO_ENCONTRADO, "  "))

    assert repo.guardar.call_args.args[0].item("a1").chequeo_salida.observacion is None


@pytest.mark.parametrize("estado", [I.PENDIENTE_RESPONSABLE, I.RECHAZADO, I.DEVUELTO])
async def test_un_activo_fuera_de_una_fase_de_chequeo_no_se_chequea(fabrica, estado):
    service, repo = _servicio(fabrica, estado)

    with pytest.raises(ChequeoNoDisponibleError):
        await service.ejecutar(_dto())

    repo.guardar.assert_not_called()


async def test_quien_no_es_administrador_no_chequea(fabrica):
    service, _ = _servicio(fabrica)

    with pytest.raises(MovimientoNoEncontradoError):
        # Un ajeno ni siquiera ve el movimiento.
        await service.ejecutar(_dto(actor_id="u9", rol="empleado"))

    with pytest.raises(ChequeoNoDisponibleError):
        # Quien lo ve (el responsable del activo) tampoco puede chequear.
        await service.ejecutar(_dto(actor_id="u1", rol="empleado"))


async def test_un_activo_ajeno_al_movimiento_se_rechaza(fabrica):
    service, _ = _servicio(fabrica)

    with pytest.raises(ActivoNoPerteneceAlMovimientoError):
        await service.ejecutar(_dto(activo_id="zzz"))


async def test_un_movimiento_inexistente_falla(fabrica):
    service, repo = _servicio(fabrica)
    repo.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto())
