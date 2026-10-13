from dataclasses import dataclass

from modules.auditorias.application.dto.auditoria_con_nombres_dto import AuditoriaConNombresDTO


@dataclass
class ListadoAuditoriasDTO:
    items: list[AuditoriaConNombresDTO]
    total: int
    skip: int
    limit: int
