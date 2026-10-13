from dataclasses import replace

from modules.activos.application.dto.entrada_historial_dto import (
    EntradaHistorialDTO,
    entrada_historial_a_dto,
)
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.historial_activo_repository import (
    HistorialActivoRepositoryPort,
)
from modules.activos.application.ports.resolutor_nombres import (
    NombresReferencias,
    ReferenciasActivo,
    ResolutorNombresPort,
)
from modules.activos.domain.errors import ActivoNoEncontradoError


def _nombre_de(campo: str | None, id_: str | None, nombres: NombresReferencias) -> str | None:
    """Nombre vigente de un id guardado en el historial; None si el campo no es una referencia."""
    if campo is None or id_ is None:
        return None
    if campo == "responsable_id":
        return nombres.responsables.get(id_)
    if campo == "area_id":
        return nombres.areas.get(id_)
    if campo == "sede_id":
        return nombres.sedes.get(id_)
    if campo == "lugar_id":
        return nombres.lugares.get(id_)
    if campo == "condicion_id":
        condicion = nombres.condiciones.get(id_)
        return condicion.nombre if condicion else None

    return None


class ObtenerHistorialActivoService:
    def __init__(
        self,
        activo_repository: ActivoRepositoryPort,
        historial_repository: HistorialActivoRepositoryPort,
        resolutor_nombres: ResolutorNombresPort,
    ):
        self._activo_repository = activo_repository
        self._historial_repository = historial_repository
        self._resolutor_nombres = resolutor_nombres

    async def ejecutar(self, id_activo: str) -> list[EntradaHistorialDTO]:
        if await self._activo_repository.obtener_por_id(id_activo) is None:
            raise ActivoNoEncontradoError(id_activo)

        entradas = await self._historial_repository.listar_por_activo(id_activo)
        if not entradas:
            return []

        # El historial guarda ids; se resuelven a nombres para que sea legible.
        ids_por_campo: dict[str, set[str]] = {}
        for entrada in entradas:
            if entrada.campo is None:
                continue  # una nota no referencia ids
            ids_por_campo.setdefault(entrada.campo, set()).update(
                (entrada.valor_anterior, entrada.valor_nuevo)
            )
        nombres = await self._resolutor_nombres.resolver(
            ReferenciasActivo(
                responsable_ids=ids_por_campo.get("responsable_id", set()),
                area_ids=ids_por_campo.get("area_id", set()),
                condicion_ids=ids_por_campo.get("condicion_id", set()),
                sede_ids=ids_por_campo.get("sede_id", set()),
                lugar_ids=ids_por_campo.get("lugar_id", set()),
            )
        )

        return [
            replace(
                entrada_historial_a_dto(entrada),
                valor_anterior_nombre=_nombre_de(entrada.campo, entrada.valor_anterior, nombres),
                valor_nuevo_nombre=_nombre_de(entrada.campo, entrada.valor_nuevo, nombres),
            )
            for entrada in entradas
        ]
