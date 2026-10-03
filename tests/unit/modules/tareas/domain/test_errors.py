from modules.tareas.domain.errors import TituloTareaVacioError
from shared.domain.errors import ErrorCategory


def test_titulo_tarea_vacio_error_tiene_code_category_y_mensaje():
    error = TituloTareaVacioError()

    assert error.code == "TAR-001"
    assert error.category == ErrorCategory.BUSINESS_RULE
    assert "titulo" in error.message.lower()
