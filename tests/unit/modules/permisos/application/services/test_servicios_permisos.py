from dataclasses import replace

import pytest

from modules.permisos.application.dto.actualizar_permisos_rol_dto import (
    ActualizarPermisosRolDTO,
    RestablecerPermisosRolDTO,
)
from modules.permisos.application.ports.permisos_repository import PermisosRolRepositoryPort
from modules.permisos.application.services.actualizar_permisos_rol import ActualizarPermisosRolService
from modules.permisos.application.services.asegurar_permisos_por_defecto import (
    AsegurarPermisosPorDefectoService,
)
from modules.permisos.application.services.listar_historial import ListarHistorialPermisosService
from modules.permisos.application.services.obtener_matriz import ObtenerMatrizPermisosService
from modules.permisos.application.services.restablecer_permisos_rol import RestablecerPermisosRolService
from modules.permisos.domain.entities import AccionPermiso, CambioPermiso, PermisosRol
from modules.permisos.domain.errors import (
    PermisoBaseNoDeshabilitableError,
    PermisoDesconocidoError,
    RolDesconocidoError,
    RolNoEditableError,
)
from shared.domain.permisos import CLAVES_BASE, CLAVES_FUNCIONES, FUNCIONES, permisos_por_defecto
from shared.domain.roles import ROLES_EDITABLES


class _RepositorioEnMemoria(PermisosRolRepositoryPort):
    def __init__(self):
        self.documentos: dict[str, PermisosRol] = {}
        self.historial: list[CambioPermiso] = []
        self.escrituras = 0

    async def obtener(self, rol):
        return self.documentos.get(rol)

    async def listar(self):
        return list(self.documentos.values())

    async def guardar(self, permisos_rol):
        self.escrituras += 1
        guardado = replace(permisos_rol, id=permisos_rol.id or f"id-{permisos_rol.rol}")
        self.documentos[guardado.rol] = guardado
        return guardado

    async def registrar_cambios(self, cambios):
        self.historial.extend(cambios)

    async def listar_historial(self, rol, skip, limit):
        cambios = [c for c in reversed(self.historial) if rol is None or c.rol == rol]
        return cambios[skip : skip + limit]


@pytest.fixture
def repo():
    return _RepositorioEnMemoria()


def _dto(rol, permisos):
    return ActualizarPermisosRolDTO(rol=rol, permisos=list(permisos), actor_id="s1", actor_nombre="Super")


# ObtenerMatrizPermisosService


async def test_la_matriz_lista_el_catalogo_completo_y_los_siete_roles(repo):
    matriz = await ObtenerMatrizPermisosService(repo).ejecutar()

    assert [f.clave for f in matriz.funciones] == [f.clave for f in FUNCIONES]
    assert [r.rol for r in matriz.roles] == ["super_administrador", *ROLES_EDITABLES]


async def test_el_super_administrador_aparece_con_todo_y_no_editable(repo):
    matriz = await ObtenerMatrizPermisosService(repo).ejecutar()

    super_admin = matriz.roles[0]
    assert super_admin.editable is False
    assert set(super_admin.permisos) == CLAVES_FUNCIONES


async def test_sin_documentos_la_matriz_muestra_los_valores_de_fabrica(repo):
    matriz = await ObtenerMatrizPermisosService(repo).ejecutar()

    for rol in matriz.roles[1:]:
        assert rol.editable is True
        assert set(rol.permisos) == permisos_por_defecto(rol.rol)


async def test_la_matriz_muestra_lo_guardado_y_siempre_las_funciones_base(repo):
    await ActualizarPermisosRolService(repo).ejecutar(_dto("empleado", [*CLAVES_BASE, "usuarios-ver"]))

    matriz = await ObtenerMatrizPermisosService(repo).ejecutar()

    empleado = next(r for r in matriz.roles if r.rol == "empleado")
    assert set(empleado.permisos) == {*CLAVES_BASE, "usuarios-ver"}


# ActualizarPermisosRolService


