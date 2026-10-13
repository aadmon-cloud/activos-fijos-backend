from dataclasses import dataclass, fields

from modules.auditorias.application.dto.auditoria_dto import AuditoriaDTO
from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditado


@dataclass
class AuditoriaConNombresDTO(AuditoriaDTO):
    usuario_nombre: str | None
    usuario_identificacion: str | None
    usuario_email: str | None


def auditoria_con_nombres_a_dto(
    auditoria: AuditoriaDTO, usuario: UsuarioAuditado | None
) -> AuditoriaConNombresDTO:
    base = {campo.name: getattr(auditoria, campo.name) for campo in fields(AuditoriaDTO)}
    return AuditoriaConNombresDTO(
        **base,
        usuario_nombre=usuario.nombre_completo if usuario else None,
        usuario_identificacion=usuario.identificacion if usuario else None,
        usuario_email=usuario.email if usuario else None,
    )
