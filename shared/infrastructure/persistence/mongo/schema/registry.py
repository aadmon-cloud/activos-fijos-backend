from modules.aprobaciones_pendientes.infrastructure.persistence.mongo.schema.movimientos_pendientes_collection import (
    MOVIMIENTOS_PENDIENTES_COLLECTION,
)
from modules.auth.infrastructure.persistence.mongo.schema.usuarios_collection import (
    USUARIOS_COLLECTION,
)
from modules.ejemplo_tareas.infrastructure.persistence.mongo.schema.tareas_collection import (
    TAREAS_COLLECTION,
)
from modules.productos.infrastructure.persistence.mongo.schema.catalogo_productos_collection import (
    CATALOGO_PRODUCTOS_COLLECTION,
)
from modules.mercados_predefinidos.infrastructure.persistence.mongo.schema.catalogo_mercados_predefinidos_collection import (
    CATALOGO_MERCADOS_PREDEFINIDOS_COLLECTION,
)
from modules.movimientos.infrastructure.persistence.mongo.schema.contadores_movimientos_collection import (
    CONTADORES_MOVIMIENTOS_COLLECTION,
)
from modules.movimientos.infrastructure.persistence.mongo.schema.registro_movimientos_collection import (
    REGISTRO_MOVIMIENTOS_COLLECTION,
)
from modules.reservas.infrastructure.persistence.mongo.schema.reservas_stock_collection import (
    RESERVAS_STOCK_COLLECTION,
)
from modules.ubicaciones.infrastructure.persistence.mongo.schema.stock_ubicaciones_collection import (
    STOCK_UBICACIONES_COLLECTION,
)
from shared.infrastructure.persistence.mongo.schema.definitions import (
    MongoCollectionDefinition,
)


def obtener_colecciones_mongo() -> list[MongoCollectionDefinition]:
    """Retorna las definiciones de colecciones administradas por el proyecto."""
    return [
        TAREAS_COLLECTION,
        USUARIOS_COLLECTION,
        CATALOGO_PRODUCTOS_COLLECTION,
        STOCK_UBICACIONES_COLLECTION,
        CATALOGO_MERCADOS_PREDEFINIDOS_COLLECTION,
        RESERVAS_STOCK_COLLECTION,
        REGISTRO_MOVIMIENTOS_COLLECTION,
        CONTADORES_MOVIMIENTOS_COLLECTION,
        MOVIMIENTOS_PENDIENTES_COLLECTION,
    ]
