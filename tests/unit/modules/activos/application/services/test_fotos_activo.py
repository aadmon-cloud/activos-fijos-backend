from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.activos.application.dto.foto_dto import EliminarFotoActivoDTO, SubirFotoActivoDTO
from modules.activos.application.ports.almacen_fotos import FotoAlmacenada
from modules.activos.application.services.eliminar_foto_activo import EliminarFotoActivoService
from modules.activos.application.services.obtener_foto_activo import ObtenerFotoActivoService
from modules.activos.application.services.subir_foto_activo import SubirFotoActivoService
from modules.activos.domain.entities import Activo, EstadoCicloVida, TipoActivo
from modules.activos.domain.errors import (
    ActivoNoEncontradoError,
    FotoDemasiadoGrandeError,
    FotoNoEncontradaError,
    FotoTipoNoPermitidoError,
)
from modules.activos.domain.fotos import TAMANO_MAXIMO_FOTO_BYTES
from shared.domain.entities.audit import AuditPersona

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100


def _activo(foto_url: str | None = None) -> Activo:
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
        estado_ciclo_vida=EstadoCicloVida.DISPONIBLE,
        sede_id="s1",
        lugar_id="l1",
        complementos=[],
        observaciones=None,
        foto_url=foto_url,
        ficha_tecnica_url=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


def _dto(contenido: bytes = JPEG) -> SubirFotoActivoDTO:
    return SubirFotoActivoDTO(
        id_activo="1", contenido=contenido, actualizado_por_id="9", actualizado_por_nombre="Admin"
    )


@pytest.fixture
def repositorio():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _activo()
    return mock


@pytest.fixture
def almacen():
    return AsyncMock()


async def test_subir_foto_guarda_en_el_almacen_con_el_tipo_detectado_y_apunta_el_activo(
    repositorio, almacen
):
    await SubirFotoActivoService(repositorio, almacen).ejecutar(_dto())

    almacen.guardar.assert_awaited_once_with("1", JPEG, "image/jpeg")
    guardado = repositorio.guardar.call_args.args[0]
    assert guardado.foto_url == "/api/activos/1/foto"
    assert guardado.actualizado_por.id_persona == "9"


async def test_subir_foto_lanza_error_si_el_activo_no_existe(repositorio, almacen):
    repositorio.obtener_por_id.return_value = None

    with pytest.raises(ActivoNoEncontradoError):
        await SubirFotoActivoService(repositorio, almacen).ejecutar(_dto())

    almacen.guardar.assert_not_called()


@pytest.mark.parametrize(
    "contenido", [b"", b"<svg onload='alert(1)'/>", b"%PDF-1.7", b"texto cualquiera"]
)
async def test_subir_foto_rechaza_lo_que_no_es_una_imagen_permitida(
    repositorio, almacen, contenido
):
    with pytest.raises(FotoTipoNoPermitidoError):
        await SubirFotoActivoService(repositorio, almacen).ejecutar(_dto(contenido))

    almacen.guardar.assert_not_called()
    repositorio.guardar.assert_not_called()


async def test_subir_foto_rechaza_una_imagen_mas_grande_que_el_maximo(repositorio, almacen):
    grande = b"\xff\xd8\xff" + b"\x00" * TAMANO_MAXIMO_FOTO_BYTES

    with pytest.raises(FotoDemasiadoGrandeError):
        await SubirFotoActivoService(repositorio, almacen).ejecutar(_dto(grande))

    almacen.guardar.assert_not_called()


async def test_subir_foto_acepta_una_imagen_de_exactamente_el_maximo(repositorio, almacen):
    justa = b"\xff\xd8\xff" + b"\x00" * (TAMANO_MAXIMO_FOTO_BYTES - 3)

    await SubirFotoActivoService(repositorio, almacen).ejecutar(_dto(justa))

    almacen.guardar.assert_awaited_once()


async def test_obtener_foto_devuelve_la_foto_del_almacen(almacen):
    almacen.obtener.return_value = FotoAlmacenada(contenido=JPEG, tipo_mime="image/jpeg")

    foto = await ObtenerFotoActivoService(almacen).ejecutar("1")

    assert foto.tipo_mime == "image/jpeg"


async def test_obtener_foto_lanza_error_si_no_hay(almacen):
    almacen.obtener.return_value = None

    with pytest.raises(FotoNoEncontradaError):
        await ObtenerFotoActivoService(almacen).ejecutar("1")


async def test_eliminar_foto_borra_del_almacen_y_limpia_el_activo(repositorio, almacen):
    repositorio.obtener_por_id.return_value = _activo(foto_url="/api/activos/1/foto")

    await EliminarFotoActivoService(repositorio, almacen).ejecutar(
        EliminarFotoActivoDTO(id_activo="1", actualizado_por_id="9", actualizado_por_nombre="Admin")
    )

    almacen.eliminar.assert_awaited_once_with("1")
    assert repositorio.guardar.call_args.args[0].foto_url is None


async def test_eliminar_foto_de_un_activo_sin_foto_no_reescribe_el_activo(repositorio, almacen):
    await EliminarFotoActivoService(repositorio, almacen).ejecutar(
        EliminarFotoActivoDTO(id_activo="1", actualizado_por_id="9", actualizado_por_nombre="Admin")
    )

    repositorio.guardar.assert_not_called()


async def test_eliminar_foto_lanza_error_si_el_activo_no_existe(repositorio, almacen):
    repositorio.obtener_por_id.return_value = None

    with pytest.raises(ActivoNoEncontradoError):
        await EliminarFotoActivoService(repositorio, almacen).ejecutar(
            EliminarFotoActivoDTO(
                id_activo="1", actualizado_por_id="9", actualizado_por_nombre="Admin"
            )
        )

    almacen.eliminar.assert_not_called()
