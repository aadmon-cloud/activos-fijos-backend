from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from modules.notificaciones.domain.entities import EstadoNotificacion, Notificacion
from modules.notificaciones.infrastructure.adapters.notificador_registrado import (
    NotificadorRegistrado,
)
from modules.notificaciones.infrastructure.adapters.tareas_recordatorio import (
    AlertasMantenimientoTarea,
    RecordatoriosDevolucionTarea,
)
from modules.notificaciones.infrastructure.correo.configuracion_correo_adapter import (
    ConfiguracionCorreoSettings,
)
from modules.notificaciones.infrastructure.persistence.mongo.notificacion_repository import (
    MongoNotificacionRepository,
    _doc_a_entidad,
    _entidad_a_doc,
    crear_indices,
)
from modules.notificaciones.infrastructure.persistence.mongo.resolutor_destinatarios_adapter import (
    MongoResolutorDestinatarios,
)

_REPO = "modules.notificaciones.infrastructure.persistence.mongo.notificacion_repository"
_RESOLUTOR = (
    "modules.notificaciones.infrastructure.persistence.mongo.resolutor_destinatarios_adapter.mongo_manager"
)
_CONFIG = "modules.notificaciones.infrastructure.correo.configuracion_correo_adapter.settings"
_AHORA = datetime(2026, 1, 1, tzinfo=UTC)


def _notificacion(**overrides) -> Notificacion:
    valores = dict(
        id=None,
        destinatarios=["usuario:1", "rol:mantenimiento"],
        correos=["ana@x.com"],
        asunto="Asunto",
        cuerpo="Cuerpo",
        estado=EstadoNotificacion.ENVIADA,
        detalle=None,
        intentos=1,
        creada_en=_AHORA,
        actualizada_en=_AHORA,
    )
    valores.update(overrides)

    return Notificacion(**valores)


# ---------- repositorio ----------


def test_la_notificacion_se_convierte_a_documento_y_de_vuelta():
    doc = _entidad_a_doc(_notificacion(estado=EstadoNotificacion.FALLIDA, detalle="boom", intentos=3))

    assert "id" not in doc
    assert doc["estado"] == "fallida"
    assert doc["intentos"] == 3

    entidad = _doc_a_entidad({**doc, "_id": ObjectId("a" * 24)})

    assert entidad.id == "a" * 24
    assert entidad.estado == EstadoNotificacion.FALLIDA
    assert entidad.detalle == "boom"
    assert entidad.destinatarios == ["usuario:1", "rol:mantenimiento"]


def test_un_documento_antiguo_sin_intentos_ni_listas_se_lee_con_valores_por_defecto():
    entidad = _doc_a_entidad(
        {
            "_id": ObjectId(),
            "asunto": "A",
            "cuerpo": "C",
            "estado": "enviada",
            "creada_en": _AHORA,
            "actualizada_en": _AHORA,
        }
    )

    assert entidad.intentos == 1
    assert entidad.destinatarios == [] and entidad.correos == []


@patch(f"{_REPO}.mongo_manager")
async def test_crear_indices(mongo_manager_mock):
    coleccion = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"notificaciones": coleccion}

    await crear_indices()

    assert {c.kwargs["name"] for c in coleccion.create_index.call_args_list} == {"idx_estado", "idx_creada_en"}


@patch(f"{_REPO}.mongo_manager")
async def test_guardar_una_nueva_inserta_y_una_existente_reemplaza(mongo_manager_mock):
    id_documento = ObjectId()
    coleccion = MagicMock()
    coleccion.insert_one = AsyncMock(return_value=MagicMock(inserted_id=id_documento))
    coleccion.replace_one = AsyncMock()
    coleccion.find_one = AsyncMock(return_value={**_entidad_a_doc(_notificacion()), "_id": id_documento})
    mongo_manager_mock.get_database.return_value = {"notificaciones": coleccion}
    repo = MongoNotificacionRepository()

    nueva = await repo.guardar(_notificacion())
    await repo.guardar(_notificacion(id=str(id_documento)))

    assert nueva.id == str(id_documento)
    coleccion.insert_one.assert_awaited_once()
    coleccion.replace_one.assert_awaited_once()


@patch(f"{_REPO}.mongo_manager")
async def test_listar_y_contar_filtran_por_estado(mongo_manager_mock):
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.skip.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=[{**_entidad_a_doc(_notificacion()), "_id": ObjectId()}])
    coleccion = MagicMock()
    coleccion.find = MagicMock(return_value=cursor)
    coleccion.count_documents = AsyncMock(return_value=7)
    mongo_manager_mock.get_database.return_value = {"notificaciones": coleccion}
    repo = MongoNotificacionRepository()

    items = await repo.listar(EstadoNotificacion.FALLIDA, 5, 10)
    total = await repo.contar(EstadoNotificacion.FALLIDA)
    await repo.contar(None)

    assert len(items) == 1
    coleccion.find.assert_called_once_with({"estado": "fallida"})
    cursor.skip.assert_called_once_with(5)
    cursor.limit.assert_called_once_with(10)
    assert total == 7
    assert coleccion.count_documents.await_args_list[1].args[0] == {}


# ---------- resolutor de destinatarios ----------


def _usuarios(documentos):
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=documentos)
    coleccion = MagicMock()
    coleccion.find = MagicMock(return_value=cursor)

    return coleccion