async def test_actualizar_guarda_la_lista_pedida_y_la_devuelve_ordenada(repo):
    resultado = await ActualizarPermisosRolService(repo).ejecutar(
        _dto("empleado", ["usuarios-ver", *CLAVES_BASE])
    )

    assert resultado.rol == "empleado"
    assert resultado.etiqueta == "Empleado"
    assert resultado.permisos == sorted(["usuarios-ver", *CLAVES_BASE])
    assert set(repo.documentos["empleado"].permisos) == {"usuarios-ver", *CLAVES_BASE}


async def test_actualizar_registra_cada_funcion_habilitada_y_deshabilitada(repo):
    base_fabrica = permisos_por_defecto("empleado")
    nuevos = (base_fabrica - {"solicitudes-crear"}) | {"usuarios-ver"}

    await ActualizarPermisosRolService(repo).ejecutar(_dto("empleado", nuevos))

    registrado = {(c.permiso, c.accion) for c in repo.historial}
    assert registrado == {
        ("usuarios-ver", AccionPermiso.HABILITADO),
        ("solicitudes-crear", AccionPermiso.DESHABILITADO),
    }
    assert all(c.por.id_persona == "s1" and c.por.nombre == "Super" for c in repo.historial)


async def test_actualizar_guarda_quien_lo_cambio(repo):
    await ActualizarPermisosRolService(repo).ejecutar(_dto("empleado", [*CLAVES_BASE]))

    assert repo.documentos["empleado"].actualizado_por.id_persona == "s1"


async def test_actualizar_conserva_el_creador_y_el_id_en_cambios_posteriores(repo):
    servicio = ActualizarPermisosRolService(repo)
    await servicio.ejecutar(_dto("empleado", [*CLAVES_BASE]))
    creado_por = repo.documentos["empleado"].creado_por

    await servicio.ejecutar(ActualizarPermisosRolDTO("empleado", [*CLAVES_BASE, "usuarios-ver"], "s2", "Otro"))

    assert repo.documentos["empleado"].creado_por == creado_por
    assert repo.documentos["empleado"].actualizado_por.id_persona == "s2"
    assert repo.documentos["empleado"].id == "id-empleado"


async def test_actualizar_sin_cambios_no_escribe_ni_registra_historial(repo):
    servicio = ActualizarPermisosRolService(repo)
    await servicio.ejecutar(_dto("empleado", [*CLAVES_BASE, "usuarios-ver"]))
    escrituras, historial = repo.escrituras, len(repo.historial)

    await servicio.ejecutar(_dto("empleado", [*CLAVES_BASE, "usuarios-ver"]))

    assert (repo.escrituras, len(repo.historial)) == (escrituras, historial)


async def test_actualizar_acepta_el_orden_y_repetidos_sin_contarlos_como_cambio(repo):
    servicio = ActualizarPermisosRolService(repo)
    await servicio.ejecutar(_dto("empleado", [*CLAVES_BASE, "usuarios-ver"]))
    escrituras = repo.escrituras

    await servicio.ejecutar(_dto("empleado", ["usuarios-ver", "usuarios-ver", *reversed(sorted(CLAVES_BASE))]))

    assert repo.escrituras == escrituras


async def test_actualizar_rechaza_el_rol_del_super_administrador(repo):
    with pytest.raises(RolNoEditableError):
        await ActualizarPermisosRolService(repo).ejecutar(_dto("super_administrador", [*CLAVES_BASE]))

    assert repo.escrituras == 0


async def test_actualizar_rechaza_un_rol_inexistente(repo):
    with pytest.raises(RolDesconocidoError):
        await ActualizarPermisosRolService(repo).ejecutar(_dto("rol-inventado", [*CLAVES_BASE]))


async def test_actualizar_rechaza_una_funcion_que_no_existe_y_no_guarda_nada(repo):
    with pytest.raises(PermisoDesconocidoError):
        await ActualizarPermisosRolService(repo).ejecutar(_dto("empleado", [*CLAVES_BASE, "usuarios-volar"]))

    assert repo.escrituras == 0 and repo.historial == []


