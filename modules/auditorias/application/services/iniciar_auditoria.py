from datetime import UTC, datetime

from modules.auditorias.application.dto.auditoria_dto import AuditoriaDTO, auditoria_a_dto
from modules.auditorias.application.dto.iniciar_auditoria_dto import IniciarAuditoriaDTO
from modules.auditorias.application.ports.activos_asignados_port import ActivosAsignadosPort
from modules.auditorias.application.ports.auditoria_repository import AuditoriaRepositoryPort
from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditadoPort
from modules.auditorias.domain.entities import Auditoria, EstadoAuditoria, ItemAuditoria
from modules.auditorias.domain.errors import UsuarioNoEncontradoParaAuditoriaError
from shared.domain.entities.audit import AuditPersona


class IniciarAuditoriaService:
    def __init__(
        self,
        auditoria_repository: AuditoriaRepositoryPort,
        usuario_auditado: UsuarioAuditadoPort,
        activos_asignados: ActivosAsignadosPort,
    ):
        self._auditoria_repository = auditoria_repository
        self._usuario_auditado = usuario_auditado
        self._activos_asignados = activos_asignados

    async def ejecutar(self, dto: IniciarAuditoriaDTO) -> AuditoriaDTO:
        usuario = await self._usuario_auditado.obtener(dto.usuario_auditado_id)
        if usuario is None:
            raise UsuarioNoEncontradoParaAuditoriaError(dto.usuario_auditado_id)

        activos = await self._activos_asignados.listar_por_responsable(dto.usuario_auditado_id)

        items = [
            ItemAuditoria(
                activo_id=activo.id,
                nombre=activo.nombre,
                numero_inventario=activo.numero_inventario,
                tipo=activo.tipo,
                descripcion=activo.descripcion,
                serie=activo.serie,
                estado_ciclo_vida_al_inicio=activo.estado_ciclo_vida,
                resultado=None,
                observacion=None,
                verificado_en=None,
            )
            for activo in activos
        ]

        auditoria = Auditoria(
            id=None,
            usuario_auditado_id=dto.usuario_auditado_id,
            estado=EstadoAuditoria.EN_PROGRESO,
            items=items,
            fecha_cierre=None,
            pdf_archivo_id=None,
            detalle_error_notificacion=None,
            creado_por=AuditPersona(
                id_persona=dto.auditor_id, nombre=dto.auditor_nombre, fecha=datetime.now(UTC)
            ),
            actualizado_por=None,
        )

        auditoria_guardada = await self._auditoria_repository.guardar(auditoria)
        return auditoria_a_dto(auditoria_guardada)
