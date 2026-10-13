from dataclasses import replace
from datetime import UTC, datetime

from modules.mantenimientos.application.dto.eliminar_archivo_mantenimiento_dto import (
    EliminarArchivoMantenimientoDTO,
)
from modules.mantenimientos.application.dto.mantenimiento_dto import (
    MantenimientoDTO,
    mantenimiento_a_dto,
)
from modules.mantenimientos.application.ports.mantenimiento_repository import (
    MantenimientoRepositoryPort,
)
from modules.mantenimientos.domain.errors import (
    ArchivoNoEncontradoError,
    MantenimientoNoEncontradoError,
)
from shared.application.file_storage.ports import AlmacenArchivosPort
from shared.domain.entities.audit import AuditPersona


class EliminarArchivoMantenimientoService:
    def __init__(
        self,
        mantenimiento_repository: MantenimientoRepositoryPort,
        almacen_archivos: AlmacenArchivosPort,
    ):
        self._mantenimiento_repository = mantenimiento_repository
        self._almacen_archivos = almacen_archivos

    async def ejecutar(self, dto: EliminarArchivoMantenimientoDTO) -> MantenimientoDTO:
        mantenimiento = await self._mantenimiento_repository.obtener_por_id(dto.id_mantenimiento)
        if mantenimiento is None:
            raise MantenimientoNoEncontradoError(dto.id_mantenimiento)

        ids_validos = {a.archivo_id for a in (*mantenimiento.documentos, *mantenimiento.evidencias)}
        if dto.archivo_id not in ids_validos:
            raise ArchivoNoEncontradoError(dto.archivo_id)

        await self._almacen_archivos.eliminar(dto.archivo_id)

        mantenimiento_actualizado = replace(
            mantenimiento,
            documentos=[a for a in mantenimiento.documentos if a.archivo_id != dto.archivo_id],
            evidencias=[a for a in mantenimiento.evidencias if a.archivo_id != dto.archivo_id],
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