async def test_actualizar_no_deja_quitar_una_funcion_base(repo):
    with pytest.raises(PermisoBaseNoDeshabilitableError):
        await ActualizarPermisosRolService(repo).ejecutar(_dto("empleado", ["home-ver"]))

    assert repo.escrituras == 0


# RestablecerPermisosRolService


async def test_restablecer_devuelve_el_rol_a_la_matriz_de_fabrica_y_lo_registra(repo):
    actualizar = ActualizarPermisosRolService(repo)
    await actualizar.ejecutar(_dto("empleado", [*CLAVES_BASE, "usuarios-ver"]))
    repo.historial.clear()

    resultado = await RestablecerPermisosRolService(actualizar).ejecutar(
        RestablecerPermisosRolDTO(rol="empleado", actor_id="s1", actor_nombre="Super")
    )

    assert set(resultado.permisos) == permisos_por_defecto("empleado")
    assert {(c.permiso, c.accion) for c in repo.historial} >= {("usuarios-ver", AccionPermiso.DESHABILITADO)}


async def test_restablecer_rechaza_el_rol_del_super_administrador(repo):
    servicio = RestablecerPermisosRolService(ActualizarPermisosRolService(repo))

    with pytest.raises(RolNoEditableError):
        await servicio.ejecutar(RestablecerPermisosRolDTO("super_administrador", "s1", "Super"))


# ListarHistorialPermisosService


async def test_el_historial_se_lista_del_mas_reciente_al_mas_antiguo(repo):
    actualizar = ActualizarPermisosRolService(repo)
    await actualizar.ejecutar(_dto("empleado", [*CLAVES_BASE, "usuarios-ver"]))
    await actualizar.ejecutar(_dto("empleado", [*CLAVES_BASE, "usuarios-ver", "catalogos-ver"]))

    historial = await ListarHistorialPermisosService(repo).ejecutar(rol=None, skip=0, limit=100)

    assert historial[0].permiso == "catalogos-ver"
    assert historial[0].accion == "habilitado"
    assert historial[0].por_nombre == "Super"


async def test_el_historial_se_puede_filtrar_por_rol(repo):
    actualizar = ActualizarPermisosRolService(repo)
    await actualizar.ejecutar(_dto("empleado", [*CLAVES_BASE, "usuarios-ver"]))
    await actualizar.ejecutar(_dto("jefe_area", [*CLAVES_BASE, "catalogos-ver"]))

    historial = await ListarHistorialPermisosService(repo).ejecutar(rol="jefe_area", skip=0, limit=100)

    assert {c.rol for c in historial} == {"jefe_area"}


async def test_el_historial_rechaza_un_rol_inexistente(repo):
    with pytest.raises(RolDesconocidoError):
        await ListarHistorialPermisosService(repo).ejecutar(rol="rol-inventado", skip=0, limit=10)


# AsegurarPermisosPorDefectoService


async def test_asegurar_crea_la_matriz_de_fabrica_de_todos_los_roles_editables(repo):
    creados = await AsegurarPermisosPorDefectoService(repo).ejecutar()

    assert creados == list(ROLES_EDITABLES)
    for rol in ROLES_EDITABLES:
        assert set(repo.documentos[rol].permisos) == permisos_por_defecto(rol)
    assert repo.documentos["empleado"].creado_por.id_persona == "sistema-permisos"
    assert repo.historial == []


async def test_asegurar_nunca_pisa_lo_que_ya_se_edito(repo):
    await ActualizarPermisosRolService(repo).ejecutar(_dto("empleado", [*CLAVES_BASE, "usuarios-ver"]))

    creados = await AsegurarPermisosPorDefectoService(repo).ejecutar()

    assert "empleado" not in creados
    assert set(repo.documentos["empleado"].permisos) == {*CLAVES_BASE, "usuarios-ver"}


async def test_asegurar_es_idempotente(repo):
    servicio = AsegurarPermisosPorDefectoService(repo)
    await servicio.ejecutar()

    assert await servicio.ejecutar() == []
