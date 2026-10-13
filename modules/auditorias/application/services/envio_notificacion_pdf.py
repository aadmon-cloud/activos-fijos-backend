from dataclasses import replace

from modules.auditorias.application.ports.usuario_auditado_port import (
    UsuarioAuditado,
    UsuarioAuditadoPort,
)
from modules.auditorias.domain.entities import Auditoria, EstadoAuditoria
from shared.application.file_storage.ports import AlmacenArchivosPort
from shared.application.notifications.ports import AdjuntoCorreo, NotificadorConAdjuntoPort

_NOMBRE_PDF = "auditoria.pdf"
_DETALLE_ERROR_MAXIMO = 300


async def enviar_pdf_auditoria(
    auditoria: Auditoria,
    usuario: UsuarioAuditado | None,
    usuario_auditado: UsuarioAuditadoPort,
    almacen_archivos: AlmacenArchivosPort,
    notificador: NotificadorConAdjuntoPort,
    asunto: str,
    cuerpo: str,
) -> Auditoria:
    """Intenta enviar el PDF ya generado a el usuario auditado y al auditor.

    Nunca lanza: retorna la auditoria con estado NOTIFICADA si tuvo exito, o
    ERROR_NOTIFICACION (con el detalle) si algo fallo. El estado FINALIZADA de la auditoria
    ya quedo guardado antes de llamar esto, asi que un fallo aqui nunca revierte el cierre.
    """
    try:
        if usuario is None:
            raise RuntimeError("El usuario auditado ya no existe.")
        if auditoria.pdf_archivo_id is None:
            raise RuntimeError("La auditoria no tiene un PDF generado.")

        auditor_info = await usuario_auditado.obtener(auditoria.creado_por.id_persona)
        destinatarios = [u.email for u in (usuario, auditor_info) if u is not None]
        if not destinatarios:
            raise RuntimeError("No se encontraron destinatarios validos para el correo.")

        archivo_pdf = await almacen_archivos.obtener(auditoria.pdf_archivo_id)
        if archivo_pdf is None:
            raise RuntimeError("El PDF generado ya no esta disponible.")

        await notificador.enviar(
            destinatarios=destinatarios,
            asunto=asunto,
            cuerpo=cuerpo,
            adjuntos=[
                AdjuntoCorreo(
                    nombre=_NOMBRE_PDF,
                    contenido=archivo_pdf.contenido,
                    tipo_mime="application/pdf",
                )
            ],
        )
    except Exception as exc:
        return replace(
            auditoria, estado=EstadoAuditoria.ERROR_NOTIFICACION,
            detalle_error_notificacion=str(exc)[:_DETALLE_ERROR_MAXIMO],
        )

    return replace(auditoria, estado=EstadoAuditoria.NOTIFICADA, detalle_error_notificacion=None)
