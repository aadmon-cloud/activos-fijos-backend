from dataclasses import replace
from datetime import UTC, datetime

from modules.catalogos.application.dto.actualizar_lugar_dto import ActualizarLugarDTO
from modules.catalogos.application.dto.lugar_dto import LugarDTO, lugar_a_dto
from modules.catalogos.application.ports.lugar_repository import LugarRepositoryPort
from modules.catalogos.domain.errors import LugarNoEncontradoError, LugarNombreDuplicadoError
from shared.domain.entities.audit import AuditPersona


class ActualizarLugarService:
    def __init__(self, lugar_repository: LugarRepositoryPort):
        self._lugar_repository = lugar_repository

    async def ejecutar(self, dto: ActualizarLugarDTO) -> LugarDTO:
        lugar = await self._lugar_repository.obtener_por_id(dto.id_lugar)
        if lugar is None:
            raise LugarNoEncontradoError(dto.id_lugar)

        nombre_nuevo = dto.nombre.strip() if dto.nombre is not None else lugar.nombre
        if nombre_nuevo != lugar.nombre:
            existente = await self._lugar_repository.obtener_por_nombre_y_sede(
                lugar.sede_id, nombre_nuevo
            )
            if existente is not None and existente.id != lugar.id:
                raise LugarNombreDuplicadoError(nombre_nuevo)

        lugar_actualizado = replace(
            lugar,
            nombre=nombre_nuevo,
            tipo=dto.tipo if dto.tipo is not None else lugar.tipo,
            actualizado_por=AuditPersona(
                id_persona=dto.actualizado_por_id,
                nombre=dto.actualizado_por_nombre,
                fecha=datetime.now(UTC),
            ),
        )

        lugar_guardado = await self._lugar_repository.guardar(lugar_actualizado)
        return lugar_a_dto(lugar_guardado)
