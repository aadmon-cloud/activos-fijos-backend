from functools import lru_cache

from modules.catalogos.application.ports.area_repository import AreaRepositoryPort
from modules.catalogos.application.ports.categoria_repository import CategoriaRepositoryPort
from modules.catalogos.application.ports.condicion_repository import CondicionRepositoryPort
from modules.catalogos.application.ports.lugar_repository import LugarRepositoryPort
from modules.catalogos.application.ports.sede_repository import SedeRepositoryPort
from modules.catalogos.application.ports.verificador_uso_en_activos import (
    VerificadorUsoEnActivosPort,
)
from modules.catalogos.application.services.actualizar_area import ActualizarAreaService
from modules.catalogos.application.services.actualizar_categoria import (
    ActualizarCategoriaService,
)
from modules.catalogos.application.services.actualizar_condicion import (
    ActualizarCondicionService,
)
from modules.catalogos.application.services.actualizar_lugar import ActualizarLugarService
from modules.catalogos.application.services.actualizar_sede import ActualizarSedeService
from modules.catalogos.application.services.crear_area import CrearAreaService
from modules.catalogos.application.services.crear_categoria import CrearCategoriaService
from modules.catalogos.application.services.crear_condicion import CrearCondicionService
from modules.catalogos.application.services.crear_lugar import CrearLugarService
from modules.catalogos.application.services.crear_sede import CrearSedeService
from modules.catalogos.application.services.eliminar_area import EliminarAreaService
from modules.catalogos.application.services.eliminar_categoria import EliminarCategoriaService
from modules.catalogos.application.services.eliminar_condicion import EliminarCondicionService
from modules.catalogos.application.services.eliminar_lugar import EliminarLugarService
from modules.catalogos.application.services.eliminar_sede import EliminarSedeService
from modules.catalogos.application.services.listar_areas import ListarAreasService
from modules.catalogos.application.services.listar_categorias import ListarCategoriasService
from modules.catalogos.application.services.listar_condiciones import ListarCondicionesService
from modules.catalogos.application.services.listar_lugares import ListarLugaresService
from modules.catalogos.application.services.listar_sedes import ListarSedesService
from modules.catalogos.application.services.obtener_area import ObtenerAreaService
from modules.catalogos.application.services.obtener_categoria import ObtenerCategoriaService
from modules.catalogos.application.services.obtener_condicion import ObtenerCondicionService
from modules.catalogos.application.services.obtener_lugar import ObtenerLugarService
from modules.catalogos.application.services.obtener_sede import ObtenerSedeService
from modules.catalogos.infrastructure.persistence.mongo.area_repository import (
    MongoAreaRepository,
)
from modules.catalogos.infrastructure.persistence.mongo.categoria_repository import (
    MongoCategoriaRepository,
)
from modules.catalogos.infrastructure.persistence.mongo.condicion_repository import (
    MongoCondicionRepository,
)
from modules.catalogos.infrastructure.persistence.mongo.lugar_repository import (
    MongoLugarRepository,
)
from modules.catalogos.infrastructure.persistence.mongo.sede_repository import (
    MongoSedeRepository,
)
from modules.catalogos.infrastructure.persistence.mongo.verificador_uso_en_activos import (
    MongoVerificadorUsoEnActivos,
)


@lru_cache(maxsize=1)
def get_area_repository() -> AreaRepositoryPort:
    return MongoAreaRepository()


@lru_cache(maxsize=1)
def get_categoria_repository() -> CategoriaRepositoryPort:
    return MongoCategoriaRepository()


@lru_cache(maxsize=1)
def get_condicion_repository() -> CondicionRepositoryPort:
    return MongoCondicionRepository()


@lru_cache(maxsize=1)
def get_sede_repository() -> SedeRepositoryPort:
    return MongoSedeRepository()


@lru_cache(maxsize=1)
def get_lugar_repository() -> LugarRepositoryPort:
    return MongoLugarRepository()


