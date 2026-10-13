from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from modules.activos.application.ports.almacen_fotos import AlmacenFotosPort, FotoAlmacenada
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_BUCKET = "activos_fotos"
_CLAVE_TIPO_MIME = "tipo_mime"


class MongoAlmacenFotos(AlmacenFotosPort):
    """Guarda las fotos en GridFS (MongoDB): sin infraestructura adicional y siempre privadas,
    porque solo se sirven por un endpoint autenticado. El nombre del archivo es el id del activo."""

    def _bucket(self) -> AsyncIOMotorGridFSBucket:
        return AsyncIOMotorGridFSBucket(mongo_manager.get_database(), bucket_name=_NOMBRE_BUCKET)

    async def guardar(self, activo_id: str, contenido: bytes, tipo_mime: str) -> None:
        bucket = self._bucket()

        # Se sube la nueva primero: si falla, la foto anterior no se pierde.
        id_nuevo = await bucket.upload_from_stream(
            activo_id, contenido, metadata={_CLAVE_TIPO_MIME: tipo_mime}
        )
        async for anterior in bucket.find({"filename": activo_id}):
            if anterior._id != id_nuevo:
                await bucket.delete(anterior._id)

    async def obtener(self, activo_id: str) -> FotoAlmacenada | None:
        bucket = self._bucket()

        archivos = await bucket.find({"filename": activo_id}).sort("uploadDate", -1).limit(1).to_list(1)
        if not archivos:
            return None

        # `to_list` devuelve documentos (dict); en cambio `async for` devuelve objetos GridOut.
        flujo = await bucket.open_download_stream(archivos[0]["_id"])
        contenido = await flujo.read()

        return FotoAlmacenada(
            contenido=contenido,
            tipo_mime=(flujo.metadata or {}).get(_CLAVE_TIPO_MIME, "application/octet-stream"),
        )

    async def eliminar(self, activo_id: str) -> None:
        bucket = self._bucket()

        async for archivo in bucket.find({"filename": activo_id}):
            await bucket.delete(archivo._id)
