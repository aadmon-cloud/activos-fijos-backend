from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from modules.activos.application.dto.complemento_dto import ComplementoDTO
from modules.activos.application.dto.crear_activo_dto import CrearActivoDTO
from modules.activos.application.services.crear_activo import CrearActivoService
from modules.activos.domain.entities import Activo, EstadoCicloVida, TipoActivo
from modules.activos.domain.errors import (
    ActivoNumeroInventarioDuplicadoError,
    ActivoValorInvalidoError,
    ComplementoCantidadInvalidaError,
)
from shared.domain.entities.audit import AuditPersona


def _dto(**overrides) -> CrearActivoDTO:
    valores = dict(
        nombre="Laptop Dell",
        numero_inventario="  inv-001  ",
        tipo=TipoActivo.ACTIVO_FIJO,
        categoria_id="c1",
        area_id="a1",
        responsable_id="u1",
        condicion_id="cond1",
        sede_id="s1",
        lugar_id="l1",
        valor=Decimal("1500000"),
        fecha_adquisicion=datetime(2026, 1, 1, tzinfo=UTC),
        creado_por_id="9",
        creado_por_nombre="Admin",
    )
    valores.update(overrides)
    return CrearActivoDTO(**valores)


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_numero_inventario.return_value = None
    mock.guardar.side_effect = lambda activo: Activo(
        id="1",
        nombre=activo.nombre,
        numero_inventario=activo.numero_inventario,
        tipo=activo.tipo,
        marca=activo.marca,
        modelo=activo.modelo,
        serie=activo.serie,
        descripcion=activo.descripcion,
        categoria_id=activo.categoria_id,
        area_id=activo.area_id,
        responsable_id=activo.responsable_id,
        condicion_id=activo.condicion_id,
        estado_ciclo_vida=activo.estado_ciclo_vida,
        sede_id=activo.sede_id,
        lugar_id=activo.lugar_id,
        valor=activo.valor,
        fecha_adquisicion=activo.fecha_adquisicion,
        complementos=activo.complementos,
        observaciones=activo.observaciones,
        foto_url=activo.foto_url,
        ficha_tecnica_url=activo.ficha_tecnica_url,
        creado_por=activo.creado_por,
        actualizado_por=activo.actualizado_por,
    )
    return mock


async def test_crear_activo_normaliza_el_numero_de_inventario(repositorio_mock):
    service = CrearActivoService(repositorio_mock)

    resultado = await service.ejecutar(_dto())

    assert resultado.numero_inventario == "INV-001"
    assert resultado.estado_ciclo_vida == EstadoCicloVida.DISPONIBLE.value


async def test_crear_activo_lanza_error_si_el_valor_no_es_positivo(repositorio_mock):
    service = CrearActivoService(repositorio_mock)

    with pytest.raises(ActivoValorInvalidoError):
        await service.ejecutar(_dto(valor=Decimal("0")))

    repositorio_mock.guardar.assert_not_called()


async def test_crear_activo_lanza_error_si_un_complemento_tiene_cantidad_invalida(
    repositorio_mock,
):
    service = CrearActivoService(repositorio_mock)

    with pytest.raises(ComplementoCantidadInvalidaError):
        await service.ejecutar(
            _dto(
                complementos=[
                    ComplementoDTO(nombre="Cargador", descripcion=None, cantidad=0, serie=None)
                ]
            )
        )

    repositorio_mock.guardar.assert_not_called()


async def test_crear_activo_lanza_error_si_el_numero_de_inventario_ya_existe(repositorio_mock):
    repositorio_mock.obtener_por_numero_inventario.return_value = Activo(
        id="9",
        nombre="X",
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
        valor=Decimal("1"),
        fecha_adquisicion=datetime.now(UTC),
        complementos=[],
        observaciones=None,
        foto_url=None,
        ficha_tecnica_url=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    service = CrearActivoService(repositorio_mock)

    with pytest.raises(ActivoNumeroInventarioDuplicadoError):
        await service.ejecutar(_dto())

    repositorio_mock.guardar.assert_not_called()
