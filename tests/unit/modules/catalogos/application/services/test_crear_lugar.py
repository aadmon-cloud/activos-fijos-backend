from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.dto.crear_lugar_dto import CrearLugarDTO
from modules.catalogos.application.services.crear_lugar import CrearLugarService
from modules.catalogos.domain.entities import Lugar, Sede, TipoLugar
from modules.catalogos.domain.errors import LugarNombreDuplicadoError, SedeNoEncontradaError
from shared.domain.entities.audit import AuditPersona

_AUDIT = AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC))


@pytest.fixture
def lugar_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_nombre_y_sede.return_value = None
    mock.guardar.side_effect = lambda lugar: Lugar(
        id="1",
        nombre=lugar.nombre,
        tipo=lugar.tipo,
        sede_id=lugar.sede_id,
        creado_por=lugar.creado_por,
        actualizado_por=lugar.actualizado_por,
    )
    return mock


@pytest.fixture
def sede_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = Sede(
        id="1", nombre="Prado", descripcion=None, creado_por=_AUDIT, actualizado_por=None
    )
    return mock


async def test_crear_lugar_guarda_la_entidad(lugar_repository_mock, sede_repository_mock):
    service = CrearLugarService(lugar_repository_mock, sede_repository_mock)

    resultado = await service.ejecutar(
        CrearLugarDTO(
            nombre="  Bodega  ",
            tipo=TipoLugar.BODEGA,
            sede_id="1",
            creado_por_id="1",
            creado_por_nombre="Admin",
        )
    )

    assert resultado.id == "1"
    assert resultado.nombre == "Bodega"
    assert resultado.tipo == "bodega"


async def test_crear_lugar_lanza_error_si_la_sede_no_existe(
    lugar_repository_mock, sede_repository_mock
):
    sede_repository_mock.obtener_por_id.return_value = None
    service = CrearLugarService(lugar_repository_mock, sede_repository_mock)

    with pytest.raises(SedeNoEncontradaError):
        await service.ejecutar(
            CrearLugarDTO(
                nombre="Bodega",
                tipo=TipoLugar.BODEGA,
                sede_id="1",
                creado_por_id="1",
                creado_por_nombre="Admin",
            )
        )

    lugar_repository_mock.guardar.assert_not_called()


async def test_crear_lugar_lanza_error_si_el_nombre_ya_existe_en_esa_sede(
    lugar_repository_mock, sede_repository_mock
):
    lugar_repository_mock.obtener_por_nombre_y_sede.return_value = Lugar(
        id="9", nombre="Bodega", tipo=TipoLugar.BODEGA, sede_id="1", creado_por=_AUDIT,
        actualizado_por=None,
    )
    service = CrearLugarService(lugar_repository_mock, sede_repository_mock)

    with pytest.raises(LugarNombreDuplicadoError):
        await service.ejecutar(
            CrearLugarDTO(
                nombre="Bodega",
                tipo=TipoLugar.BODEGA,
                sede_id="1",
                creado_por_id="1",
                creado_por_nombre="Admin",
            )
        )
