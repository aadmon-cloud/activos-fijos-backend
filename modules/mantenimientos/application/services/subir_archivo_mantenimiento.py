from dataclasses import replace
from datetime import UTC, datetime

from modules.mantenimientos.application.dto.mantenimiento_dto import (
    MantenimientoDTO,
    mantenimiento_a_dto,
)
from modules.mantenimientos.application.dto.subir_archivo_mantenimiento_dto import (
    SubirArchivoMantenimientoDTO,
)
from modules.mantenimientos.application.ports.mantenimiento_repository import (
    MantenimientoRepositoryPort,
)
from modules.mantenimientos.domain.entities import ArchivoMantenimiento
from modules.mantenimientos.domain.errors import (
    ArchivoDemasiadoGrandeError,
    ArchivoTipoNoPermitidoError,
    MantenimientoNoEncontradoError,
)
from shared.application.file_storage.ports import AlmacenArchivosPort
from shared.domain.archivos import detectar_tipo_archivo
from shared.domain.entities.audit import AuditPersona

TAMANO_MAXIMO_ARCHIVO_BYTES = 10 * 1024 * 1024


class SubirArchivoMantenimientoService:
    def __init__(
        self,
        mantenimiento_repository: MantenimientoRepositoryPort,
        almacen_archivos: AlmacenArchivosPort,
    ):
        self._mantenimiento_repository = mantenimiento_repository
        self._almacen_archivos = almacen_archivos

    async def ejecutar(self, dto: SubirArchivoMantenimientoDTO) -> MantenimientoDTO:
        mantenimiento = await self._mantenimiento_repository.obtener_por_id(dto.id_mantenimiento)
        if mantenimiento is None:
            raise MantenimientoNoEncontradoError(dto.id_mantenimiento)

        if len(dto.contenido) > TAMANO_MAXIMO_ARCHIVO_BYTES:
            raise ArchivoDemasiadoGrandeError()

        tipo_mime = detectar_tipo_archivo(dto.contenido)
        if tipo_mime is None:
            raise ArchivoTipoNoPermitidoError()

        archivo_id = await self._almacen_archivos.guardar(
            dto.id_mantenimiento, dto.nombre, dto.contenido, tipo_mime
        )
        archivo = ArchivoMantenimiento(archivo_id=archivo_id, nombre=dto.nombre)

        if dto.categoria == "documento":
            documentos = [*mantenimiento.documentos, archivo]
            evidencias = mantenimiento.evidencias
        else:
            documentos = mantenimiento.documentos
            evidencias = [*mantenimiento.evidencias, archivo]

        mantenimiento_actualizado = replace(
            mantenimiento,
            documentos=documentos,
            evidencias=evidencias,
            actualizado_por=AuditPersona(
                id_persona=dto.actualizado_por_id,
                nombre=dto.actualizado_por_nombre,
                fecha=datetime.now(UTC),
            ),
        )

        mantenimiento_guardado = await self._mantenimiento_repository.guardar(
            mantenimiento_actualizado
        )
        return mantenimiento_a_dto(mantenimiento_guardado)
