from dataclasses import replace
from datetime import UTC, datetime

from modules.activos.application.dto.activo_dto import ActivoDTO, activo_a_dto
from modules.activos.application.dto.actualizar_activo_dto import ActualizarActivoDTO
from modules.activos.application.dto.complemento_dto import dto_a_complemento
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.historial_activo_repository import (
    HistorialActivoRepositoryPort,
)
from modules.activos.domain.entities import Activo, EntradaHistorialActivo
from modules.activos.domain.errors import (
    ActivoNoEncontradoError,
    ActivoValorInvalidoError,
    ComplementoCantidadInvalidaError,
)
from shared.domain.entities.audit import AuditPersona

_CAMPOS_CON_HISTORIAL = ("responsable_id", "area_id", "condicion_id", "sede_id", "lugar_id")


class ActualizarActivoService:
    def __init__(
        self,
        activo_repository: ActivoRepositoryPort,
        historial_repository: HistorialActivoRepositoryPort,
    ):
        self._activo_repository = activo_repository
        self._historial_repository = historial_repository

    async def ejecutar(self, dto: ActualizarActivoDTO) -> ActivoDTO:
        activo = await self._activo_repository.obtener_por_id(dto.id_activo)
        if activo is None:
            raise ActivoNoEncontradoError(dto.id_activo)

        if dto.valor is not None and dto.valor <= 0:
            raise ActivoValorInvalidoError()

        complementos_nuevos = activo.complementos
        if dto.complementos is not None:
            for complemento_dto in dto.complementos:
                if complemento_dto.cantidad < 1:
                    raise ComplementoCantidadInvalidaError(complemento_dto.nombre)
            complementos_nuevos = [dto_a_complemento(c) for c in dto.complementos]

        audit = AuditPersona(
            id_persona=dto.actualizado_por_id,
            nombre=dto.actualizado_por_nombre,
            fecha=datetime.now(UTC),
        )

        activo_actualizado = replace(
            activo,
            nombre=dto.nombre if dto.nombre is not None else activo.nombre,
            marca=dto.marca if dto.marca is not None else activo.marca,
            modelo=dto.modelo if dto.modelo is not None else activo.modelo,
            serie=dto.serie if dto.serie is not None else activo.serie,
            descripcion=dto.descripcion if dto.descripcion is not None else activo.descripcion,
            categoria_id=(
                dto.categoria_id if dto.categoria_id is not None else activo.categoria_id
            ),
            area_id=dto.area_id if dto.area_id is not None else activo.area_id,
            responsable_id=(
                dto.responsable_id if dto.responsable_id is not None else activo.responsable_id
            ),
            condicion_id=(
                dto.condicion_id if dto.condicion_id is not None else activo.condicion_id
            ),
            sede_id=dto.sede_id if dto.sede_id is not None else activo.sede_id,
            lugar_id=dto.lugar_id if dto.lugar_id is not None else activo.lugar_id,
            valor=dto.valor if dto.valor is not None else activo.valor,
            fecha_adquisicion=(
                dto.fecha_adquisicion
                if dto.fecha_adquisicion is not None
                else activo.fecha_adquisicion
            ),
            complementos=complementos_nuevos,
            observaciones=(
                dto.observaciones if dto.observaciones is not None else activo.observaciones
            ),
            foto_url=dto.foto_url if dto.foto_url is not None else activo.foto_url,
            ficha_tecnica_url=(
                dto.ficha_tecnica_url
                if dto.ficha_tecnica_url is not None
                else activo.ficha_tecnica_url
            ),
            actualizado_por=audit,
        )

        await self._registrar_cambios(activo, activo_actualizado, audit)

        activo_guardado = await self._activo_repository.guardar(activo_actualizado)
        return activo_a_dto(activo_guardado)

    async def _registrar_cambios(
        self, anterior: Activo, nuevo: Activo, audit: AuditPersona
    ) -> None:
        for campo in _CAMPOS_CON_HISTORIAL:
            valor_anterior = getattr(anterior, campo)
            valor_nuevo = getattr(nuevo, campo)
            if valor_anterior != valor_nuevo:
                await self._historial_repository.registrar(
                    EntradaHistorialActivo(
                        id=None,
                        activo_id=anterior.id,
                        campo=campo,
                        valor_anterior=str(valor_anterior),
                        valor_nuevo=str(valor_nuevo),
                        modificado_por=audit,
                    )
                )
