from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.mantenimientos.application.dto.eliminar_archivo_mantenimiento_dto import (
    EliminarArchivoMantenimientoDTO,
)
from modules.mantenimientos.application.dto.subir_archivo_mantenimiento_dto import (
    SubirArchivoMantenimientoDTO,
)
from modules.mantenimientos.application.services.eliminar_archivo_mantenimiento import (
    EliminarArchivoMantenimientoService,
)
from modules.mantenimientos.application.services.obtener_archivo_mantenimiento import (
    ObtenerArchivoMantenimientoService,
)
from modules.mantenimientos.application.services.subir_archivo_mantenimiento import (
    SubirArchivoMantenimientoService,
)
from modules.mantenimientos.domain.entities import (
    ArchivoMantenimiento,
    EstadoMantenimiento,
    Mantenimiento,
    TipoMantenimiento,
)
from modules.mantenimientos.domain.errors import (
    ArchivoDemasiadoGrandeError,
    ArchivoNoEncontradoError,
    ArchivoTipoNoPermitidoError,
    MantenimientoNoEncontradoError,
)
from shared.application.file_storage.ports import ArchivoAlmacenado
from shared.domain.entities.audit import AuditPersona

_PNG_VALIDO = b"\x89PNG\r\n\x1a\n" + b"0" * 10


