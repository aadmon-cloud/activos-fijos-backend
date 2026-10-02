from typing import Annotated

from fastapi import Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.aprobaciones_pendientes.application.dto.listar_movimientos_pendientes import (
    ListarMovimientosPendientesInput,
)
from modules.aprobaciones_pendientes.application.ports.movimiento_pendiente_repository import (
    MovimientoPendienteRepositoryPort,
)
from modules.aprobaciones_pendientes.application.services.confirmar_movimiento_pendiente import (
    ConfirmarMovimientoPendienteService,
)
from modules.aprobaciones_pendientes.application.services.eliminar_movimiento_pendiente import (
    EliminarMovimientoPendienteService,
)
from modules.aprobaciones_pendientes.application.services.eliminar_movimientos_pendientes_multiples import (
    EliminarMovimientosPendientesMultiplesService,
)
from modules.aprobaciones_pendientes.application.services.listar_movimientos_pendientes import (
    ListarMovimientosPendientesService,
)
from modules.aprobaciones_pendientes.application.services.proponer_entrada import (
    ProponerEntradaService,
)
from modules.aprobaciones_pendientes.application.services.proponer_entrada_multiple import (
    ProponerEntradaMultipleService,
)
from modules.aprobaciones_pendientes.application.services.proponer_salida import (
    ProponerSalidaService,
)
from modules.aprobaciones_pendientes.application.services.proponer_salida_multiple import (
    ProponerSalidaMultipleService,
)
from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    EstadoMovimientoPendiente,
    TipoPropuesto,
)
from modules.aprobaciones_pendientes.infrastructure.persistence.mongo.movimiento_pendiente_repository import (
    MongoMovimientoPendienteRepository,
)
from modules.movimientos.application.ports.ejecutor_de_movimientos import (
    EjecutorDeMovimientosPort,
)
from modules.movimientos.infrastructure.api.dependencies import get_ejecutor_de_movimientos
from shared.application.persistence.unit_of_work import UnitOfWorkFactory
from shared.infrastructure.api.dependencies.mongo import get_mongo_db
from shared.infrastructure.persistence.mongo.unit_of_work import MongoUnitOfWork


def get_movimiento_pendiente_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> MovimientoPendienteRepositoryPort:
    return MongoMovimientoPendienteRepository(db)


def get_unit_of_work_factory() -> UnitOfWorkFactory:
    return lambda: MongoUnitOfWork()


def get_proponer_entrada_service(
    movimiento_pendiente_repository: Annotated[
        MovimientoPendienteRepositoryPort, Depends(get_movimiento_pendiente_repository)
    ],
) -> ProponerEntradaService:
    return ProponerEntradaService(movimiento_pendiente_repository)


def get_proponer_entrada_multiple_service(
    movimiento_pendiente_repository: Annotated[
        MovimientoPendienteRepositoryPort, Depends(get_movimiento_pendiente_repository)
    ],
) -> ProponerEntradaMultipleService:
    return ProponerEntradaMultipleService(movimiento_pendiente_repository)


def get_proponer_salida_service(
    movimiento_pendiente_repository: Annotated[
        MovimientoPendienteRepositoryPort, Depends(get_movimiento_pendiente_repository)
    ],
) -> ProponerSalidaService:
    return ProponerSalidaService(movimiento_pendiente_repository)


def get_proponer_salida_multiple_service(
    movimiento_pendiente_repository: Annotated[
        MovimientoPendienteRepositoryPort, Depends(get_movimiento_pendiente_repository)
    ],
) -> ProponerSalidaMultipleService:
    return ProponerSalidaMultipleService(movimiento_pendiente_repository)


def get_listar_movimientos_pendientes_input(
    estado: EstadoMovimientoPendiente | None = None,
    tipo_propuesto: TipoPropuesto | None = None,
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=200),
) -> ListarMovimientosPendientesInput:
    return ListarMovimientosPendientesInput(
        estado=estado, tipo_propuesto=tipo_propuesto, pagina=pagina, limite=limite
    )


def get_listar_movimientos_pendientes_service(
    movimiento_pendiente_repository: Annotated[
        MovimientoPendienteRepositoryPort, Depends(get_movimiento_pendiente_repository)
    ],
) -> ListarMovimientosPendientesService:
    return ListarMovimientosPendientesService(movimiento_pendiente_repository)


def get_eliminar_movimiento_pendiente_service(
    movimiento_pendiente_repository: Annotated[
        MovimientoPendienteRepositoryPort, Depends(get_movimiento_pendiente_repository)
    ],
) -> EliminarMovimientoPendienteService:
    return EliminarMovimientoPendienteService(movimiento_pendiente_repository)


def get_eliminar_movimientos_pendientes_multiples_service(
    movimiento_pendiente_repository: Annotated[
        MovimientoPendienteRepositoryPort, Depends(get_movimiento_pendiente_repository)
    ],
) -> EliminarMovimientosPendientesMultiplesService:
    return EliminarMovimientosPendientesMultiplesService(movimiento_pendiente_repository)


def get_confirmar_movimiento_pendiente_service(
    movimiento_pendiente_repository: Annotated[
        MovimientoPendienteRepositoryPort, Depends(get_movimiento_pendiente_repository)
    ],
    ejecutor_de_movimientos: Annotated[
        EjecutorDeMovimientosPort, Depends(get_ejecutor_de_movimientos)
    ],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> ConfirmarMovimientoPendienteService:
    return ConfirmarMovimientoPendienteService(
        movimiento_pendiente_repository, ejecutor_de_movimientos, unit_of_work_factory
    )
