from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.mantenimientos.application.ports.resolutor_nombres_port import (
    ActivoNombre,
    NombresReferenciasMantenimiento,
)
from modules.mantenimientos.application.services.obtener_mantenimiento import (
    ObtenerMantenimientoService,
)
from modules.mantenimientos.domain.entities import EstadoMantenimiento, Mantenimiento, TipoMantenimiento
from modules.mantenimientos.domain.errors import MantenimientoNoEncontradoError
from shared.domain.entities.audit import AuditPersona


def _mantenimiento(estado=EstadoMantenimiento.PROGRAMADO) -> Mantenimiento:
    return Mantenimiento(
        id="1",
        activo_id="a1",
        solicitud_id=None,
        tipo=TipoMantenimiento.PREVENTIVO,
        tecnico_responsable_id="u1",
        fecha=datetime.now(UTC),
        observaciones=None,
        costo=None,
        documentos=[],
        evidencias=[],
        estado=estado,
        frecuencia_dias=None,
        proxima_fecha_sugerida=None,
        alerta_enviada=False,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


def _resolutor():
    mock = AsyncMock()
    mock.resolver.return_value = NombresReferenciasMantenimiento(
        activos={"a1": ActivoNombre(nombre="Laptop", numero_inventario="INV-1")},
        tecnicos={"u1": "Tecnico Uno"},
    )
    return mock


async def test_obtener_mantenimiento_retorna_el_dto_con_nombres_si_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _mantenimiento()
    resolutor = _resolutor()
    service = ObtenerMantenimientoService(repositorio_mock, resolutor)

    resultado = await service.ejecutar("1")

    assert resultado.activo_id == "a1"
    assert resultado.activo_nombre == "Laptop"
    assert resultado.activo_numero_inventario == "INV-1"
    assert resultado.tecnico_nombre == "Tecnico Uno"
    assert resultado.creado_por_nombre == "S"
    assert resultado.alerta_enviada is False
    referencias = resolutor.resolver.call_args.args[0]
    assert referencias.activo_ids == {"a1"}
    assert referencias.tecnico_ids == {"u1"}


@pytest.mark.parametrize(
    ("estado", "esperados"),
    [
        (EstadoMantenimiento.PROGRAMADO, ["en_proceso", "cancelado"]),
        (EstadoMantenimiento.EN_PROCESO, ["completado", "cancelado"]),
        (EstadoMantenimiento.COMPLETADO, []),
        (EstadoMantenimiento.CANCELADO, []),
    ],
)
async def test_obtener_informa_los_estados_a_los_que_puede_pasar(estado, esperados):
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _mantenimiento(estado)
    service = ObtenerMantenimientoService(repositorio_mock, _resolutor())

    resultado = await service.ejecutar("1")

    assert resultado.estados_permitidos == esperados


async def test_obtener_mantenimiento_lanza_error_si_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    resolutor = _resolutor()
    service = ObtenerMantenimientoService(repositorio_mock, resolutor)

    with pytest.raises(MantenimientoNoEncontradoError):
        await service.ejecutar("1")

    resolutor.resolver.assert_not_called()
