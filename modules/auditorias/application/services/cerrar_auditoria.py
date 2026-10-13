import logging
from dataclasses import replace
from datetime import UTC, datetime

from modules.auditorias.application.dto.auditoria_dto import AuditoriaDTO, auditoria_a_dto
from modules.auditorias.application.dto.cerrar_auditoria_dto import CerrarAuditoriaDTO
from modules.auditorias.application.ports.auditoria_repository import AuditoriaRepositoryPort
from modules.auditorias.application.ports.generador_reporte_port import GeneradorReportePort
from modules.auditorias.application.ports.historial_activo_nota_port import (
    HistorialActivoNotaPort,
)
from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditadoPort
from modules.auditorias.application.services.envio_notificacion_pdf import enviar_pdf_auditoria
from modules.auditorias.domain.entities import (
    Auditoria,
    EstadoAuditoria,
    ItemAuditoria,
    ResultadoVerificacion,
)
from modules.auditorias.domain.errors import AuditoriaNoEncontradaError, AuditoriaNoModificableError
from shared.application.file_storage.ports import AlmacenArchivosPort
from shared.application.notifications.ports import NotificadorConAdjuntoPort
from shared.domain.entities.audit import AuditPersona

logger = logging.getLogger(__name__)

_NOMBRE_PDF = "auditoria.pdf"


class CerrarAuditoriaService:
    def __init__(
        self,
        auditoria_repository: AuditoriaRepositoryPort,
        usuario_auditado: UsuarioAuditadoPort,
        historial_nota: HistorialActivoNotaPort,
        generador_reporte: GeneradorReportePort,
        almacen_archivos: AlmacenArchivosPort,
        notificador: NotificadorConAdjuntoPort,
    ):
        self._auditoria_repository = auditoria_repository
        self._usuario_auditado = usuario_auditado
        self._historial_nota = historial_nota
        self._generador_reporte = generador_reporte
        self._almacen_archivos = almacen_archivos
        self._notificador = notificador

    async def ejecutar(self, dto: CerrarAuditoriaDTO) -> AuditoriaDTO:
        auditoria = await self._auditoria_repository.obtener_por_id(dto.id_auditoria)
        if auditoria is None:
            raise AuditoriaNoEncontradaError(dto.id_auditoria)
        if auditoria.estado != EstadoAuditoria.EN_PROGRESO:
            raise AuditoriaNoModificableError(dto.id_auditoria)

        ahora = datetime.now(UTC)
        items_cerrados = [
            (
                replace(item, resultado=ResultadoVerificacion.NO_ENCONTRADO, verificado_en=ahora)
                if item.resultado is None
                else item
            )
            for item in auditoria.items
        ]
        actor = AuditPersona(id_persona=dto.actor_id, nombre=dto.actor_nombre, fecha=ahora)

        auditoria_finalizada = replace(
            auditoria,
            items=items_cerrados,
            estado=EstadoAuditoria.FINALIZADA,
            fecha_cierre=ahora,
            actualizado_por=actor,
        )
        # Escritura unica y atomica del documento: de aqui en adelante la auditoria queda
        # cerrada e inmutable sin importar lo que pase despues con el historial, el PDF o el
        # correo (ninguno de esos pasos puede revertir este guardado).
        auditoria_guardada = await self._auditoria_repository.guardar(auditoria_finalizada)

        await self._registrar_notas_historial(auditoria_guardada, actor)

        usuario = await self._usuario_auditado.obtener(auditoria_guardada.usuario_auditado_id)
        auditoria_con_pdf = await self._generar_y_guardar_pdf(auditoria_guardada, usuario)

        auditoria_final = await enviar_pdf_auditoria(
            auditoria_con_pdf,
            usuario,
            self._usuario_auditado,
            self._almacen_archivos,
            self._notificador,
            asunto=f"Auditoria de activos y elementos - {usuario.nombre_completo if usuario else ''}",
            cuerpo=_cuerpo_correo(auditoria_con_pdf, usuario),
        )
        auditoria_guardada_final = await self._auditoria_repository.guardar(auditoria_final)

        return auditoria_a_dto(auditoria_guardada_final)

    async def _registrar_notas_historial(self, auditoria: Auditoria, actor: AuditPersona) -> None:
        for item in auditoria.items:
            nota = _nota_para_resultado(item)
            try:
                await self._historial_nota.registrar_nota(item.activo_id, nota, auditoria.id, actor)
            except Exception:
                logger.exception(
                    "No se pudo registrar la nota de historial del activo '%s' (auditoria '%s').",
                    item.activo_id,
                    auditoria.id,
                )

    async def _generar_y_guardar_pdf(self, auditoria: Auditoria, usuario) -> Auditoria:
        if usuario is None:
            return auditoria
        try:
            contenido_pdf = await self._generador_reporte.generar_pdf(auditoria, usuario)
            archivo_id = await self._almacen_archivos.guardar(
                auditoria.id, _NOMBRE_PDF, contenido_pdf, "application/pdf"
            )
        except Exception:
            logger.exception(
                "No se pudo generar/guardar el PDF de la auditoria '%s'.", auditoria.id
            )
            return auditoria

        return replace(auditoria, pdf_archivo_id=archivo_id)


def _nota_para_resultado(item: ItemAuditoria) -> str:
    if item.resultado == ResultadoVerificacion.ENCONTRADO:
        nota = "Elemento verificado fisicamente durante auditoria. Resultado: Encontrado."
    elif item.resultado == ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD:
        nota = "Elemento verificado fisicamente durante auditoria. Resultado: Encontrado con novedad."
    else:
        nota = "Elemento reportado como no encontrado durante auditoria."

    if item.observacion:
        nota += f" Observacion: {item.observacion}"
    return nota


def _cuerpo_correo(auditoria: Auditoria, usuario) -> str:
    encontrados = sum(1 for i in auditoria.items if i.resultado == ResultadoVerificacion.ENCONTRADO)
    con_novedad = sum(
        1 for i in auditoria.items if i.resultado == ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD
    )
    no_encontrados = sum(
        1 for i in auditoria.items if i.resultado == ResultadoVerificacion.NO_ENCONTRADO
    )

    lineas = [
        "Auditoria de activos y elementos",
        "",
        f"Usuario auditado: {usuario.nombre_completo if usuario else '-'}",
        f"Auditor: {auditoria.creado_por.nombre}",
        f"Fecha: {auditoria.creado_por.fecha:%d/%m/%Y}",
        f"ID de auditoria: {auditoria.id}",
        "",
        "Resumen",
        f"Total auditado: {len(auditoria.items)}",
        f"Encontrados: {encontrados}",
        f"Encontrados con novedad: {con_novedad}",
        f"No encontrados: {no_encontrados}",
        "",
        "Se adjunta el reporte completo de la auditoria en formato PDF.",
    ]
    if no_encontrados == 0:
        lineas.append("La auditoria fue completada y no se registraron elementos faltantes.")

    return "\n".join(lineas)
