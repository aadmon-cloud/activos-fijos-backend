from modules.usuarios.domain.entities import RolUsuario
from shared.domain.roles import (
    ETIQUETAS_ROL,
    ROL_ADMINISTRADOR_GENERAL,
    ROL_EMPLEADO,
    ROL_SUPER_ADMINISTRADOR,
    ROLES_EDITABLES,
    es_administrador,
    es_super_administrador,
)


def test_los_roles_compartidos_coinciden_con_el_enum_de_usuarios():
    # Los nombres de rol viven en dos sitios (shared y el enum de usuarios): este test los mantiene iguales.
    assert {rol.value for rol in RolUsuario} == set(ROLES_EDITABLES) | {ROL_SUPER_ADMINISTRADOR}


def test_todo_rol_tiene_etiqueta_en_espanol():
    assert set(ETIQUETAS_ROL) == {rol.value for rol in RolUsuario}
    assert all(etiqueta.strip() for etiqueta in ETIQUETAS_ROL.values())


def test_el_super_administrador_no_es_un_rol_editable():
    assert ROL_SUPER_ADMINISTRADOR not in ROLES_EDITABLES


def test_solo_el_super_administrador_es_super_administrador():
    assert es_super_administrador(ROL_SUPER_ADMINISTRADOR)
    assert not es_super_administrador(ROL_ADMINISTRADOR_GENERAL)
    assert not es_super_administrador(None)


def test_el_super_administrador_y_el_administrador_general_son_administradores():
    assert es_administrador(ROL_SUPER_ADMINISTRADOR)
    assert es_administrador(ROL_ADMINISTRADOR_GENERAL)


def test_los_demas_roles_y_los_desconocidos_no_son_administradores():
    assert not es_administrador(ROL_EMPLEADO)
    assert not es_administrador("rol-inventado")
    assert not es_administrador(None)
    assert not es_administrador("")
