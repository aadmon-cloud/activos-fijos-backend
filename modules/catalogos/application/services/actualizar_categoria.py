from dataclasses import replace
from datetime import UTC, datetime

from modules.catalogos.application.dto.actualizar_categoria_dto import ActualizarCategoriaDTO
from modules.catalogos.application.dto.categoria_dto import CategoriaDTO, categoria_a_dto
from modules.catalogos.application.ports.categoria_repository import CategoriaRepositoryPort
from modules.catalogos.domain.errors import (
    CategoriaNoEncontradaError,
    CategoriaNombreDuplicadaError,
)
from shared.domain.entities.audit import AuditPersona


class ActualizarCategoriaService:
    def __init__(self, categoria_repository: CategoriaRepositoryPort):
        self._categoria_repository = categoria_repository

    async def ejecutar(self, dto: ActualizarCategoriaDTO) -> CategoriaDTO:
        categoria = await self._categoria_repository.obtener_por_id(dto.id_categoria)
        if categoria is None:
            raise CategoriaNoEncontradaError(dto.id_categoria)

        nombre_nuevo = dto.nombre.strip() if dto.nombre is not None else categoria.nombre
        if nombre_nuevo != categoria.nombre:
            existente = await self._categoria_repository.obtener_por_nombre(nombre_nuevo)
            if existente is not None and existente.id != categoria.id:
                raise CategoriaNombreDuplicadaError(nombre_nuevo)

        categoria_actualizada = replace(
            categoria,
            nombre=nombre_nuevo,
            descripcion=(
                dto.descripcion if dto.descripcion is not None else categoria.descripcion
            ),
            actualizado_por=AuditPersona(
                id_persona=dto.actualizado_por_id,
                nombre=dto.actualizado_por_nombre,
                fecha=datetime.now(UTC),
            ),
        )

        categoria_guardada = await self._categoria_repository.guardar(categoria_actualizada)
        return categoria_a_dto(categoria_guardada)
