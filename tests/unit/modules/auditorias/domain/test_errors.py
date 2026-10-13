import pytest

from modules.auditorias.domain.errors import (
    AuditoriaNoEncontradaError,
    AuditoriaNoModificableError,
    ItemAuditoriaNoEncontradoError,
    ObservacionObligatoriaError,
    PdfAuditoriaNoDisponibleError,
    UsuarioNoEncontradoParaAuditoriaError,
)
from shared.domain.errors import ErrorCategory


@pytest.mark.parametrize(
    "excepcion,args,codigo,categoria",
    [
        (UsuarioNoEncontradoParaAuditoriaError, ("u1",), "AUD-001", ErrorCategory.NOT_FOUND),
        (AuditoriaNoModificableError, ("aud-1",), "AUD-002", ErrorCategory.BUSINESS_RULE),
        (ItemAuditoriaNoEncontradoError, ("a1",), "AUD-003", ErrorCategory.NOT_FOUND),
        (ObservacionObligatoriaError, (), "AUD-004", ErrorCategory.VALIDATION),
        (AuditoriaNoEncontradaError, ("aud-1",), "AUD-005", ErrorCategory.NOT_FOUND),
        (PdfAuditoriaNoDisponibleError, ("aud-1",), "AUD-006", ErrorCategory.NOT_FOUND),
    ],
)
def test_errores_de_dominio_tienen_el_codigo_y_la_categoria_esperados(
    excepcion, args, codigo, categoria
):
    error = excepcion(*args)

    assert error.code == codigo
    assert error.category == categoria