def _mantenimiento(**overrides) -> Mantenimiento:
    valores = dict(
        id="1",
        activo_id="a1",
        solicitud_id=None,
        tipo=TipoMantenimiento.CORRECTIVO,
        tecnico_responsable_id="u1",
        fecha=datetime.now(UTC),
        observaciones=None,
        costo=None,
        documentos=[],
        evidencias=[],
        estado=EstadoMantenimiento.PROGRAMADO,
        frecuencia_dias=None,
        proxima_fecha_sugerida=None,
        alerta_enviada=False,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Mantenimiento(**valores)


# ---------------------------------------------------------------- subir


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _mantenimiento()
    mock.guardar.side_effect = lambda m: m
    return mock


@pytest.fixture
def almacen_mock():
    mock = AsyncMock()
    mock.guardar.return_value = "archivo-1"
    return mock


async def test_subir_documento_lo_agrega_a_documentos(repositorio_mock, almacen_mock):
    service = SubirArchivoMantenimientoService(repositorio_mock, almacen_mock)

    resultado = await service.ejecutar(
        SubirArchivoMantenimientoDTO(
            id_mantenimiento="1",
            nombre="factura.png",
            contenido=_PNG_VALIDO,
            categoria="documento",
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
        )
    )

    assert len(resultado.documentos) == 1
    assert resultado.documentos[0].archivo_id == "archivo-1"
    assert len(resultado.evidencias) == 0


async def test_subir_evidencia_la_agrega_a_evidencias(repositorio_mock, almacen_mock):
    service = SubirArchivoMantenimientoService(repositorio_mock, almacen_mock)

    resultado = await service.ejecutar(
        SubirArchivoMantenimientoDTO(
            id_mantenimiento="1",
            nombre="foto.png",
            contenido=_PNG_VALIDO,
            categoria="evidencia",
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
        )
    )

    assert len(resultado.evidencias) == 1
    assert len(resultado.documentos) == 0


async def test_subir_archivo_lanza_error_si_el_tipo_no_es_permitido(repositorio_mock, almacen_mock):
    service = SubirArchivoMantenimientoService(repositorio_mock, almacen_mock)

    with pytest.raises(ArchivoTipoNoPermitidoError):
        await service.ejecutar(
            SubirArchivoMantenimientoDTO(
                id_mantenimiento="1",
                nombre="archivo.txt",
                contenido=b"no es una imagen ni un pdf",
                categoria="documento",
                actualizado_por_id="9",
                actualizado_por_nombre="Admin",
            )
        )

    almacen_mock.guardar.assert_not_called()


async def test_subir_archivo_lanza_error_si_supera_el_tamano_maximo(repositorio_mock, almacen_mock):
    service = SubirArchivoMantenimientoService(repositorio_mock, almacen_mock)
    contenido_grande = _PNG_VALIDO + b"0" * (10 * 1024 * 1024)

    with pytest.raises(ArchivoDemasiadoGrandeError):
        await service.ejecutar(
            SubirArchivoMantenimientoDTO(
                id_mantenimiento="1",
                nombre="foto.png",
                contenido=contenido_grande,
                categoria="evidencia",
                actualizado_por_id="9",
                actualizado_por_nombre="Admin",
            )
        )


async def test_subir_archivo_lanza_error_si_el_mantenimiento_no_existe(
    repositorio_mock, almacen_mock
):
    repositorio_mock.obtener_por_id.return_value = None
    service = SubirArchivoMantenimientoService(repositorio_mock, almacen_mock)

    with pytest.raises(MantenimientoNoEncontradoError):
        await service.ejecutar(
            SubirArchivoMantenimientoDTO(
                id_mantenimiento="1",
                nombre="foto.png",
                contenido=_PNG_VALIDO,
                categoria="evidencia",
                actualizado_por_id="9",
                actualizado_por_nombre="Admin",
            )
        )


# ---------------------------------------------------------------- obtener


async def test_obtener_archivo_retorna_el_contenido_si_pertenece_al_mantenimiento():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _mantenimiento(
        evidencias=[ArchivoMantenimiento(archivo_id="f1", nombre="foto.png")]
    )
    almacen_mock = AsyncMock()
    almacen_mock.obtener.return_value = ArchivoAlmacenado(
        nombre="foto.png", tipo_mime="image/png", contenido=_PNG_VALIDO
    )
    service = ObtenerArchivoMantenimientoService(repositorio_mock, almacen_mock)

    resultado = await service.ejecutar("1", "f1")

    assert resultado.contenido == _PNG_VALIDO


async def test_obtener_archivo_lanza_error_si_el_archivo_no_pertenece_al_mantenimiento():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _mantenimiento()
    almacen_mock = AsyncMock()
    service = ObtenerArchivoMantenimientoService(repositorio_mock, almacen_mock)

    with pytest.raises(ArchivoNoEncontradoError):
        await service.ejecutar("1", "f1")

    almacen_mock.obtener.assert_not_called()


async def test_obtener_archivo_lanza_error_si_el_mantenimiento_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    almacen_mock = AsyncMock()
    service = ObtenerArchivoMantenimientoService(repositorio_mock, almacen_mock)

    with pytest.raises(MantenimientoNoEncontradoError):
        await service.ejecutar("1", "f1")


# ---------------------------------------------------------------- eliminar


async def test_eliminar_archivo_lo_quita_de_la_lista():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _mantenimiento(
        documentos=[ArchivoMantenimiento(archivo_id="f1", nombre="factura.pdf")]
    )
    repositorio_mock.guardar.side_effect = lambda m: m
    almacen_mock = AsyncMock()
    service = EliminarArchivoMantenimientoService(repositorio_mock, almacen_mock)

    resultado = await service.ejecutar(
        EliminarArchivoMantenimientoDTO(
            id_mantenimiento="1",
            archivo_id="f1",
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
        )
    )

    assert resultado.documentos == []
    almacen_mock.eliminar.assert_called_once_with("f1")


async def test_eliminar_archivo_lanza_error_si_no_pertenece_al_mantenimiento():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _mantenimiento()
    almacen_mock = AsyncMock()
    service = EliminarArchivoMantenimientoService(repositorio_mock, almacen_mock)

    with pytest.raises(ArchivoNoEncontradoError):
        await service.ejecutar(
            EliminarArchivoMantenimientoDTO(
                id_mantenimiento="1",
                archivo_id="f1",
                actualizado_por_id="9",
                actualizado_por_nombre="Admin",
            )
        )

    almacen_mock.eliminar.assert_not_called()
