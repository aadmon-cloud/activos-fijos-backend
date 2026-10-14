from shared.domain.permisos import (
    CLAVES_BASE,
    CLAVES_FUNCIONES,
    FUNCIONES,
    PERMISOS_EXCLUSIVOS_SUPER_ADMINISTRADOR,
    PERMISOS_POR_DEFECTO,
    permisos_por_defecto,
)
from shared.domain.roles import (
    ROL_ADMINISTRADOR_GENERAL,
    ROL_EMPLEADO,
    ROL_MANTENIMIENTO,
    ROLES_EDITABLES,
)


def test_las_claves_del_catalogo_son_unicas_y_siguen_el_formato_modulo_accion():
    claves = [funcion.clave for funcion in FUNCIONES]

    assert len(claves) == len(set(claves))
    assert all("-" in clave and clave == clave.lower() for clave in claves)


def test_toda_funcion_tiene_modulo_etiqueta_y_descripcion():
    for funcion in FUNCIONES:
        assert funcion.modulo.strip() and funcion.etiqueta.strip() and funcion.descripcion.strip()


def test_hay_una_matriz_de_fabrica_para_cada_rol_editable_y_solo_para_ellos():
    assert set(PERMISOS_POR_DEFECTO) == set(ROLES_EDITABLES)


def test_la_matriz_de_fabrica_solo_usa_funciones_del_catalogo():
    for rol, permisos in PERMISOS_POR_DEFECTO.items():
        assert permisos <= CLAVES_FUNCIONES, rol


def test_las_funciones_base_las_tiene_todo_rol_de_fabrica():
    assert CLAVES_BASE == {"home-ver", "cuenta-ver"}

    for rol in ROLES_EDITABLES:
        assert CLAVES_BASE <= permisos_por_defecto(rol), rol


def test_las_funciones_exclusivas_del_super_administrador_no_estan_en_el_catalogo_asignable():
    assert not set(PERMISOS_EXCLUSIVOS_SUPER_ADMINISTRADOR) & CLAVES_FUNCIONES


def test_el_empleado_de_fabrica_no_administra_nada():
    permisos = permisos_por_defecto(ROL_EMPLEADO)

    assert "usuarios-ver" not in permisos
    assert "activos-crear" not in permisos
    assert "mantenimientos-gestionar" not in permisos


def test_mantenimiento_de_fabrica_gestiona_mantenimientos_pero_no_usuarios():
    permisos = permisos_por_defecto(ROL_MANTENIMIENTO)

    assert {"mantenimientos-ver", "mantenimientos-gestionar"} <= permisos
    assert "usuarios-crear" not in permisos


def test_el_administrador_general_de_fabrica_tiene_todo_el_catalogo():
    # Antes de la administracion de permisos el Administrador General podia hacer todo lo que existia.
    assert permisos_por_defecto(ROL_ADMINISTRADOR_GENERAL) == CLAVES_FUNCIONES


def test_un_rol_desconocido_no_recibe_ninguna_funcion():
    assert permisos_por_defecto("rol-inventado") == frozenset()
