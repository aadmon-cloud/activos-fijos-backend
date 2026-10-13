from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from modules.activos.infrastructure.persistence.mongo.almacen_fotos import MongoAlmacenFotos

_MODULO = "modules.activos.infrastructure.persistence.mongo.almacen_fotos"


class _Cursor:
    """Cursor falso de GridFS: iterable asincrono y encadenable (sort/limit/to_list)."""

    def __init__(self, archivos):
        self._archivos = archivos

    def __aiter__(self):
        async def _gen():
            for archivo in self._archivos:
                yield archivo

        return _gen()

    def sort(self, *_):
        return self

    def limit(self, *_):
        return self

    async def to_list(self, _):
        # Igual que GridFS real: to_list devuelve documentos (dict), no objetos GridOut.
        return [{"_id": archivo._id} for archivo in self._archivos]


def _archivo(id_=None):
    archivo = MagicMock()
    archivo._id = id_ or ObjectId()
    return archivo


def _con_bucket(bucket):
    return patch(f"{_MODULO}.AsyncIOMotorGridFSBucket", return_value=bucket), patch(
        f"{_MODULO}.mongo_manager"
    )


async def test_guardar_sube_la_nueva_y_borra_las_anteriores_pero_no_la_nueva():
    nuevo_id = ObjectId()
    anterior = _archivo()
    nueva = _archivo(nuevo_id)
    bucket = MagicMock()
    bucket.upload_from_stream = AsyncMock(return_value=nuevo_id)
    bucket.find.return_value = _Cursor([anterior, nueva])
    bucket.delete = AsyncMock()
    p_bucket, p_manager = _con_bucket(bucket)

    with p_bucket, p_manager:
        await MongoAlmacenFotos().guardar("act1", b"datos", "image/png")

    bucket.upload_from_stream.assert_awaited_once_with(
        "act1", b"datos", metadata={"tipo_mime": "image/png"}
    )
    bucket.find.assert_called_once_with({"filename": "act1"})
    bucket.delete.assert_awaited_once_with(anterior._id)


async def test_guardar_no_borra_nada_si_la_subida_falla():
    bucket = MagicMock()
    bucket.upload_from_stream = AsyncMock(side_effect=RuntimeError("falló"))
    bucket.delete = AsyncMock()
    p_bucket, p_manager = _con_bucket(bucket)

    with p_bucket, p_manager:
        try:
            await MongoAlmacenFotos().guardar("act1", b"datos", "image/png")
        except RuntimeError:
            pass

    bucket.delete.assert_not_called()


async def test_obtener_devuelve_contenido_y_tipo_del_archivo_mas_reciente():
    archivo = _archivo()
    flujo = MagicMock()
    flujo.read = AsyncMock(return_value=b"datos")
    flujo.metadata = {"tipo_mime": "image/webp"}
    bucket = MagicMock()
    bucket.find.return_value = _Cursor([archivo])
    bucket.open_download_stream = AsyncMock(return_value=flujo)
    p_bucket, p_manager = _con_bucket(bucket)

    with p_bucket, p_manager:
        foto = await MongoAlmacenFotos().obtener("act1")

    assert foto.contenido == b"datos"
    assert foto.tipo_mime == "image/webp"
    bucket.open_download_stream.assert_awaited_once_with(archivo._id)


async def test_obtener_devuelve_none_si_no_hay_foto():
    bucket = MagicMock()
    bucket.find.return_value = _Cursor([])
    p_bucket, p_manager = _con_bucket(bucket)

    with p_bucket, p_manager:
        assert await MongoAlmacenFotos().obtener("act1") is None


async def test_obtener_usa_un_tipo_neutro_si_faltan_los_metadatos():
    flujo = MagicMock()
    flujo.read = AsyncMock(return_value=b"x")
    flujo.metadata = None
    bucket = MagicMock()
    bucket.find.return_value = _Cursor([_archivo()])
    bucket.open_download_stream = AsyncMock(return_value=flujo)
    p_bucket, p_manager = _con_bucket(bucket)

    with p_bucket, p_manager:
        foto = await MongoAlmacenFotos().obtener("act1")

    assert foto.tipo_mime == "application/octet-stream"


async def test_eliminar_borra_todos_los_archivos_del_activo():
    a, b = _archivo(), _archivo()
    bucket = MagicMock()
    bucket.find.return_value = _Cursor([a, b])
    bucket.delete = AsyncMock()
    p_bucket, p_manager = _con_bucket(bucket)

    with p_bucket, p_manager:
        await MongoAlmacenFotos().eliminar("act1")

    assert [c.args[0] for c in bucket.delete.await_args_list] == [a._id, b._id]
