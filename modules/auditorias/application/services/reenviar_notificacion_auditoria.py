from modules.auditorias.application.dto.auditoria_dto import AuditoriaDTO, auditoria_a_dto
from modules.auditorias.application.ports.auditoria_repository import AuditoriaRepositoryPort
from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditadoPort
from modules.auditorias.application.services.envio_notificacion_pdf import enviar_pdf_auditoria
from modules.auditorias.domain.entities import EstadoAuditoria
from modules.auditorias.domain.errors import (
    AuditoriaNoEncontradaError,
    AuditoriaNoModificableError,
    PdfAuditoriaNoDisponibleError,
)
from shared.application.file_storage.ports import AlmacenArchivosPort
from shared.application.notifications.ports import NotificadorConAdjuntoPort


class ReenviarNotificacionAuditoriaService:
    def __init__(
        self,
        auditoria_repository: AuditoriaRepositoryPort,
        usuario_auditado: UsuarioAuditadoPort,
        almacen_archivos: AlmacenArchivosPort,
        notificador: NotificadorConAdjuntoPort,
    ):
        self._auditoria_repository = auditoria_repository
        self._usuario_auditado = usuario_auditado
        self._almacen_archivos = almacen_archivos
        self._notificador = notificador

    async def ejecutar(self, id_auditoria: str) -> AuditoriaDTO:
        auditoria = await self._auditoria_repository.obtener_por_id(id_auditoria)
        if auditoria is None:
            raise AuditoriaNoEncontradaError(id_auditoria)
        if auditoria.estado == EstadoAuditoria.EN_PROGRESO:
            raise AuditoriaNoModificableError(id_auditoria)
        if auditoria.pdf_archivo_id is None:
            raise PdfAuditoriaNoDisponibleError(id_auditoria)

        usuario = await self._usuario_auditado.obtener(auditoria.usuario_auditado_id)

        auditoria_actualizada = await enviar_pdf_auditoria(
            auditoria,
            usuario,
            self._usuario_auditado,
            self._almacen_archivos,
            self._notificador,
            asunto=f"Auditoria de activos y elementos - {usuario.nombre_completo if usuario else ''}",
            cuerpo=(
                "Reenvio del reporte de auditoria de activos y elementos.\n\n"
                f"ID de auditoria: {auditoria.id}\n"
                "Se adjunta el reporte completo en formato PDF."
            ),
        )
        auditoria_guardada = await self._auditoria_repository.guardar(auditoria_actualizada)
        return auditoria_a_dto(auditoria_guardada)
