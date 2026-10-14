import time

from shared.application.user_auth.ports import ConsultaPermisosRolPort
from shared.domain.permisos import (
    CLAVES_BASE,
    CLAVES_FUNCIONES,
    PERMISOS_EXCLUSIVOS_SUPER_ADMINISTRADOR,
    permisos_por_defecto,
)
from shared.domain.roles import ROLES_EDITABLES, es_super_administrador
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Consulta la coleccion por nombre en vez de importar modules.permisos: shared no puede depender de un modulo.
_NOMBRE_COLECCION = "permisos_rol"

# Una lectura a Mongo por rol cada pocos segundos, no por peticion. Al guardar la matriz se vacia al instante en este
# proceso (`invalidar`); si hubiera varios procesos, el cambio llega a los demas en, como maximo, estos segundos.
SEGUNDOS_DE_CACHE = 5.0


class ConsultaPermisosRolMongo(ConsultaPermisosRolPort):
    def __init__(self, segundos_de_cache: float = SEGUNDOS_DE_CACHE):
        self._segundos_de_cache = segundos_de_cache
        self._cache: dict[str, tuple[float, frozenset[str]]] = {}

    def invalidar(self) -> None:
        self._cache.clear()

    async def _leer_documento(self, rol: str) -> dict | None:
        return await mongo_manager.get_database()[_NOMBRE_COLECCION].find_one({"rol": rol}, {"permisos": 1})

    async def obtener(self, rol: str) -> frozenset[str]:
        # El Super administrador siempre lo tiene todo: no depende de la matriz ni se puede bloquear.
        if es_super_administrador(rol):
            return CLAVES_FUNCIONES | frozenset(PERMISOS_EXCLUSIVOS_SUPER_ADMINISTRADOR)

        # Un rol desconocido no recibe nada (denegar por defecto).
        if rol not in ROLES_EDITABLES:
            return frozenset()

        ahora = time.monotonic()
        guardado = self._cache.get(rol)
        if guardado is not None and ahora - guardado[0] < self._segundos_de_cache:
            return guardado[1]

        doc = await self._leer_documento(rol)

        # Sin documento (base nueva) rige la matriz de fabrica. Se ignoran claves que ya no existen y las funciones
        # base siempre se mantienen, aunque alguien manipulara el documento.
        permisos = permisos_por_defecto(rol) if doc is None else frozenset(doc.get("permisos", [])) & CLAVES_FUNCIONES
        permisos = permisos | CLAVES_BASE

        self._cache[rol] = (ahora, permisos)
        return permisos


# Instancia unica: la usan la autorizacion de las rutas y el modulo de permisos (para invalidar al guardar).
consulta_permisos_rol = ConsultaPermisosRolMongo()
