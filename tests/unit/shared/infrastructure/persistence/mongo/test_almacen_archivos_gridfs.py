from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId
from gridfs.errors import NoFile

from shared.infrastructure.persistence.mongo.almacen_archivos_gridfs import (
    MongoAlmacenArchivosGridFS,
)

_MODULO = "shared.infrastructure.persistence.mongo.almacen_archivos_gridfs"


def _con_bucket(bucket):
    return (
        patch(f"{_MODULO}.AsyncIOMotorGridFSBucket", return_value=bucket),
        patch(f"{_MODULO}.mongo_manager"),
    )


async def test_guardar_sube_el_archivo_con_metadata_y_retorna_el_id():
    id_nuevo = ObjectId()
    bucket = MagicMock()
    bucket.upload_from_stream = AsyncMock(return_value=id_nuevo)
    p_bucket, p_manager = _con_bucket(bucket)

    with p_bucket, p_manager:
        archivo_id = await MongoAlmacenArchivosGridFS("mi_bucket").guardar(
            "propietario-1", "factura.pdf", b"contenido", "application/pdf"
        )

    assert archivo_id == str(id_nuevo)
    bucket.upload_from_stream.assert_awaited_once_with(
        "factura.pdf",
        b"contenido",
        metadata={"tipo_mime": "application/pdf", "propietario_id": "propietario-1"},
    )


async def test_obtener_retorna_el_archivo_con_su_nombre_y_tipo():
    flujo = MagicMock()
    flujo.read = AsyncMock(return_value=b"contenido")
    flujo.filename = "factura.pdf"
    flujo.metadata = {"tipo_mime": "application/pdf"}
    bucket = MagicMock()
    bucket.open_download_stream = AsyncMock(return_value=flujo)
    p_bucket, p_manager = _con_bucket(bucket)

    with p_bucket, p_manager:
        archivo = await MongoAlmacenArchivosGridFS("mi_bucket").obtener(str(ObjectId()))

    assert archivo.contenido == b"contenido"
    assert archivo.nombre == "factura.pdf"
    assert archivo.tipo_mime == "application/pdf"


async def test_obtener_retorna_none_si_el_archivo_no_existe():
    bucket = MagicMock()
    bucket.open_download_stream = AsyncMock(side_effect=NoFile("no existe"))
    p_bucket, p_manager = _con_bucket(bucket)

    with p_bucket, p_manager:
        assert await MongoAlmacenArchivosGridFS("mi_bucket").obtener(str(ObjectId())) is None


async def test_obtener_usa_un_tipo_neutro_si_faltan_los_metadatos():
    flujo = MagicMock()
    flujo.read = AsyncMock(return_value=b"x")
    flujo.filename = "x.bin"
    flujo.metadata = None
    bucket = MagicMock()
    bucket.open_download_stream = AsyncMock(return_value=flujo)
    p_bucket, p_manager = _con_bucket(bucket)

    with p_bucket, p_manager:
        archivo = await MongoAlmacenArchivosGridFS("mi_bucket").obtener(str(ObjectId()))

    assert archivo.tipo_mime == "application/octet-stream"


async def test_eliminar_borra_el_archivo():
    bucket = MagicMock()
    bucket.delete = AsyncMock()
    p_bucket, p_manager = _con_bucket(bucket)
    id_archivo = ObjectId()

    with p_bucket, p_manager:
        await MongoAlmacenArchivosGridFS("mi_bucket").eliminar(str(id_archivo))

    bucket.delete.assert_awaited_once_with(id_archivo)


async def test_eliminar_no_lanza_error_si_el_archivo_ya_no_existe():
    bucket = MagicMock()
    bucket.delete = AsyncMock(side_effect=NoFile("no existe"))
    p_bucket, p_manager = _con_bucket(bucket)

    with p_bucket, p_manager:
        await MongoAlmacenArchivosGridFS("mi_bucket").eliminar(str(ObjectId()))
