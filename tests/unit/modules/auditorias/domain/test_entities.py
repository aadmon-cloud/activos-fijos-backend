from dataclasses import replace
from datetime import UTC, datetime

from modules.auditorias.domain.entities import (
    Auditoria,
    EstadoAuditoria,
    ItemAuditoria,
    ResultadoVerificacion,
)
from shared.domain.entities.audit import AuditPersona


def _item(**overrides) -> ItemAuditoria:
    valores = dict(
        activo_id="a1",
        nombre="Laptop",
        numero_inventario="INV-1",
        tipo="activo_fijo",
        descripcion=None,
        serie=None,
        estado_ciclo_vida_al_inicio="disponible",
        resultado=None,
        observacion=None,
        verificado_en=None,
    )
    valores.update(overrides)
    return ItemAuditoria(**valores)


def test_item_auditoria_es_inmutable():
    item = _item()
    item_verificado = replace(item, resultado=ResultadoVerificacion.ENCONTRADO)

    assert item.resultado is None
    assert item_verificado.resultado == ResultadoVerificacion.ENCONTRADO


def test_auditoria_guarda_el_snapshot_de_items():
    auditoria = Auditoria(
        id=None,
        usuario_auditado_id="u1",
        estado=EstadoAuditoria.EN_PROGRESO,
        items=[_item(), _item(activo_id="a2")],
        fecha_cierre=None,
        pdf_archivo_id=None,
        detalle_error_notificacion=None,
        creado_por=AuditPersona(id_persona="admin-1", nombre="Admin", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )

    assert len(auditoria.items) == 2
    assert auditoria.estado == EstadoAuditoria.EN_PROGRESO
