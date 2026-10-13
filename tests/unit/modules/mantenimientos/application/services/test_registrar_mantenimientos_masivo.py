from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from modules.mantenimientos.application.dto.crear_mantenimientos_masivo_dto import (
    CrearMantenimientosMasivoDTO,
)
from modules.mantenimientos.application.services.registrar_mantenimientos_masivo import (
    LIMITE_CODIGOS_MASIVO,
    RegistrarMantenimientosMasivoService,
)
from modules.mantenimientos.domain.entities import EstadoMantenimiento, TipoMantenimiento
from modules.mantenimientos.domain.errors import (
    CodigosMasivosVaciosError,
    DemasiadosCodigosMasivosError,
    TecnicoInvalidoError,
)


def _dto(**overrides) -> CrearMantenimientosMasivoDTO:
    valores = dict(
        codigos=["INV-1", "INV-2"],
        tipo=TipoMantenimiento.PREVENTIVO,
        tecnico_responsable_id="u1",
        fecha=datetime(2026, 1, 1, tzinfo=UTC),
        creado_por_id="9",
        creado_por_nombre="Admin",
    )
    valores.update(overrides)

    return CrearMantenimientosMasivoDTO(**valores)


def _servicio(activos_por_codigo=None, tecnico_valido=True):
    repo = AsyncMock()

    async def guardar_varios(mantenimientos):
        from dataclasses import replace

        return [replace(m, id=f"m{i}") for i, m in enumerate(mantenimientos, start=1)]

    repo.guardar_varios.side_effect = guardar_varios
    buscador = AsyncMock()
    buscador.buscar_por_codigo.return_value = (
        {"INV-1": "a1", "INV-2": "a2"} if activos_por_codigo is None else activos_por_codigo
    )
    verificador = AsyncMock()
    verificador.tiene_rol_mantenimiento.return_value = tecnico_valido

    return RegistrarMantenimientosMasivoService(repo, buscador, verificador), repo, buscador


async def test_registra_un_mantenimiento_completado_por_cada_codigo_existente():
    service, repo, _ = _servicio()

    resultado = await service.ejecutar(_dto(observaciones="Limpieza general", costo=Decimal("5000")))

    assert [(r.codigo, r.activo_id, r.mantenimiento_id) for r in resultado.registrados] == [
        ("INV-1", "a1", "m1"),
        ("INV-2", "a2", "m2"),
    ]
    assert resultado.no_encontrados == []
    guardados = repo.guardar_varios.call_args.args[0]
    assert {m.estado for m in guardados} == {EstadoMantenimiento.COMPLETADO}
    assert {m.observaciones for m in guardados} == {"Limpieza general"}
    assert {m.costo for m in guardados} == {Decimal("5000")}
    assert {m.creado_por.nombre for m in guardados} == {"Admin"}
    assert all(m.solicitud_id is None for m in guardados)


async def test_informa_los_codigos_que_no_existen_y_registra_el_resto():
    service, repo, _ = _servicio(activos_por_codigo={"INV-1": "a1"})

    resultado = await service.ejecutar(_dto(codigos=["INV-1", "NO-EXISTE", "TAMBIEN-NO"]))

    assert [r.codigo for r in resultado.registrados] == ["INV-1"]
    assert resultado.no_encontrados == ["NO-EXISTE", "TAMBIEN-NO"]
    assert len(repo.guardar_varios.call_args.args[0]) == 1


async def test_si_ningun_codigo_existe_no_guarda_nada():
    service, repo, _ = _servicio(activos_por_codigo={})

    resultado = await service.ejecutar(_dto(codigos=["X", "Y"]))

    assert resultado.registrados == []
    assert resultado.no_encontrados == ["X", "Y"]
    repo.guardar_varios.assert_not_called()


async def test_normaliza_los_codigos_quita_espacios_vacios_y_repetidos():
    service, _, buscador = _servicio()

    await service.ejecutar(_dto(codigos=["  INV-1 ", "", "INV-2", "INV-1", "   "]))

    buscador.buscar_por_codigo.assert_awaited_once_with(["INV-1", "INV-2"])


async def test_los_codigos_se_buscan_en_mayusculas_como_los_guarda_activos():
    service, _, buscador = _servicio()

    resultado = await service.ejecutar(_dto(codigos=["inv-1", " Inv-2", "INV-1"]))

    buscador.buscar_por_codigo.assert_awaited_once_with(["INV-1", "INV-2"])
    assert [r.codigo for r in resultado.registrados] == ["INV-1", "INV-2"]


async def test_con_frecuencia_calcula_la_proxima_fecha_de_cada_uno():
    service, repo, _ = _servicio()

    await service.ejecutar(_dto(frecuencia_dias=90))

    guardados = repo.guardar_varios.call_args.args[0]
    assert {m.proxima_fecha_sugerida for m in guardados} == {datetime(2026, 4, 1, tzinfo=UTC)}
    assert {m.frecuencia_dias for m in guardados} == {90}


@pytest.mark.parametrize("codigos", [[], ["", "  "]])
async def test_sin_codigos_falla(codigos):
    service, repo, buscador = _servicio()

    with pytest.raises(CodigosMasivosVaciosError):
        await service.ejecutar(_dto(codigos=codigos))

    buscador.buscar_por_codigo.assert_not_called()
    repo.guardar_varios.assert_not_called()


async def test_mas_codigos_que_el_limite_falla():
    service, repo, _ = _servicio()
    codigos = [f"INV-{i}" for i in range(LIMITE_CODIGOS_MASIVO + 1)]

    with pytest.raises(DemasiadosCodigosMasivosError):
        await service.ejecutar(_dto(codigos=codigos))

    repo.guardar_varios.assert_not_called()


async def test_los_repetidos_no_cuentan_para_el_limite():
    service, _, buscador = _servicio(activos_por_codigo={})

    await service.ejecutar(_dto(codigos=["INV-1"] * (LIMITE_CODIGOS_MASIVO + 50)))

    buscador.buscar_por_codigo.assert_awaited_once_with(["INV-1"])


async def test_un_tecnico_sin_el_rol_falla_sin_buscar_ni_guardar():
    service, repo, buscador = _servicio(tecnico_valido=False)

    with pytest.raises(TecnicoInvalidoError):
        await service.ejecutar(_dto())

    buscador.buscar_por_codigo.assert_not_called()
    repo.guardar_varios.assert_not_called()
