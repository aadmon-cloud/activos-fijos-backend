from unittest.mock import AsyncMock

from shared.domain.permisos import (
    CLAVES_BASE,
    CLAVES_FUNCIONES,
    PERMISOS_EXCLUSIVOS_SUPER_ADMINISTRADOR,
    permisos_por_defecto,
)
from shared.domain.roles import ROL_EMPLEADO, ROL_SUPER_ADMINISTRADOR
from shared.infrastructure.security.consulta_permisos_rol_mongo import ConsultaPermisosRolMongo


def _consulta(documento: dict | None, segundos_de_cache: float = 60.0):
    consulta = ConsultaPermisosRolMongo(segundos_de_cache=segundos_de_cache)
    consulta._leer_documento = AsyncMock(return_value=documento)
    return consulta


async def test_el_super_administrador_tiene_todo_sin_consultar_la_base():
    consulta = _consulta(None)

    permisos = await consulta.obtener(ROL_SUPER_ADMINISTRADOR)

    assert permisos == CLAVES_FUNCIONES | frozenset(PERMISOS_EXCLUSIVOS_SUPER_ADMINISTRADOR)
    consulta._leer_documento.assert_not_awaited()


async def test_un_rol_desconocido_no_recibe_nada_ni_consulta_la_base():
    consulta = _consulta({"permisos": sorted(CLAVES_FUNCIONES)})

    assert await consulta.obtener("rol-inventado") == frozenset()
    consulta._leer_documento.assert_not_awaited()


async def test_sin_documento_rige_la_matriz_de_fabrica():
    consulta = _consulta(None)

    assert await consulta.obtener(ROL_EMPLEADO) == permisos_por_defecto(ROL_EMPLEADO)


async def test_con_documento_rige_lo_guardado():
    consulta = _consulta({"permisos": ["home-ver", "cuenta-ver", "usuarios-ver"]})

    assert await consulta.obtener(ROL_EMPLEADO) == {"home-ver", "cuenta-ver", "usuarios-ver"}


async def test_las_funciones_base_se_mantienen_aunque_el_documento_las_quite():
    consulta = _consulta({"permisos": ["usuarios-ver"]})

    permisos = await consulta.obtener(ROL_EMPLEADO)

    assert CLAVES_BASE <= permisos
    assert "usuarios-ver" in permisos


async def test_se_ignoran_claves_que_ya_no_existen_en_el_catalogo():
    consulta = _consulta({"permisos": ["home-ver", "cuenta-ver", "funcion-borrada"]})

    assert "funcion-borrada" not in await consulta.obtener(ROL_EMPLEADO)


async def test_un_documento_no_puede_dar_funciones_exclusivas_del_super_administrador():
    consulta = _consulta({"permisos": ["home-ver", "cuenta-ver", "administracion-ver"]})

    assert "administracion-ver" not in await consulta.obtener(ROL_EMPLEADO)


async def test_la_segunda_consulta_dentro_del_tiempo_usa_la_cache():
    consulta = _consulta({"permisos": ["home-ver", "cuenta-ver"]})

    await consulta.obtener(ROL_EMPLEADO)
    await consulta.obtener(ROL_EMPLEADO)

    assert consulta._leer_documento.await_count == 1


async def test_invalidar_hace_que_el_cambio_se_vea_de_inmediato():
    consulta = _consulta({"permisos": ["home-ver", "cuenta-ver"]})
    await consulta.obtener(ROL_EMPLEADO)

    consulta._leer_documento.return_value = {"permisos": ["home-ver", "cuenta-ver", "usuarios-ver"]}
    consulta.invalidar()

    assert "usuarios-ver" in await consulta.obtener(ROL_EMPLEADO)


async def test_con_cache_en_cero_siempre_consulta_la_base():
    consulta = _consulta({"permisos": ["home-ver", "cuenta-ver"]}, segundos_de_cache=0)

    await consulta.obtener(ROL_EMPLEADO)
    await consulta.obtener(ROL_EMPLEADO)

    assert consulta._leer_documento.await_count == 2
