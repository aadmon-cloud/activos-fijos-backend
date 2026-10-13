from bson import ObjectId
from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from shared.application.file_storage.ports import AlmacenArchivosPort, ArchivoAlmacenado
from shared.infrastructure.persistence.mongo.database import mongo_manager

_CLAVE_TIPO_MIME = "tipo_mime"


class MongoAlmacenArchivosGridFS(AlmacenArchivosPort):
    """Adaptador generico de GridFS: un bucket por modulo consumidor (`bucket_name`),
    muchos archivos por propietario, cada uno con su propio id de GridFS."""

    def __init__(self, bucket_name: str):
        self._bucket_name = bucket_name

    def _bucket(self) -> AsyncIOMotorGridFSBucket:
        return AsyncIOMotorGridFSBucket(mongo_manager.get_database(), bucket_name=self._bucket_name)

    async def guardar(self, propietario_id: str, nombre: str, contenido: bytes, tipo_mime: str) -> str:
        bucket = self._bucket()
        id_archivo = await bucket.upload_from_stream(
            nombre,
            contenido,
            metadata={_CLAVE_TIPO_MIME: tipo_mime, "propietario_id": propietario_id},
        )
        return str(id_archivo)

    async def obtener(self, archivo_id: str) -> ArchivoAlmacenado | None:
        bucket = self._bucket()
        try:
            flujo = await bucket.open_download_stream(ObjectId(archivo_id))
        except NoFile:
            return None

        contenido = await flujo.read()
        metadata = flujo.metadata or {}
        return ArchivoAlmacenado(
            nombre=flujo.filename,
            tipo_mime=metadata.get(_CLAVE_TIPO_MIME, "application/octet-stream"),
            contenido=contenido,
        )

    async def eliminar(self, archivo_id: str) -> None:
        bucket = self._bucket()
        try:
            await bucket.delete(ObjectId(archivo_id))
        except NoFile:
            pass
