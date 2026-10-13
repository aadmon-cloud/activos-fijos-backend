from modules.mantenimientos.domain.errors import (
    ActivoNoEncontradoParaMantenimientoError,
    ArchivoDemasiadoGrandeError,
    ArchivoNoEncontradoError,
    ArchivoTipoNoPermitidoError,
    CodigosMasivosVaciosError,
    DemasiadosCodigosMasivosError,
    MantenimientoNoEncontradoError,
    SolicitudNoValidaParaMantenimientoError,
    TecnicoInvalidoError,
    TransicionEstadoMantenimientoInvalidaError,
)
from shared.domain.errors import ErrorCategory


def test_mantenimiento_no_encontrado_error_tiene_code_y_category():
    error = MantenimientoNoEncontradoError("1")

    assert error.code == "MNT-001"
    assert error.category == ErrorCategory.NOT_FOUND


def test_activo_no_encontrado_para_mantenimiento_error_tiene_code_y_category():
    error = ActivoNoEncontradoParaMantenimientoError("a1")

    assert error.code == "MNT-002"
    assert error.category == ErrorCategory.NOT_FOUND


def test_tecnico_invalido_error_tiene_code_y_category():
    error = TecnicoInvalidoError("u1")

    assert error.code == "MNT-003"
    assert error.category == ErrorCategory.BUSINESS_RULE


def test_transicion_estado_mantenimiento_invalida_error_tiene_code_y_category():
    error = TransicionEstadoMantenimientoInvalidaError("completado", "programado")

    assert error.code == "MNT-004"
    assert error.category == ErrorCategory.BUSINESS_RULE


def test_archivo_tipo_no_permitido_error_tiene_code_y_category():
    error = ArchivoTipoNoPermitidoError()

    assert error.code == "MNT-005"
    assert error.category == ErrorCategory.VALIDATION


def test_archivo_demasiado_grande_error_tiene_code_y_category():
    error = ArchivoDemasiadoGrandeError()

    assert error.code == "MNT-006"
    assert error.category == ErrorCategory.VALIDATION


def test_archivo_no_encontrado_error_tiene_code_y_category():
    error = ArchivoNoEncontradoError("f1")

    assert error.code == "MNT-007"
    assert error.category == ErrorCategory.NOT_FOUND


def test_solicitud_no_valida_para_mantenimiento_error_tiene_code_y_category():
    error = SolicitudNoValidaParaMantenimientoError("s1")

    assert error.code == "MNT-008"
    assert error.category == ErrorCategory.BUSINESS_RULE


def test_codigos_masivos_vacios_error_tiene_code_y_category():
    error = CodigosMasivosVaciosError()

    assert error.code == "MNT-009"
    assert error.category == ErrorCategory.VALIDATION


def test_demasiados_codigos_masivos_error_informa_el_limite():
    error = DemasiadosCodigosMasivosError(200)

    assert error.code == "MNT-010"
    assert error.category == ErrorCategory.VALIDATION
    assert error.details == {"limite": 200}
