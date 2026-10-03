from datetime import UTC, datetime

from modules.catalogos.application.dto.crear_lugar_dto import CrearLugarDTO
from modules.catalogos.application.dto.lugar_dto import LugarDTO, lugar_a_dto
from modules.catalogos.application.ports.lugar_repository import LugarRepositoryPort
from modules.catalogos.application.ports.sede_repository import SedeRepositoryPort
from modules.catalogos.domain.entities import Lugar
from modules.catalogos.domain.errors import LugarNombreDuplicadoError, SedeNoEncontradaError
from shared.domain.entities.audit import AuditPersona


class CrearLugarService:
    def __init__(
        self, lugar_repository: LugarRepositoryPort, sede_repository: SedeRepositoryPort
    ):
        self._lugar_repository = lugar_repository
        self._sede_repository = sede_repository

    async def ejecutar(self, dto: CrearLugarDTO) -> LugarDTO:
        if await self._sede_repository.obtener_por_id(dto.sede_id) is None:
            raise SedeNoEncontradaError(dto.sede_id)

        nombre = dto.nombre.strip()

        if await self._lugar_repository.obtener_por_nombre_y_sede(dto.sede_id, nombre) is not None:
            raise LugarNombreDuplicadoError(nombre)

        lugar = Lugar(
            id=None,
            nombre=nombre,
            tipo=dto.tipo,
            sede_id=dto.sede_id,
            creado_por=AuditPersona(
                id_persona=dto.creado_por_id,
                nombre=dto.creado_por_nombre,
                fecha=datetime.now(UTC),
            ),
            actualizado_por=None,
        )

        lugar_guardado = await self._lugar_repository.guardar(lugar)
        return lugar_a_dto(lugar_guardado)
