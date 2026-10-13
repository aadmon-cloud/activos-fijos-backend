from datetime import UTC, datetime

from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditado
from modules.auditorias.domain.entities import (
    Auditoria,
    EstadoAuditoria,
    ItemAuditoria,
    ResultadoVerificacion,
)
from modules.auditorias.infrastructure.reportes.generador_reporte_pdf import GeneradorReportePdf
from shared.domain.entities.audit import AuditPersona


def _item(**overrides) -> ItemAuditoria:
    valores = dict(
        activo_id="a1",
        nombre="Laptop",
        numero_inventario="INV-1",
        tipo="activo_fijo",
        descripcion="Dell Latitude",
        serie="SN1",
        estado_ciclo_vida_al_inicio="disponible",
        resultado=ResultadoVerificacion.ENCONTRADO,
        observacion=None,
        verificado_en=datetime(2026, 1, 1, tzinfo=UTC),
    )
    valores.update(overrides)
    return ItemAuditoria(**valores)


def _auditoria(items) -> Auditoria:
    return Auditoria(
        id="aud-1",
        usuario_auditado_id="u1",
        estado=EstadoAuditoria.FINALIZADA,
        items=items,
        fecha_cierre=datetime(2026, 1, 2, tzinfo=UTC),
        pdf_archivo_id=None,
        detalle_error_notificacion=None,
        creado_por=AuditPersona(
            id_persona="admin-1", nombre="Admin", fecha=datetime(2026, 1, 1, tzinfo=UTC)
        ),
        actualizado_por=None,
    )


def _usuario() -> UsuarioAuditado:
    return UsuarioAuditado(
        id="u1", nombre_completo="Camilo Perez", identificacion="102425103", email="c@x.com", activo=True
    )


async def test_generar_pdf_retorna_bytes_de_un_pdf_valido():
    auditoria = _auditoria([_item()])

    contenido = await GeneradorReportePdf().generar_pdf(auditoria, _usuario())

    assert contenido.startswith(b"%PDF")
    assert len(contenido) > 0


async def test_generar_pdf_funciona_con_una_auditoria_sin_items():
    auditoria = _auditoria([])

    contenido = await GeneradorReportePdf().generar_pdf(auditoria, _usuario())

    assert contenido.startswith(b"%PDF")


async def test_generar_pdf_funciona_con_faltantes():
    auditoria = _auditoria(
        [
            _item(resultado=ResultadoVerificacion.ENCONTRADO),
            _item(
                activo_id="a2",
                resultado=ResultadoVerificacion.NO_ENCONTRADO,
                observacion="El usuario manifiesta que no lo tiene.",
            ),
        ]
    )

    contenido = await GeneradorReportePdf().generar_pdf(auditoria, _usuario())

    assert contenido.startswith(b"%PDF")
