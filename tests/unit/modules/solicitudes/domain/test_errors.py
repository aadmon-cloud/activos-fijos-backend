from modules.solicitudes.domain.errors import (
    ActivoNoAsignadoError,
    ActivoNoEncontradoParaSolicitudError,
    DescripcionVaciaError,
    SolicitudNoEncontradaError,
    SolicitudSinPermisoError,
    TransicionEstadoSolicitudInvalidaError,
)
from shared.domain.errors import ErrorCategory


def test_solicitud_no_encontrada_error_tiene_code_y_category():
    error = SolicitudNoEncontradaError("1")

    assert error.code == "SOL-001"
    assert error.category == ErrorCategory.NOT_FOUND


def test_activo_no_encontrado_para_solicitud_error_tiene_code_y_category():
    error = ActivoNoEncontradoParaSolicitudError("a1")

    assert error.code == "SOL-002"
    assert error.category == ErrorCategory.NOT_FOUND


def test_activo_no_asignado_error_tiene_code_y_category():
    error = ActivoNoAsignadoError("a1")

    assert error.code == "SOL-003"
    assert error.category == ErrorCategory.BUSINESS_RULE


def test_transicion_estado_solicitud_invalida_error_tiene_code_y_category():
    error = TransicionEstadoSolicitudInvalidaError("cerrada", "pendiente")

    assert error.code == "SOL-004"
    assert error.category == ErrorCategory.BUSINESS_RULE


def test_solicitud_sin_permiso_error_tiene_code_y_category():
    error = SolicitudSinPermisoError("1")

    assert error.code == "SOL-005"
    assert error.category == ErrorCategory.FORBIDDEN


def test_descripcion_vacia_error_tiene_code_y_category():
    error = DescripcionVaciaError()

    assert error.code == "SOL-006"
    assert error.category == ErrorCategory.VALIDATION
