from modules.activos.domain.errors import (
    ActivoNoEncontradoError,
    ActivoNumeroInventarioDuplicadoError,
    ActivoValorInvalidoError,
    ComplementoCantidadInvalidaError,
    TransicionEstadoInvalidaError,
)
from shared.domain.errors import ErrorCategory


def test_activo_numero_inventario_duplicado_error_tiene_code_y_category():
    error = ActivoNumeroInventarioDuplicadoError("INV-001")

    assert error.code == "ACT-001"
    assert error.category == ErrorCategory.CONFLICT
    assert "INV-001" in error.message


def test_activo_no_encontrado_error_tiene_code_y_category():
    error = ActivoNoEncontradoError("1")

    assert error.code == "ACT-002"
    assert error.category == ErrorCategory.NOT_FOUND


def test_transicion_estado_invalida_error_tiene_code_y_category():
    error = TransicionEstadoInvalidaError("dado_de_baja", "disponible")

    assert error.code == "ACT-003"
    assert error.category == ErrorCategory.BUSINESS_RULE
    assert "dado_de_baja" in error.message
    assert "disponible" in error.message


def test_activo_valor_invalido_error_tiene_code_y_category():
    error = ActivoValorInvalidoError()

    assert error.code == "ACT-004"
    assert error.category == ErrorCategory.VALIDATION


def test_complemento_cantidad_invalida_error_tiene_code_y_category():
    error = ComplementoCantidadInvalidaError("Cargador")

    assert error.code == "ACT-005"
    assert error.category == ErrorCategory.VALIDATION
