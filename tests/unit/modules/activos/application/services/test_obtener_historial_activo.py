from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from modules.activos.application.services.obtener_historial_activo import (
    ObtenerHistorialActivoService,
)
from modules.activos.domain.entities import (
    Activo,
    EntradaHistorialActivo,
    EstadoCicloVida,
    TipoActivo,
)
from modules.activos.domain.errors import ActivoNoEncontradoError
from shared.domain.entities.audit import AuditPersona

_AUDIT = AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC))


def _activo() -> Activo:
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
        valor=Decimal("100"),
        fecha_adquisicion=datetime.now(UTC),
        complementos=[],
        observaciones=None,
        foto_url=None,
        ficha_tecnica_url=None,
        creado_por=_AUDIT,
        actualizado_por=None,
    )


async def test_obtener_historial_activo_retorna_las_entradas():
    activo_repository_mock = AsyncMock()
    activo_repository_mock.obtener_por_id.return_value = _activo()
    historial_repository_mock = AsyncMock()
    historial_repository_mock.listar_por_activo.return_value = [
        EntradaHistorialActivo(
            id="1",
            activo_id="1",
            campo="responsable_id",
            valor_anterior="u1",
            valor_nuevo="u2",
            modificado_por=_AUDIT,
        )
    ]
    service = ObtenerHistorialActivoService(activo_repository_mock, historial_repository_mock)

    resultado = await service.ejecutar("1")

    assert len(resultado) == 1
    assert resultado[0].campo == "responsable_id"


async def test_obtener_historial_activo_lanza_error_si_el_activo_no_existe():
    activo_repository_mock = AsyncMock()
    activo_repository_mock.obtener_por_id.return_value = None
    historial_repository_mock = AsyncMock()
    service = ObtenerHistorialActivoService(activo_repository_mock, historial_repository_mock)

    with pytest.raises(ActivoNoEncontradoError):
        await service.ejecutar("1")
