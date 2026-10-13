from datetime import UTC, datetime, timedelta

from modules.mantenimientos.application.dto.crear_mantenimientos_masivo_dto import (
    CrearMantenimientosMasivoDTO,
    MantenimientoRegistradoDTO,
    ResultadoMantenimientosMasivoDTO,
)
from modules.mantenimientos.application.ports.buscador_activos_port import BuscadorActivosPort
from modules.mantenimientos.application.ports.mantenimiento_repository import (
    MantenimientoRepositoryPort,
)
from modules.mantenimientos.application.ports.verificador_tecnico_port import (
    VerificadorTecnicoPort,
)
from modules.mantenimientos.domain.entities import EstadoMantenimiento, Mantenimiento
from modules.mantenimientos.domain.errors import (
    CodigosMasivosVaciosError,
    DemasiadosCodigosMasivosError,
    TecnicoInvalidoError,
)
from shared.domain.entities.audit import AuditPersona

LIMITE_CODIGOS_MASIVO = 200


def _normalizar_codigos(codigos: list[str]) -> list[str]:
    """Normaliza como el modulo activos (sin espacios y en mayusculas, que es como guarda el numero de
    inventario), y descarta vacios y repetidos, conservando el orden de aparicion."""
    vistos: dict[str, None] = {}
    for codigo in codigos:
        limpio = (codigo or "").strip().upper()
        if limpio:
            vistos.setdefault(limpio)

    return list(vistos)


class RegistrarMantenimientosMasivoService:
    """Registra un mismo mantenimiento, ya realizado, sobre varios activos a la vez."""

    def __init__(
        self,
        mantenimiento_repository: MantenimientoRepositoryPort,
        buscador_activos: BuscadorActivosPort,
        verificador_tecnico: VerificadorTecnicoPort,
    ):
        self._mantenimiento_repository = mantenimiento_repository
        self._buscador_activos = buscador_activos
        self._verificador_tecnico = verificador_tecnico

    async def ejecutar(self, dto: CrearMantenimientosMasivoDTO) -> ResultadoMantenimientosMasivoDTO:
        codigos = _normalizar_codigos(dto.codigos)
        if not codigos:
            raise CodigosMasivosVaciosError()
        if len(codigos) > LIMITE_CODIGOS_MASIVO:
            raise DemasiadosCodigosMasivosError(LIMITE_CODIGOS_MASIVO)

        if not await self._verificador_tecnico.tiene_rol_mantenimiento(dto.tecnico_responsable_id):
            raise TecnicoInvalidoError(dto.tecnico_responsable_id)

        activos_por_codigo = await self._buscador_activos.buscar_por_codigo(codigos)
        encontrados = [codigo for codigo in codigos if codigo in activos_por_codigo]
        no_encontrados = [codigo for codigo in codigos if codigo not in activos_por_codigo]

        proxima_fecha_sugerida = (
            dto.fecha + timedelta(days=dto.frecuencia_dias)
            if dto.frecuencia_dias is not None
            else None
        )
        audit = AuditPersona(
            id_persona=dto.creado_por_id, nombre=dto.creado_por_nombre, fecha=datetime.now(UTC)
        )

        # Ya se hizo el mantenimiento: queda completado (y, con frecuencia, genera su proxima alerta).
        mantenimientos = [
            Mantenimiento(
                id=None,
                activo_id=activos_por_codigo[codigo],
                solicitud_id=None,
                tipo=dto.tipo,
                tecnico_responsable_id=dto.tecnico_responsable_id,
                fecha=dto.fecha,
                observaciones=dto.observaciones,
                costo=dto.costo,
                documentos=[],
                evidencias=[],
                estado=EstadoMantenimiento.COMPLETADO,
                frecuencia_dias=dto.frecuencia_dias,
                proxima_fecha_sugerida=proxima_fecha_sugerida,
                alerta_enviada=False,
                creado_por=audit,
                actualizado_por=None,
            )
            for codigo in encontrados
        ]

        guardados = (
            await self._mantenimiento_repository.guardar_varios(mantenimientos)
            if mantenimientos
            else []
        )

        return ResultadoMantenimientosMasivoDTO(
            registrados=[
                MantenimientoRegistradoDTO(
                    codigo=codigo, activo_id=guardado.activo_id, mantenimiento_id=guardado.id
                )
                for codigo, guardado in zip(encontrados, guardados, strict=True)
            ],
            no_encontrados=no_encontrados,
        )
