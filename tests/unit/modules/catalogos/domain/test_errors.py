from modules.catalogos.domain.errors import (
    AreaNoEncontradaError,
    AreaNombreDuplicadoError,
    CategoriaNoEncontradaError,
    CategoriaNombreDuplicadaError,
    CondicionColorInvalidoError,
    CondicionNoEncontradaError,
    CondicionNombreDuplicadoError,
    LugarNoEncontradoError,
    LugarNombreDuplicadoError,
    SedeEnUsoError,
    SedeNoEncontradaError,
    SedeNombreDuplicadoError,
)
from shared.domain.errors import ErrorCategory


def test_area_nombre_duplicado_error_tiene_code_y_category():
    error = AreaNombreDuplicadoError("Direccion")

    assert error.code == "CAT-001"
    assert error.category == ErrorCategory.CONFLICT
    assert "Direccion" in error.message


def test_area_no_encontrada_error_tiene_code_y_category():
    error = AreaNoEncontradaError("1")

    assert error.code == "CAT-002"
    assert error.category == ErrorCategory.NOT_FOUND


def test_categoria_nombre_duplicada_error_tiene_code_y_category():
    error = CategoriaNombreDuplicadaError("Muebles")

    assert error.code == "CAT-003"
    assert error.category == ErrorCategory.CONFLICT


def test_categoria_no_encontrada_error_tiene_code_y_category():
    error = CategoriaNoEncontradaError("1")

    assert error.code == "CAT-004"
    assert error.category == ErrorCategory.NOT_FOUND


def test_condicion_nombre_duplicado_error_tiene_code_y_category():
    error = CondicionNombreDuplicadoError("Bueno")

    assert error.code == "CAT-005"
    assert error.category == ErrorCategory.CONFLICT


def test_condicion_no_encontrada_error_tiene_code_y_category():
    error = CondicionNoEncontradaError("1")

    assert error.code == "CAT-006"
    assert error.category == ErrorCategory.NOT_FOUND


def test_condicion_color_invalido_error_tiene_code_y_category():
    error = CondicionColorInvalidoError("rojo")

    assert error.code == "CAT-007"
    assert error.category == ErrorCategory.VALIDATION


def test_sede_nombre_duplicado_error_tiene_code_y_category():
    error = SedeNombreDuplicadoError("Prado")

    assert error.code == "CAT-008"
    assert error.category == ErrorCategory.CONFLICT


def test_sede_no_encontrada_error_tiene_code_y_category():
    error = SedeNoEncontradaError("1")

    assert error.code == "CAT-009"
    assert error.category == ErrorCategory.NOT_FOUND


def test_sede_en_uso_error_tiene_code_y_category():
    error = SedeEnUsoError("1")

    assert error.code == "CAT-010"
    assert error.category == ErrorCategory.CONFLICT


def test_lugar_nombre_duplicado_error_tiene_code_y_category():
    error = LugarNombreDuplicadoError("Bodega")

    assert error.code == "CAT-011"
    assert error.category == ErrorCategory.CONFLICT


def test_lugar_no_encontrado_error_tiene_code_y_category():
    error = LugarNoEncontradoError("1")

    assert error.code == "CAT-012"
    assert error.category == ErrorCategory.NOT_FOUND
