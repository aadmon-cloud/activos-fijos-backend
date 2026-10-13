from datetime import UTC, datetime

from modules.activos.application.dto.activo_dto import ActivoDTO, activo_a_dto
from modules.activos.application.dto.complemento_dto import dto_a_complemento
from modules.activos.application.dto.crear_activo_dto import CrearActivoDTO
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.domain.entities import Activo, EstadoCicloVida
from modules.activos.domain.errors import (
    ActivoNumeroInventarioDuplicadoError,
    ComplementoCantidadInvalidaError,
)
from shared.domain.entities.audit import AuditPersona


class CrearActivoService:
    def __init__(self, activo_repository: ActivoRepositoryPort):
        self._activo_repository = activo_repository

    async def ejecutar(self, dto: CrearActivoDTO) -> ActivoDTO:
        numero_inventario = dto.numero_inventario.strip().upper()

        for complemento_dto in dto.complementos:
            if complemento_dto.cantidad < 1:
                raise ComplementoCantidadInvalidaError(complemento_dto.nombre)

        existente = await self._activo_repository.obtener_por_numero_inventario(
            numero_inventario
        )
        if existente is not None:
            raise ActivoNumeroInventarioDuplicadoError(numero_inventario)

        activo = Activo(
            id=None,
            nombre=dto.nombre.strip(),
            numero_inventario=numero_inventario,
            tipo=dto.tipo,
            marca=dto.marca,
            modelo=dto.modelo,
            serie=dto.serie,
            descripcion=dto.descripcion,
            categoria_id=dto.categoria_id,
            area_id=dto.area_id,
            responsable_id=dto.responsable_id,
            condicion_id=dto.condicion_id,
            estado_ciclo_vida=EstadoCicloVida.DISPONIBLE,
            sede_id=dto.sede_id,
            lugar_id=dto.lugar_id,
            complementos=[dto_a_complemento(c) for c in dto.complementos],
            observaciones=dto.observaciones,
            foto_url=dto.foto_url,
            ficha_tecnica_url=dto.ficha_tecnica_url,
            creado_por=AuditPersona(
                id_persona=dto.creado_por_id,
                nombre=dto.creado_por_nombre,
                fecha=datetime.now(UTC),
            ),
            actualizado_por=None,
        )

        activo_guardado = await self._activo_repository.guardar(activo)
        return activo_a_dto(activo_guardado)
