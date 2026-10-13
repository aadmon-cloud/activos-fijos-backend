from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from modules.activos.application.ports.resolutor_nombres import (
    CondicionResuelta,
    NombresReferencias,
)
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
    resolutor_mock = AsyncMock()
    resolutor_mock.resolver.return_value = NombresReferencias(
        responsables={"u1": "Ana Gomez", "u2": "Luis Perez"}
    )
    service = ObtenerHistorialActivoService(
        activo_repository_mock, historial_repository_mock, resolutor_mock
    )

    resultado = await service.ejecutar("1")

    assert len(resultado) == 1
    assert resultado[0].campo == "responsable_id"
    assert resultado[0].valor_anterior == "u1"
    assert resultado[0].valor_anterior_nombre == "Ana Gomez"
    assert resultado[0].valor_nuevo_nombre == "Luis Perez"


async def test_obtener_historial_activo_lanza_error_si_el_activo_no_existe():
    activo_repository_mock = AsyncMock()
    activo_repository_mock.obtener_por_id.return_value = None
    historial_repository_mock = AsyncMock()
    service = ObtenerHistorialActivoService(
        activo_repository_mock, historial_repository_mock, AsyncMock()
    )

    with pytest.raises(ActivoNoEncontradoError):
        await service.ejecutar("1")


async def test_el_historial_de_estado_no_resuelve_nombres_y_solo_consulta_las_referencias_presentes():
    activo_repository_mock = AsyncMock()
    activo_repository_mock.obtener_por_id.return_value = _activo()
    historial_repository_mock = AsyncMock()
    historial_repository_mock.listar_por_activo.return_value = [
        EntradaHistorialActivo(
            id="1",
            activo_id="1",
            campo="estado_ciclo_vida",
            valor_anterior="disponible",
            valor_nuevo="prestado",
            modificado_por=_AUDIT,
        ),
        EntradaHistorialActivo(
            id="2",
            activo_id="1",
            campo="condicion_id",
            valor_anterior="cond1",
            valor_nuevo="cond2",
            modificado_por=_AUDIT,
        ),
    ]
    resolutor_mock = AsyncMock()
    resolutor_mock.resolver.return_value = NombresReferencias(
        condiciones={"cond1": CondicionResuelta(nombre="Bueno", color="#4CAF50")}
    )
    service = ObtenerHistorialActivoService(
        activo_repository_mock, historial_repository_mock, resolutor_mock
    )

    resultado = await service.ejecutar("1")

    referencias = resolutor_mock.resolver.call_args.args[0]
    assert referencias.condicion_ids == {"cond1", "cond2"}
    assert referencias.responsable_ids == set()
    assert resultado[0].valor_nuevo_nombre is None
    assert resultado[1].valor_anterior_nombre == "Bueno"
    assert resultado[1].valor_nuevo_nombre is None


async def test_un_historial_vacio_no_consulta_nombres():
    activo_repository_mock = AsyncMock()
    activo_repository_mock.obtener_por_id.return_value = _activo()
    historial_repository_mock = AsyncMock()
    historial_repository_mock.listar_por_activo.return_value = []
    resolutor_mock = AsyncMock()
    service = ObtenerHistorialActivoService(
        activo_repository_mock, historial_repository_mock, resolutor_mock
    )

    assert await service.ejecutar("1") == []
    resolutor_mock.resolver.assert_not_called()


async def test_una_nota_se_devuelve_sin_campo_ni_valores_y_no_consulta_referencias():
    activo_repository_mock = AsyncMock()
    activo_repository_mock.obtener_por_id.return_value = _activo()
    historial_repository_mock = AsyncMock()
    historial_repository_mock.listar_por_activo.return_value = [
        EntradaHistorialActivo(
            id="1",
            activo_id="1",
            tipo="nota",
            nota="Pantalla rayada",
            auditoria_id="au1",
            modificado_por=_AUDIT,
        )
    ]
    resolutor_mock = AsyncMock()
    resolutor_mock.resolver.return_value = NombresReferencias()
    service = ObtenerHistorialActivoService(
        activo_repository_mock, historial_repository_mock, resolutor_mock
    )

    resultado = await service.ejecutar("1")

    assert resultado[0].tipo == "nota"
    assert resultado[0].nota == "Pantalla rayada"
    assert resultado[0].campo is None
    assert resultado[0].valor_anterior_nombre is None
    referencias = resolutor_mock.resolver.call_args.args[0]
    assert referencias.responsable_ids == set()
    assert referencias.condicion_ids == set()

