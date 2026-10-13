import pytest

from modules.movimientos.domain.errors import (
    ActivoNoDisponibleError,
    ActivoNoEncontradoParaMovimientoError,
    ActivoNoPerteneceAlMovimientoError,
    ActivosMovimientoObligatoriosError,
    BajaDeUnSoloActivoError,
    DestinatarioIgualAlResponsableError,
    DestinatarioNoPermitidoError,
    NoEsResponsableDelActivoError,
    ObservacionDeNovedadObligatoriaError,
    SentidoPrestamoObligatorioError,
    SinActivosParaProcesarError,
    ComprobanteNoDisponibleError,
    DescripcionMovimientoVaciaError,
    EventoNombreObligatorioError,
    FechasMovimientoInvalidasError,
    MotivoRechazoObligatorioError,
    MovimientoActivoYaExisteError,
    MovimientoNoEncontradoError,
    OperacionSobreActivoFallidaError,
    PermisoAprobacionError,
    SolicitudDeBajaRequiereAdminError,
    TransicionEstadoMovimientoInvalidaError,
    UsuarioDestinoNoEncontradoError,
    UsuarioDestinoObligatorioError,
)
from shared.domain.errors import ErrorCategory


@pytest.mark.parametrize(
    "excepcion,args,codigo,categoria",
    [
        (ActivoNoEncontradoParaMovimientoError, ("a1",), "MOV-001", ErrorCategory.NOT_FOUND),
        (UsuarioDestinoNoEncontradoError, ("u1",), "MOV-002", ErrorCategory.NOT_FOUND),
        (ActivoNoDisponibleError, ("a1",), "MOV-003", ErrorCategory.BUSINESS_RULE),
        (MovimientoActivoYaExisteError, ("a1",), "MOV-004", ErrorCategory.CONFLICT),
        (MovimientoNoEncontradoError, ("m1",), "MOV-005", ErrorCategory.NOT_FOUND),
        (
            TransicionEstadoMovimientoInvalidaError,
            ("solicitado", "aprobado"),
            "MOV-006",
            ErrorCategory.BUSINESS_RULE,
        ),
        (PermisoAprobacionError, ("m1",), "MOV-007", ErrorCategory.FORBIDDEN),
        (ComprobanteNoDisponibleError, ("m1",), "MOV-008", ErrorCategory.NOT_FOUND),
        (MotivoRechazoObligatorioError, (), "MOV-009", ErrorCategory.VALIDATION),
        (SolicitudDeBajaRequiereAdminError, (), "MOV-010", ErrorCategory.FORBIDDEN),
        (OperacionSobreActivoFallidaError, ("a1",), "MOV-011", ErrorCategory.BUSINESS_RULE),
        (DescripcionMovimientoVaciaError, (), "MOV-012", ErrorCategory.VALIDATION),
        (UsuarioDestinoObligatorioError, (), "MOV-013", ErrorCategory.VALIDATION),
        (EventoNombreObligatorioError, (), "MOV-014", ErrorCategory.VALIDATION),
        (FechasMovimientoInvalidasError, (), "MOV-015", ErrorCategory.VALIDATION),
        (ActivosMovimientoObligatoriosError, (), "MOV-016", ErrorCategory.VALIDATION),
        (BajaDeUnSoloActivoError, (), "MOV-017", ErrorCategory.VALIDATION),
        (SentidoPrestamoObligatorioError, (), "MOV-018", ErrorCategory.VALIDATION),
        (NoEsResponsableDelActivoError, ("a1",), "MOV-019", ErrorCategory.FORBIDDEN),
        (DestinatarioNoPermitidoError, (), "MOV-020", ErrorCategory.FORBIDDEN),
        (ActivoNoPerteneceAlMovimientoError, ("a1",), "MOV-021", ErrorCategory.VALIDATION),
        (SinActivosParaProcesarError, (), "MOV-022", ErrorCategory.BUSINESS_RULE),
        (ObservacionDeNovedadObligatoriaError, ("a1",), "MOV-023", ErrorCategory.VALIDATION),
        (DestinatarioIgualAlResponsableError, (), "MOV-024", ErrorCategory.VALIDATION),
    ],
)
def test_errores_de_dominio_tienen_el_codigo_y_la_categoria_esperados(
    excepcion, args, codigo, categoria
):
    error = excepcion(*args)

    assert error.code == codigo
    assert error.category == categoria
