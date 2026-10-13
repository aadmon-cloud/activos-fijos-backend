from dataclasses import replace
from datetime import UTC, datetime

from modules.activos.application.dto.foto_dto import SubirFotoActivoDTO
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.almacen_fotos import AlmacenFotosPort
from modules.activos.domain.errors import (
    ActivoNoEncontradoError,
    FotoDemasiadoGrandeError,
    FotoTipoNoPermitidoError,
)
from modules.activos.domain.fotos import TAMANO_MAXIMO_FOTO_BYTES, detectar_tipo_imagen, ruta_foto
from shared.domain.entities.audit import AuditPersona


class SubirFotoActivoService:
    def __init__(self, activo_repository: ActivoRepositoryPort, almacen_fotos: AlmacenFotosPort):
        self._activo_repository = activo_repository
        self._almacen_fotos = almacen_fotos

    async def ejecutar(self, dto: SubirFotoActivoDTO) -> None:
        activo = await self._activo_repository.obtener_por_id(dto.id_activo)
        if activo is None:
            raise ActivoNoEncontradoError(dto.id_activo)

        if len(dto.contenido) > TAMANO_MAXIMO_FOTO_BYTES:
            raise FotoDemasiadoGrandeError()

        tipo_mime = detectar_tipo_imagen(dto.contenido)
        if tipo_mime is None:
            raise FotoTipoNoPermitidoError()

        await self._almacen_fotos.guardar(dto.id_activo, dto.contenido, tipo_mime)

        await self._activo_repository.guardar(
            replace(
                activo,
                foto_url=ruta_foto(dto.id_activo),
                actualizado_por=AuditPersona(
                    id_persona=dto.actualizado_por_id,
                    nombre=dto.actualizado_por_nombre,
                    fecha=datetime.now(UTC),
                ),
            )
        )
