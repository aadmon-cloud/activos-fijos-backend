from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.chequeo_movimiento_dto import ObtenerActaDTO
from modules.movimientos.application.services.obtener_acta_movimiento import (
    ObtenerActaMovimientoService,
)
from modules.movimientos.domain.errors import ActaNoEncontradaError, MovimientoNoEncontradoError
from shared.application.file_storage.ports import ArchivoAlmacenado


def _dto(actor_id="u1", rol="empleado", acta_id="acta-1") -> ObtenerActaDTO:
    return ObtenerActaDTO(id_movimiento="m1", acta_id=acta_id, actor_id=actor_id, actor_rol=rol)


def _servicio(fabrica, archivo=None, **acta):
    repo = AsyncMock()
    repo.obtener_por_id.return_value = fabrica.movimiento(actas=[fabrica.acta(**acta)])
    almacen = AsyncMock()
    almacen.obtener.return_value = archivo
    activo_movimiento = AsyncMock()
    activo_movimiento.obtener_resumenes.return_value = {"a1": fabrica.resumen()}

    return ObtenerActaMovimientoService(repo, almacen, activo_movimiento), repo, almacen


def _archivo() -> ArchivoAlmacenado:
    return ArchivoAlmacenado(contenido=b"%PDF", tipo_mime="application/pdf", nombre="acta-salida-1.pdf")


async def test_entrega_el_pdf_del_acta_a_quien_ve_el_movimiento(fabrica):
    service, _, almacen = _servicio(fabrica, _archivo())

    archivo = await service.ejecutar(_dto("u1"))

    assert archivo.contenido == b"%PDF"
    almacen.obtener.assert_awaited_once_with("archivo-1")


async def test_el_administrador_tambien_la_descarga(fabrica):
    service, _, _ = _servicio(fabrica, _archivo())

    assert (await service.ejecutar(_dto("u9", "administrador_general"))).contenido == b"%PDF"


async def test_quien_no_ve_el_movimiento_recibe_no_encontrado(fabrica):
    service, _, _ = _servicio(fabrica, _archivo())

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto("u9"))


async def test_un_acta_inexistente_falla(fabrica):
    service, _, _ = _servicio(fabrica, _archivo())

    with pytest.raises(ActaNoEncontradaError):
        await service.ejecutar(_dto(acta_id="nada"))


async def test_un_acta_sin_archivo_o_con_archivo_perdido_falla(fabrica):
    sin_archivo, _, _ = _servicio(fabrica, _archivo(), archivo_id=None)
    perdido, _, _ = _servicio(fabrica, None)

    with pytest.raises(ActaNoEncontradaError):
        await sin_archivo.ejecutar(_dto())
    with pytest.raises(ActaNoEncontradaError):
        await perdido.ejecutar(_dto())


async def test_un_movimiento_inexistente_falla(fabrica):
    service, repo, _ = _servicio(fabrica, _archivo())
    repo.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto())
