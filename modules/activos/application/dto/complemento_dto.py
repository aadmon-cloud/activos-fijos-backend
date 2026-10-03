from dataclasses import dataclass

from modules.activos.domain.entities import Complemento


@dataclass
class ComplementoDTO:
    nombre: str
    descripcion: str | None
    cantidad: int
    serie: str | None


def complemento_a_dto(complemento: Complemento) -> ComplementoDTO:
    return ComplementoDTO(
        nombre=complemento.nombre,
        descripcion=complemento.descripcion,
        cantidad=complemento.cantidad,
        serie=complemento.serie,
    )


def dto_a_complemento(dto: ComplementoDTO) -> Complemento:
    return Complemento(
        nombre=dto.nombre,
        descripcion=dto.descripcion,
        cantidad=dto.cantidad,
        serie=dto.serie,
    )
