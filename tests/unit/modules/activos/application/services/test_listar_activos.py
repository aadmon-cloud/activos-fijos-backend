from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from modules.activos.application.dto.listar_activos_dto import ListarActivosDTO
from modules.activos.application.services.listar_activos import ListarActivosService
from modules.activos.domain.entities import Activo, EstadoCicloVida, TipoActivo
from shared.domain.entities.audit import AuditPersona


def _activo(id_: str) -> Activo:
    return Activo(
        id=id_,
        nombre="Laptop",
        numero_inventario=f"INV-{id_}",
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


async def test_listar_activos_retorna_los_dtos_del_repositorio():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar.return_value = [_activo("1"), _activo("2")]
    service = ListarActivosService(repositorio_mock)

    resultado = await service.ejecutar(ListarActivosDTO())

    assert len(resultado) == 2


async def test_listar_activos_limita_el_limit_maximo():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar.return_value = []
    service = ListarActivosService(repositorio_mock)

    await service.ejecutar(ListarActivosDTO(limit=5000))

    _, kwargs = repositorio_mock.listar.call_args
    assert kwargs["limit"] == 1000
