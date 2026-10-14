from modules.permisos.application.dto.matriz_dto import FuncionDTO, MatrizDTO, RolMatrizDTO
from modules.permisos.application.ports.permisos_repository import PermisosRolRepositoryPort
from shared.domain.permisos import CLAVES_BASE, CLAVES_FUNCIONES, FUNCIONES, permisos_por_defecto
from shared.domain.roles import ETIQUETAS_ROL, ROL_SUPER_ADMINISTRADOR, ROLES_EDITABLES


class ObtenerMatrizPermisosService:
    """Catalogo de funciones y que funciones tiene habilitadas cada rol."""

    def __init__(self, permisos_repository: PermisosRolRepositoryPort):
        self._permisos_repository = permisos_repository

    async def ejecutar(self) -> MatrizDTO:
        guardados = {item.rol: item for item in await self._permisos_repository.listar()}

        roles = [
            # El Super administrador no esta en la base: siempre lo tiene todo y no se edita.
            RolMatrizDTO(
                rol=ROL_SUPER_ADMINISTRADOR,
                etiqueta=ETIQUETAS_ROL[ROL_SUPER_ADMINISTRADOR],
                editable=False,
                permisos=sorted(CLAVES_FUNCIONES),
            )
        ]

        for rol in ROLES_EDITABLES:
            guardado = guardados.get(rol)

            # Sin documento (base nueva) rige la matriz de fabrica; las funciones base nunca faltan.
            permisos = set(guardado.permisos) & CLAVES_FUNCIONES if guardado else set(permisos_por_defecto(rol))
            roles.append(
                RolMatrizDTO(
                    rol=rol,
                    etiqueta=ETIQUETAS_ROL[rol],
                    editable=True,
                    permisos=sorted(permisos | CLAVES_BASE),
                )
            )

        funciones = [FuncionDTO(f.clave, f.modulo, f.etiqueta, f.descripcion, f.es_base) for f in FUNCIONES]
        return MatrizDTO(funciones=funciones, roles=roles)
