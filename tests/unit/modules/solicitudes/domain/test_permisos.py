from datetime import UTC, datetime

from modules.solicitudes.domain.entities import (
    EstadoSolicitud,
    PrioridadSolicitud,
    Solicitud,
    TipoSolicitud,
)
from shared.domain.entities.audit import AuditPersona


def _solicitud(**overrides) -> Solicitud:
    valores = dict(
        id="1",
        tipo=TipoSolicitud.MANTENIMIENTO,
        activo_id="a1",
        descripcion="desc",
        prioridad=PrioridadSolicitud.MEDIA,
        evidencias=[],
        estado=EstadoSolicitud.PENDIENTE,
        rol_asignado="mantenimiento",
        area_id=None,
        seguimiento=[],
        creado_por=AuditPersona(id_persona="solicitante-1", nombre="Ana", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Solicitud(**valores)

from modules.solicitudes.domain.permisos import (
    estados_destino_permitidos,
    puede_cambiar_a,
    puede_cerrar,
    puede_comentar,
    puede_procesar,
    puede_ver,
)

ADMIN = ("admin-1", "administrador_general", None)
SOLICITANTE = ("solicitante-1", "empleado", None)
TECNICO = ("tecnico-1", "mantenimiento", None)
TERCERO = ("tercero-1", "tecnologia", "area-2")


# ---------------------------------------------------------------- ver
def test_ve_la_solicitud_el_administrador_el_solicitante_y_el_rol_asignado():
    solicitud = _solicitud()

    assert puede_ver(solicitud, *ADMIN) is True
    assert puede_ver(solicitud, *SOLICITANTE) is True
    assert puede_ver(solicitud, *TECNICO) is True


def test_ve_la_solicitud_el_area_asignada():
    solicitud = _solicitud(rol_asignado=None, area_id="area-1")

    assert puede_ver(solicitud, "otro", "empleado", "area-1") is True


def test_un_tercero_sin_relacion_no_ve_la_solicitud():
    assert puede_ver(_solicitud(), *TERCERO) is False


def test_un_empleado_de_otra_area_no_ve_una_solicitud_asignada_a_un_area():
    solicitud = _solicitud(rol_asignado=None, area_id="area-1")

    assert puede_ver(solicitud, "otro", "empleado", "area-9") is False
    assert puede_ver(solicitud, "otro", "empleado", None) is False


# ---------------------------------------------------------------- procesar
def test_procesa_el_administrador_y_el_equipo_asignado():
    solicitud = _solicitud()

    assert puede_procesar(solicitud, *ADMIN) is True
    assert puede_procesar(solicitud, *TECNICO) is True


def test_el_solicitante_no_puede_procesar_su_propia_solicitud():
    assert puede_procesar(_solicitud(), *SOLICITANTE) is False


def test_el_solicitante_no_la_procesa_ni_siquiera_si_pertenece_al_equipo_asignado():
    solicitud = _solicitud(creado_por=_solicitud().creado_por)

    assert puede_procesar(solicitud, "solicitante-1", "mantenimiento", None) is False


def test_el_administrador_puede_procesar_incluso_lo_que_el_mismo_creo():
    solicitud = _solicitud(
        creado_por=AuditPersona(id_persona="admin-1", nombre="Admin", fecha=datetime.now(UTC))
    )

    assert puede_procesar(solicitud, *ADMIN) is True


def test_un_tercero_no_puede_procesar():
    assert puede_procesar(_solicitud(), *TERCERO) is False


# ---------------------------------------------------------------- cerrar y comentar
def test_cierra_el_solicitante_y_el_administrador_pero_no_el_equipo_asignado():
    solicitud = _solicitud()

    assert puede_cerrar(solicitud, "solicitante-1", "empleado") is True
    assert puede_cerrar(solicitud, "admin-1", "administrador_general") is True
    assert puede_cerrar(solicitud, "tecnico-1", "mantenimiento") is False


def test_comenta_quien_puede_ver_y_nadie_mas():
    solicitud = _solicitud()

    assert puede_comentar(solicitud, *SOLICITANTE) is True
    assert puede_comentar(solicitud, *TECNICO) is True
    assert puede_comentar(solicitud, *TERCERO) is False


def test_puede_cambiar_a_cerrada_depende_de_cerrar_y_lo_demas_de_procesar():
    solicitud = _solicitud()

    assert puede_cambiar_a(solicitud, EstadoSolicitud.CERRADA, *SOLICITANTE) is True
    assert puede_cambiar_a(solicitud, EstadoSolicitud.CERRADA, *TECNICO) is False
    assert puede_cambiar_a(solicitud, EstadoSolicitud.EN_PROCESO, *TECNICO) is True
    assert puede_cambiar_a(solicitud, EstadoSolicitud.EN_PROCESO, *SOLICITANTE) is False


# ---------------------------------------------------------------- estados que se ofrecen
def test_el_equipo_ve_iniciar_o_rechazar_una_solicitud_pendiente():
    assert estados_destino_permitidos(_solicitud(), *TECNICO) == [
        EstadoSolicitud.EN_PROCESO,
        EstadoSolicitud.RECHAZADA,
    ]


def test_el_solicitante_no_tiene_estados_en_una_pendiente_pero_si_cerrar_una_resuelta():
    pendiente = _solicitud()
    resuelta = _solicitud(estado=EstadoSolicitud.RESUELTA)

    assert estados_destino_permitidos(pendiente, *SOLICITANTE) == []
    assert estados_destino_permitidos(resuelta, *SOLICITANTE) == [EstadoSolicitud.CERRADA]


def test_el_equipo_no_puede_cerrar_una_resuelta():
    assert estados_destino_permitidos(_solicitud(estado=EstadoSolicitud.RESUELTA), *TECNICO) == []


def test_una_solicitud_cerrada_o_rechazada_no_ofrece_estados():
    for estado in (EstadoSolicitud.CERRADA, EstadoSolicitud.RECHAZADA):
        assert estados_destino_permitidos(_solicitud(estado=estado), *ADMIN) == []


def test_el_administrador_puede_hacer_todo_el_flujo():
    assert estados_destino_permitidos(_solicitud(estado=EstadoSolicitud.EN_PROCESO), *ADMIN) == [
        EstadoSolicitud.RESUELTA,
        EstadoSolicitud.RECHAZADA,
    ]
    assert estados_destino_permitidos(_solicitud(estado=EstadoSolicitud.RESUELTA), *ADMIN) == [
        EstadoSolicitud.CERRADA
    ]
