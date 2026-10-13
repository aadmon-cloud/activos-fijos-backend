from dataclasses import replace
from datetime import UTC, datetime

from modules.activos.application.dto.foto_dto import EliminarFotoActivoDTO
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.almacen_fotos import AlmacenFotosPort
from modules.activos.domain.errors import ActivoNoEncontradoError
from shared.domain.entities.audit import AuditPersona


class EliminarFotoActivoService:
    def __init__(self, activo_repository: ActivoRepositoryPort, almacen_fotos: AlmacenFotosPort):
        self._activo_repository = activo_repository
        self._almacen_fotos = almacen_fotos

    async def ejecutar(self, dto: EliminarFotoActivoDTO) -> None:
        activo = await self._activo_repository.obtener_por_id(dto.id_activo)
        if activo is None:
            raise ActivoNoEncontradoError(dto.id_activo)

        await self._almacen_fotos.eliminar(dto.id_activo)

        if activo.foto_url is not None:
            await self._activo_repository.guardar(
                replace(
                    activo,
                    foto_url=None,
                    actualizado_por=AuditPersona(
                        id_persona=dto.actualizado_por_id,
                        nombre=dto.actualizado_por_nombre,
                        fecha=datetime.now(UTC),
                    ),
                )
            )
