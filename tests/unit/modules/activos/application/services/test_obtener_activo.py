from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from modules.activos.application.ports.resolutor_nombres import (
    CondicionResuelta,
    NombresReferencias,
)
from modules.activos.application.services.obtener_activo import ObtenerActivoService
from modules.activos.domain.entities import Activo, EstadoCicloVida, TipoActivo
from modules.activos.domain.errors import ActivoNoEncontradoError
from shared.domain.entities.audit import AuditPersona


async def test_obtener_activo_retorna_el_dto_si_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = Activo(
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
        foto_url=None,
        ficha_tecnica_url=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    resolutor_mock = AsyncMock()
    resolutor_mock.resolver.return_value = NombresReferencias(
        categorias={"c1": "Computo"},
        condiciones={"cond1": CondicionResuelta(nombre="Bueno", color="#4CAF50")},
    )
    service = ObtenerActivoService(repositorio_mock, resolutor_mock)

    resultado = await service.ejecutar("1")

    assert resultado.nombre == "Laptop"
    assert resultado.categoria_nombre == "Computo"
    assert resultado.condicion_color == "#4CAF50"
    assert resultado.area_nombre is None


async def test_obtener_activo_lanza_error_si_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    resolutor_mock = AsyncMock()
    service = ObtenerActivoService(repositorio_mock, resolutor_mock)

    with pytest.raises(ActivoNoEncontradoError):
        await service.ejecutar("1")
