from modules.auditorias.application.dto.auditoria_con_nombres_dto import (
    AuditoriaConNombresDTO,
    auditoria_con_nombres_a_dto,
)
from modules.auditorias.application.dto.auditoria_dto import auditoria_a_dto
from modules.auditorias.application.ports.auditoria_repository import AuditoriaRepositoryPort
from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditadoPort
from modules.auditorias.domain.errors import AuditoriaNoEncontradaError


class ObtenerAuditoriaService:
    def __init__(
        self,
        auditoria_repository: AuditoriaRepositoryPort,
        usuario_auditado: UsuarioAuditadoPort,
    ):
        self._auditoria_repository = auditoria_repository
        self._usuario_auditado = usuario_auditado

    async def ejecutar(self, id_auditoria: str) -> AuditoriaConNombresDTO:
        auditoria = await self._auditoria_repository.obtener_por_id(id_auditoria)
        if auditoria is None:
            raise AuditoriaNoEncontradaError(id_auditoria)

        usuario = await self._usuario_auditado.obtener(auditoria.usuario_auditado_id)
        return auditoria_con_nombres_a_dto(auditoria_a_dto(auditoria), usuario)
