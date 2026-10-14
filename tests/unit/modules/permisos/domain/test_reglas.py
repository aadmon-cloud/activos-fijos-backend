import pytest

from modules.permisos.domain.errors import (
    PermisoBaseNoDeshabilitableError,
    PermisoDesconocidoError,
    RolDesconocidoError,
    RolNoEditableError,
)
from modules.permisos.domain.reglas import (
    calcular_cambios,
    normalizar_permisos,
    validar_rol_editable,
    validar_rol_existente,
)
from shared.domain.errors import ErrorCategory

_BASE = ["home-ver", "cuenta-ver"]


def test_un_rol_editable_se_acepta():
    validar_rol_editable("empleado")


def test_el_super_administrador_no_es_editable():
    with pytest.raises(RolNoEditableError) as exc_info:
        validar_rol_editable("super_administrador")

    assert exc_info.value.code == "PER-002"
    assert exc_info.value.category == ErrorCategory.BUSINESS_RULE


def test_un_rol_inexistente_no_se_puede_editar():
    with pytest.raises(RolDesconocidoError) as exc_info:
        validar_rol_editable("rol-inventado")

    assert exc_info.value.code == "PER-001"
    assert exc_info.value.category == ErrorCategory.NOT_FOUND


def test_validar_rol_existente_acepta_incluso_al_super_administrador():
    validar_rol_existente("super_administrador")
    validar_rol_existente("empleado")


def test_validar_rol_existente_rechaza_un_rol_inexistente():
    with pytest.raises(RolDesconocidoError):
        validar_rol_existente("rol-inventado")


def test_normalizar_acepta_una_lista_valida_y_quita_repetidos():
    assert normalizar_permisos([*_BASE, "usuarios-ver", "usuarios-ver"]) == {*_BASE, "usuarios-ver"}


def test_normalizar_rechaza_una_funcion_que_no_existe():
    with pytest.raises(PermisoDesconocidoError) as exc_info:
        normalizar_permisos([*_BASE, "usuarios-volar"])

    assert exc_info.value.code == "PER-003"
    assert exc_info.value.category == ErrorCategory.VALIDATION


def test_normalizar_rechaza_dar_una_funcion_exclusiva_del_super_administrador():
    with pytest.raises(PermisoDesconocidoError):
        normalizar_permisos([*_BASE, "administracion-ver"])


@pytest.mark.parametrize("falta", ["home-ver", "cuenta-ver"])
def test_normalizar_no_deja_quitar_una_funcion_base(falta):
    pedidos = [clave for clave in _BASE if clave != falta]

    with pytest.raises(PermisoBaseNoDeshabilitableError) as exc_info:
        normalizar_permisos(pedidos)

    assert exc_info.value.code == "PER-004"


def test_calcular_cambios_separa_lo_habilitado_de_lo_deshabilitado():
    habilitadas, deshabilitadas = calcular_cambios(frozenset({"a", "b", "c"}), frozenset({"b", "c", "d", "e"}))

    assert habilitadas == ["d", "e"]
    assert deshabilitadas == ["a"]


def test_calcular_cambios_sin_diferencias_devuelve_listas_vacias():
    assert calcular_cambios(frozenset({"a"}), frozenset({"a"})) == ([], [])
