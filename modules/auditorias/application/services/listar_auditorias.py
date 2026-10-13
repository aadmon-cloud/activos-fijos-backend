from modules.auditorias.application.dto.auditoria_con_nombres_dto import (
    auditoria_con_nombres_a_dto,
)
from modules.auditorias.application.dto.auditoria_dto import auditoria_a_dto
from modules.auditorias.application.dto.listado_auditorias_dto import ListadoAuditoriasDTO
from modules.auditorias.application.dto.listar_auditorias_dto import ListarAuditoriasDTO
from modules.auditorias.application.ports.auditoria_repository import AuditoriaRepositoryPort
from modules.auditorias.application.ports.usuario_auditado_port import (
    UsuarioAuditado,
    UsuarioAuditadoPort,
)

_LIMITE_MAXIMO = 1000


class ListarAuditoriasService:
    def __init__(
        self,
        auditoria_repository: AuditoriaRepositoryPort,
        usuario_auditado: UsuarioAuditadoPort,
    ):
        self._auditoria_repository = auditoria_repository
        self._usuario_auditado = usuario_auditado

    async def ejecutar(self, dto: ListarAuditoriasDTO) -> ListadoAuditoriasDTO:
        limit = min(dto.limit, _LIMITE_MAXIMO)
        kwargs = dict(
            usuario_auditado_id=dto.usuario_auditado_id,
            estado=dto.estado,
            creado_por_id=dto.creado_por_id,
        )
        auditorias = await self._auditoria_repository.listar(**kwargs, skip=dto.skip, limit=limit)
        total = await self._auditoria_repository.contar(**kwargs)

        usuarios_cache: dict[str, UsuarioAuditado | None] = {}
        items = []
        for auditoria in auditorias:
            if auditoria.usuario_auditado_id not in usuarios_cache:
                usuarios_cache[auditoria.usuario_auditado_id] = await self._usuario_auditado.obtener(
                    auditoria.usuario_auditado_id
                )
            items.append(
                auditoria_con_nombres_a_dto(
                    auditoria_a_dto(auditoria), usuarios_cache[auditoria.usuario_auditado_id]
                )
            )

        return ListadoAuditoriasDTO(items=items, total=total, skip=dto.skip, limit=limit)
