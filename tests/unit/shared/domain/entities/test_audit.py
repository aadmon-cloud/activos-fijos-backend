from datetime import UTC, datetime

from shared.domain.entities.audit import AuditPersona


def test_audit_persona_se_crea_con_los_campos_esperados():
    audit = AuditPersona(
        id_persona="1", nombre="Ana Garcia", fecha=datetime(2026, 1, 1, tzinfo=UTC)
    )

    assert audit.id_persona == "1"
    assert audit.nombre == "Ana Garcia"
    assert audit.fecha == datetime(2026, 1, 1, tzinfo=UTC)
