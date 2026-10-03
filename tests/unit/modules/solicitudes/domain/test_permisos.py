from datetime import UTC, datetime

from modules.solicitudes.domain.entities import EstadoSolicitud, PrioridadSolicitud, Solicitud, TipoSolicitud
from modules.solicitudes.domain.permisos import puede_gestionar
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


def test_administrador_general_siempre_puede_gestionar():
    solicitud = _solicitud()

    assert puede_gestionar(solicitud, "otro-id", "administrador_general", None) is True


def test_el_solicitante_puede_gestionar():
    solicitud = _solicitud()

    assert puede_gestionar(solicitud, "solicitante-1", "empleado", None) is True


def test_el_rol_asignado_puede_gestionar():
    solicitud = _solicitud(rol_asignado="mantenimiento")

    assert puede_gestionar(solicitud, "otro-id", "mantenimiento", None) is True


def test_el_area_asignada_puede_gestionar():
    solicitud = _solicitud(rol_asignado=None, area_id="area-1")

    assert puede_gestionar(solicitud, "otro-id", "empleado", "area-1") is True


def test_un_tercero_sin_relacion_no_puede_gestionar():
    solicitud = _solicitud(rol_asignado="mantenimiento")

    assert puede_gestionar(solicitud, "otro-id", "tecnologia", "area-2") is False
