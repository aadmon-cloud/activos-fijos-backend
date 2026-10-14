from unittest.mock import AsyncMock, patch

import pytest

from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.application.user_auth.errors import PermisosInsuficientesError
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_permiso,
    requiere_rol,
    requiere_super_administrador,
)

_MODULO = "shared.infrastructure.api.dependencies.user_authentication"


def _identidad(rol: str) -> IdentidadUsuarioAutenticada:
    return IdentidadUsuarioAutenticada(id_usuario="1", email="a@b.com", nombre="Ana", rol=rol)


# requiere_rol


def test_requiere_rol_deja_pasar_al_rol_permitido():
    verificar = requiere_rol("mantenimiento")

    assert verificar(_identidad("mantenimiento")).rol == "mantenimiento"


def test_requiere_rol_rechaza_a_otro_rol():
    with pytest.raises(PermisosInsuficientesError):
        requiere_rol("mantenimiento")(_identidad("empleado"))


def test_el_super_administrador_pasa_cualquier_guardia_de_rol():
    assert requiere_rol("mantenimiento")(_identidad("super_administrador")).rol == "super_administrador"


# requiere_super_administrador


async def test_requiere_super_administrador_deja_pasar_solo_al_super_administrador():
    assert (await requiere_super_administrador(_identidad("super_administrador"))).rol == "super_administrador"


@pytest.mark.parametrize("rol", ["administrador_general", "empleado", "rol-inventado"])
async def test_requiere_super_administrador_rechaza_a_los_demas_roles(rol):
    with pytest.raises(PermisosInsuficientesError):
        await requiere_super_administrador(_identidad(rol))


# requiere_permiso


def test_una_funcion_que_no_existe_en_el_catalogo_falla_al_declarar_la_ruta():
    with pytest.raises(ValueError, match="no existe en el catalogo"):
        requiere_permiso("usuarios-volar")


async def test_requiere_permiso_deja_pasar_a_un_rol_que_tiene_la_funcion():
    with patch(f"{_MODULO}.consulta_permisos_rol") as consulta:
        consulta.obtener = AsyncMock(return_value=frozenset({"usuarios-ver"}))

        identidad = await requiere_permiso("usuarios-ver")(_identidad("empleado"))

    assert identidad.rol == "empleado"
    consulta.obtener.assert_awaited_once_with("empleado")


async def test_requiere_permiso_rechaza_a_un_rol_que_no_tiene_la_funcion():
    with patch(f"{_MODULO}.consulta_permisos_rol") as consulta:
        consulta.obtener = AsyncMock(return_value=frozenset({"home-ver"}))

        with pytest.raises(PermisosInsuficientesError):
            await requiere_permiso("usuarios-ver")(_identidad("empleado"))


async def test_requiere_permiso_usa_la_matriz_de_fabrica_cuando_no_hay_base():
    # Sin tocar Mongo (fixture global): el Administrador General de fabrica puede crear usuarios, el empleado no.
    assert (await requiere_permiso("usuarios-crear")(_identidad("administrador_general"))).rol == "administrador_general"

    with pytest.raises(PermisosInsuficientesError):
        await requiere_permiso("usuarios-crear")(_identidad("empleado"))


async def test_el_super_administrador_siempre_pasa_requiere_permiso():
    for clave in ("usuarios-crear", "administracion-ver", "auditorias-ver"):
        assert (await requiere_permiso(clave)(_identidad("super_administrador"))).rol == "super_administrador"