@lru_cache(maxsize=1)
def get_verificador_uso_en_activos() -> VerificadorUsoEnActivosPort:
    return MongoVerificadorUsoEnActivos()


def get_crear_area_service() -> CrearAreaService:
    return CrearAreaService(area_repository=get_area_repository())


def get_listar_areas_service() -> ListarAreasService:
    return ListarAreasService(area_repository=get_area_repository())


def get_obtener_area_service() -> ObtenerAreaService:
    return ObtenerAreaService(area_repository=get_area_repository())


def get_actualizar_area_service() -> ActualizarAreaService:
    return ActualizarAreaService(area_repository=get_area_repository())


def get_eliminar_area_service() -> EliminarAreaService:
    return EliminarAreaService(
        area_repository=get_area_repository(),
        verificador_uso=get_verificador_uso_en_activos(),
    )


def get_crear_categoria_service() -> CrearCategoriaService:
    return CrearCategoriaService(categoria_repository=get_categoria_repository())


def get_listar_categorias_service() -> ListarCategoriasService:
    return ListarCategoriasService(categoria_repository=get_categoria_repository())


def get_obtener_categoria_service() -> ObtenerCategoriaService:
    return ObtenerCategoriaService(categoria_repository=get_categoria_repository())


def get_actualizar_categoria_service() -> ActualizarCategoriaService:
    return ActualizarCategoriaService(categoria_repository=get_categoria_repository())


def get_eliminar_categoria_service() -> EliminarCategoriaService:
    return EliminarCategoriaService(
        categoria_repository=get_categoria_repository(),
        verificador_uso=get_verificador_uso_en_activos(),
    )


def get_crear_condicion_service() -> CrearCondicionService:
    return CrearCondicionService(condicion_repository=get_condicion_repository())


def get_listar_condiciones_service() -> ListarCondicionesService:
    return ListarCondicionesService(condicion_repository=get_condicion_repository())


def get_obtener_condicion_service() -> ObtenerCondicionService:
    return ObtenerCondicionService(condicion_repository=get_condicion_repository())


def get_actualizar_condicion_service() -> ActualizarCondicionService:
    return ActualizarCondicionService(condicion_repository=get_condicion_repository())


def get_eliminar_condicion_service() -> EliminarCondicionService:
    return EliminarCondicionService(
        condicion_repository=get_condicion_repository(),
        verificador_uso=get_verificador_uso_en_activos(),
    )


def get_crear_sede_service() -> CrearSedeService:
    return CrearSedeService(sede_repository=get_sede_repository())


def get_listar_sedes_service() -> ListarSedesService:
    return ListarSedesService(sede_repository=get_sede_repository())


def get_obtener_sede_service() -> ObtenerSedeService:
    return ObtenerSedeService(sede_repository=get_sede_repository())


def get_actualizar_sede_service() -> ActualizarSedeService:
    return ActualizarSedeService(sede_repository=get_sede_repository())


def get_eliminar_sede_service() -> EliminarSedeService:
    return EliminarSedeService(
        sede_repository=get_sede_repository(), lugar_repository=get_lugar_repository()
    )


def get_crear_lugar_service() -> CrearLugarService:
    return CrearLugarService(
        lugar_repository=get_lugar_repository(), sede_repository=get_sede_repository()
    )


def get_listar_lugares_service() -> ListarLugaresService:
    return ListarLugaresService(lugar_repository=get_lugar_repository())


def get_obtener_lugar_service() -> ObtenerLugarService:
    return ObtenerLugarService(lugar_repository=get_lugar_repository())


def get_actualizar_lugar_service() -> ActualizarLugarService:
    return ActualizarLugarService(lugar_repository=get_lugar_repository())


def get_eliminar_lugar_service() -> EliminarLugarService:
    return EliminarLugarService(
        lugar_repository=get_lugar_repository(),
        verificador_uso=get_verificador_uso_en_activos(),
    )