@patch(_RESOLUTOR)
async def test_resuelve_usuario_rol_y_area_en_una_sola_consulta_solo_de_activos(mongo_manager_mock):
    usuario, area = ObjectId(), ObjectId()
    coleccion = _usuarios([{"email": "ana@x.com"}, {"email": "luis@x.com"}])
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion}

    correos = await MongoResolutorDestinatarios().resolver(
        [f"usuario:{usuario}", "rol:mantenimiento", f"area:{area}"]
    )

    assert correos == ["ana@x.com", "luis@x.com"]
    filtro, proyeccion = coleccion.find.call_args.args
    assert filtro == {
        "$or": [{"_id": usuario}, {"rol": "mantenimiento"}, {"area_id": area}],
        "activo": True,
    }
    assert proyeccion == {"email": 1}
    assert coleccion.find.call_count == 1


@patch(_RESOLUTOR)
async def test_un_correo_literal_valido_se_usa_tal_cual_y_no_consulta(mongo_manager_mock):
    coleccion = _usuarios([])
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion}

    correos = await MongoResolutorDestinatarios().resolver(["ana@example.com"])

    assert correos == ["ana@example.com"]
    coleccion.find.assert_not_called()


@patch(_RESOLUTOR)
async def test_ignora_los_destinatarios_que_no_se_entienden(mongo_manager_mock):
    coleccion = _usuarios([])
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion}

    correos = await MongoResolutorDestinatarios().resolver(
        ["usuario:no-es-un-id", "area:xyz", "no es un correo", "ana@@x.com", ""]
    )

    assert correos == []
    coleccion.find.assert_not_called()


@patch(_RESOLUTOR)
async def test_quita_repetidos_sin_distinguir_mayusculas_y_conserva_el_orden(mongo_manager_mock):
    usuario = ObjectId()
    mongo_manager_mock.get_database.return_value = {
        "usuarios": _usuarios([{"email": "ANA@x.com"}, {"email": "luis@x.com"}, {}])
    }

    correos = await MongoResolutorDestinatarios().resolver(["ana@x.com", f"usuario:{usuario}"])

    assert correos == ["ana@x.com", "luis@x.com"]


# ---------- configuracion del correo ----------


def _settings(**overrides):
    mock = MagicMock()
    mock.ENTORNO = "local"
    mock.SMTP_HOST = "smtp.gmail.com"
    mock.SMTP_USER = "sistema@org.com"
    mock.SMTP_FROM_EMAIL = "sistema@org.com"
    mock.SMTP_PASSWORD = "clave"
    mock.SMTP_PASSWORD_SECRET_NAME = None
    mock.APP_URL = "https://activos.org"
    for clave, valor in overrides.items():
        setattr(mock, clave, valor)

    return mock


def test_el_correo_esta_configurado_con_servidor_usuario_remitente_y_clave():
    with patch(_CONFIG, _settings()):
        assert ConfiguracionCorreoSettings().esta_configurado() is True


def test_en_local_se_necesita_la_clave_y_fuera_de_local_el_nombre_del_secreto():
    with patch(_CONFIG, _settings(SMTP_PASSWORD=None)):
        assert ConfiguracionCorreoSettings().esta_configurado() is False

    with patch(_CONFIG, _settings(ENTORNO="produccion", SMTP_PASSWORD=None, SMTP_PASSWORD_SECRET_NAME="smtp-clave")):
        assert ConfiguracionCorreoSettings().esta_configurado() is True

    with patch(_CONFIG, _settings(ENTORNO="produccion", SMTP_PASSWORD="ignorada", SMTP_PASSWORD_SECRET_NAME=None)):
        assert ConfiguracionCorreoSettings().esta_configurado() is False


def test_sin_servidor_usuario_o_remitente_no_esta_configurado():
    for faltante in ("SMTP_HOST", "SMTP_USER", "SMTP_FROM_EMAIL"):
        with patch(_CONFIG, _settings(**{faltante: None})):
            assert ConfiguracionCorreoSettings().esta_configurado() is False


def test_remitente_y_url_de_la_aplicacion():
    with patch(_CONFIG, _settings()):
        assert ConfiguracionCorreoSettings().remitente() == "sistema@org.com"
        assert ConfiguracionCorreoSettings().url_aplicacion() == "https://activos.org"

    with patch(_CONFIG, _settings(SMTP_FROM_EMAIL=None, APP_URL=None)):
        assert ConfiguracionCorreoSettings().remitente() is None
        assert ConfiguracionCorreoSettings().url_aplicacion() is None


# ---------- notificador registrado ----------


async def test_el_notificador_registrado_envia_a_traves_del_servicio():
    servicio = AsyncMock()

    await NotificadorRegistrado(servicio).notificar(["usuario:1"], "Asunto", "Cuerpo")

    servicio.ejecutar.assert_awaited_once_with(["usuario:1"], "Asunto", "Cuerpo")


async def test_si_el_servicio_falla_el_notificador_no_rompe_la_accion_del_usuario():
    servicio = AsyncMock()
    servicio.ejecutar.side_effect = RuntimeError("base de datos caida")

    await NotificadorRegistrado(servicio).notificar(["usuario:1"], "Asunto", "Cuerpo")


# ---------- tareas de recordatorio ----------


async def test_las_tareas_delegan_en_los_servicios_de_cada_modulo():
    servicio_mantenimientos, servicio_devoluciones = AsyncMock(), AsyncMock()
    servicio_mantenimientos.ejecutar.return_value = 4
    servicio_devoluciones.ejecutar.return_value = 2

    with patch(
        "modules.notificaciones.infrastructure.adapters.tareas_recordatorio.get_verificar_alertas_mantenimiento_service",
        return_value=servicio_mantenimientos,
    ), patch(
        "modules.notificaciones.infrastructure.adapters.tareas_recordatorio.get_recordar_devoluciones_movimiento_service",
        return_value=servicio_devoluciones,
    ):
        assert await AlertasMantenimientoTarea().ejecutar() == 4
        assert await RecordatoriosDevolucionTarea().ejecutar() == 2
