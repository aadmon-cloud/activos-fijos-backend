from dataclasses import dataclass
from datetime import datetime

from modules.auditorias.domain.entities import ItemAuditoria, ResultadoVerificacion


@dataclass
class ItemAuditoriaDTO:
    activo_id: str
    nombre: str
    numero_inventario: str
    tipo: str
    descripcion: str | None
    serie: str | None
    estado_ciclo_vida_al_inicio: str
    resultado: ResultadoVerificacion | None
    observacion: str | None
    verificado_en: datetime | None


def item_a_dto(item: ItemAuditoria) -> ItemAuditoriaDTO:
    return ItemAuditoriaDTO(
        activo_id=item.activo_id,
        nombre=item.nombre,
        numero_inventario=item.numero_inventario,
        tipo=item.tipo,
        descripcion=item.descripcion,
        serie=item.serie,
        estado_ciclo_vida_al_inicio=item.estado_ciclo_vida_al_inicio,
        resultado=item.resultado,
        observacion=item.observacion,
        verificado_en=item.verificado_en,
    )
