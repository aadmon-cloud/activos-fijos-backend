from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.obtener_movimiento_dto import ObtenerMovimientoDTO
from modules.movimientos.application.services.obtener_comprobante_movimiento import (
    ObtenerComprobanteMovimientoService,
)
from modules.movimientos.domain.errors import (
    ComprobanteNoDisponibleError,
    MovimientoNoEncontradoError,
)
from shared.application.file_storage.ports import ArchivoAlmacenado


def _dto(actor_id="u1", rol="empleado") -> ObtenerMovimientoDTO:
    return ObtenerMovimientoDTO(id_movimiento="m1", actor_id=actor_id, actor_rol=rol)


def _servicio(fabrica, movimiento, archivo=None):
    repo = AsyncMock()
    repo.obtener_por_id.return_value = movimiento
    almacen = AsyncMock()
    almacen.obtener.return_value = archivo
    activo_movimiento = AsyncMock()
    activo_movimiento.obtener_resumenes.return_value = {"a1": fabrica.resumen()}

    return ObtenerComprobanteMovimientoService(repo, almacen, activo_movimiento), repo


def _archivo() -> ArchivoAlmacenado:
    return ArchivoAlmacenado(contenido=b"%PDF", tipo_mime="application/pdf", nombre="comprobante.pdf")


async def test_entrega_el_comprobante_a_quien_ve_el_movimiento(fabrica):
    service, _ = _servicio(fabrica, fabrica.movimiento(comprobante_archivo_id="f1"), _archivo())

    archivo = await service.ejecutar(_dto("u1"))

    assert archivo.contenido == b"%PDF"


async def test_quien_no_ve_el_movimiento_recibe_no_encontrado(fabrica):
    service, _ = _servicio(fabrica, fabrica.movimiento(comprobante_archivo_id="f1"), _archivo())

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto("u9"))


async def test_sin_comprobante_generado_falla(fabrica):
    service, _ = _servicio(fabrica, fabrica.movimiento(comprobante_archivo_id=None))

    with pytest.raises(ComprobanteNoDisponibleError):
        await service.ejecutar(_dto("u1"))


async def test_si_el_archivo_ya_no_existe_falla(fabrica):
    service, _ = _servicio(fabrica, fabrica.movimiento(comprobante_archivo_id="f1"), archivo=None)

    with pytest.raises(ComprobanteNoDisponibleError):
        await service.ejecutar(_dto("u1"))


async def test_un_movimiento_inexistente_falla(fabrica):
    service, repo = _servicio(fabrica, fabrica.movimiento())
    repo.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto())
