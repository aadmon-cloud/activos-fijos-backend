from datetime import UTC, datetime

import pytest

from modules.movimientos.application.ports.activo_movimiento_port import ActivoResumenMovimiento
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    ItemMovimiento,
    Movimiento,
    TipoMovimiento,
)
from shared.domain.entities.audit import AuditPersona


class Fabrica:
    """Constructores de datos de prueba del modulo de movimientos."""

    @staticmethod
    def audit(id_persona: str = "u2", nombre: str = "Persona") -> AuditPersona:
        return AuditPersona(id_persona=id_persona, nombre=nombre, fecha=datetime.now(UTC))

    @staticmethod
    def item(**overrides) -> ItemMovimiento:
        valores = dict(
            activo_id="a1",
            responsable_original_id="u1",
            estado=EstadoItemMovimiento.PENDIENTE_RESPONSABLE,
        )
        valores.update(overrides)
        return ItemMovimiento(**valores)

    @classmethod
    def movimiento(cls, **overrides) -> Movimiento:
        valores = dict(
            id="m1",
            tipo=TipoMovimiento.PRESTAMO,
            items=[cls.item()],
            usuario_destino_id="u2",
            descripcion="Necesito el proyector",
            evento_nombre=None,
            fecha_salida_estimada=None,
            fecha_retorno_estimada=None,
            fecha_entrega_real=None,
            fecha_devolucion_real=None,
            estado=EstadoMovimiento.SOLICITADO,
            aprobado_por_admin=None,
            comprobante_archivo_id=None,
            creado_por=cls.audit("u2", "Destino"),
            actualizado_por=None,
        )
        valores.update(overrides)
        return Movimiento(**valores)

    @staticmethod
    def resumen(**overrides) -> ActivoResumenMovimiento:
        valores = dict(
            id="a1",
            responsable_id="u1",
            estado_ciclo_vida="disponible",
            nombre="Proyector",
            numero_inventario="INV-1",
        )
        valores.update(overrides)
        return ActivoResumenMovimiento(**valores)


@pytest.fixture
def fabrica() -> type[Fabrica]:
    return Fabrica
