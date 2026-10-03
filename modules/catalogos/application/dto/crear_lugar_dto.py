from dataclasses import dataclass

from modules.catalogos.domain.entities import TipoLugar


@dataclass
class CrearLugarDTO:
    nombre: str
    tipo: TipoLugar
    sede_id: str
    creado_por_id: str
    creado_por_nombre: str
