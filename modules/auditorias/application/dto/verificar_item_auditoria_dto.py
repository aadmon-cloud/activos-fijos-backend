from dataclasses import dataclass

from modules.auditorias.domain.entities import ResultadoVerificacion


@dataclass
class VerificarItemAuditoriaDTO:
    id_auditoria: str
    activo_id: str
    resultado: ResultadoVerificacion
    observacion: str | None = None
