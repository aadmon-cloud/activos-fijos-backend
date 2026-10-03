from datetime import UTC, datetime

from modules.catalogos.application.dto.categoria_dto import CategoriaDTO, categoria_a_dto
from modules.catalogos.application.dto.crear_categoria_dto import CrearCategoriaDTO
from modules.catalogos.application.ports.categoria_repository import CategoriaRepositoryPort
from modules.catalogos.domain.entities import Categoria
from modules.catalogos.domain.errors import CategoriaNombreDuplicadaError
from shared.domain.entities.audit import AuditPersona


class CrearCategoriaService:
    def __init__(self, categoria_repository: CategoriaRepositoryPort):
        self._categoria_repository = categoria_repository

    async def ejecutar(self, dto: CrearCategoriaDTO) -> CategoriaDTO:
        nombre = dto.nombre.strip()

        if await self._categoria_repository.obtener_por_nombre(nombre) is not None:
            raise CategoriaNombreDuplicadaError(nombre)

        categoria = Categoria(
            id=None,
            nombre=nombre,
            descripcion=dto.descripcion,
            creado_por=AuditPersona(
                id_persona=dto.creado_por_id,
                nombre=dto.creado_por_nombre,
                fecha=datetime.now(UTC),
            ),
            actualizado_por=None,
        )

        categoria_guardada = await self._categoria_repository.guardar(categoria)
        return categoria_a_dto(categoria_guardada)
