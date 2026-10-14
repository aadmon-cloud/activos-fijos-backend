import pytest

from modules.usuarios.domain.entities import RolUsuario
from modules.usuarios.domain.reglas import puede_gestionar_rol


def test_el_super_administrador_puede_gestionar_el_rol_de_super_administrador():
    assert puede_gestionar_rol("super_administrador", RolUsuario.SUPER_ADMINISTRADOR)


@pytest.mark.parametrize("actor", ["administrador_general", "tecnologia", "mantenimiento", "empleado", "", "rol-inventado"])
def test_ningun_otro_rol_puede_gestionar_el_rol_de_super_administrador(actor):
    assert not puede_gestionar_rol(actor, RolUsuario.SUPER_ADMINISTRADOR)


@pytest.mark.parametrize("rol", [rol for rol in RolUsuario if rol != RolUsuario.SUPER_ADMINISTRADOR])
def test_cualquier_actor_con_poder_puede_gestionar_los_demas_roles(rol):
    assert puede_gestionar_rol("administrador_general", rol)
    assert puede_gestionar_rol("super_administrador", rol)


def test_acepta_el_rol_como_texto_o_como_enum():
    assert not puede_gestionar_rol("administrador_general", "super_administrador")
    assert puede_gestionar_rol("super_administrador", "super_administrador")
