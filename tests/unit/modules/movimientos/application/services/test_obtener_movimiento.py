from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.obtener_movimiento_dto import ObtenerMovimientoDTO
from modules.movimientos.application.ports.resolutor_nombres_port import (
    ActivoNombreMovimiento,
    NombresReferenciasMovimiento,
)
from modules.movimientos.application.services.obtener_movimiento import ObtenerMovimientoService
from modules.movimientos.domain.entities import EstadoItemMovimiento as I
from modules.movimientos.domain.errors import MovimientoNoEncontradoError


def _dto(actor_id="u1", rol="empleado") -> ObtenerMovimientoDTO:
    return ObtenerMovimientoDTO(id_movimiento="m1", actor_id=actor_id, actor_rol=rol)


def _servicio(movimiento):
    repo = AsyncMock()
    repo.obtener_por_id.return_value = movimiento
    resolutor = AsyncMock()
    resolutor.resolver.return_value = NombresReferenciasMovimiento(
        activos={"a1": ActivoNombreMovimiento("Proyector", "INV-1", responsable_id="u1")},
        usuarios={"u1": "Ana Uno", "u2": "Luis Dos"},
    )

    return ObtenerMovimientoService(repo, resolutor, AsyncMock())


async def test_devuelve_el_movimiento_con_nombres_y_acciones(fabrica):
    movimiento = fabrica.movimiento(items=[fabrica.item(estado=I.PENDIENTE_RESPONSABLE)])

    resultado = await _servicio(movimiento).ejecutar(_dto("u1"))

    assert resultado.items[0].activo_nombre == "Proyector"
    assert resultado.items[0].activo_numero_inventario == "INV-1"
    assert resultado.items[0].responsable_original_nombre == "Ana Uno"
    assert resultado.usuario_destino_nombre == "Luis Dos"
    assert resultado.items[0].acciones_permitidas == ["aprobar", "rechazar"]
    assert resultado.acciones_permitidas == ["aprobar", "rechazar"]


async def test_el_administrador_ve_cualquier_movimiento(fabrica):
    resultado = await _servicio(fabrica.movimiento()).ejecutar(_dto("u7", "administrador_general"))

    assert resultado.id == "m1"


async def test_quien_no_tiene_relacion_recibe_no_encontrado(fabrica):
    with pytest.raises(MovimientoNoEncontradoError):
        await _servicio(fabrica.movimiento()).ejecutar(_dto("u9"))


async def test_un_movimiento_inexistente_falla(fabrica):
    service = _servicio(fabrica.movimiento())
    service._movimiento_repository.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto())
