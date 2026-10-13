from datetime import UTC, datetime

from modules.movimientos.application.avisos import EventoMovimiento, avisar
from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO, movimiento_a_dto
from modules.movimientos.application.dto.solicitar_movimiento_dto import SolicitarMovimientoDTO
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.ports.verificador_usuario_port import VerificadorUsuarioPort
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    ItemMovimiento,
    Movimiento,
    SentidoPrestamo,
    TipoMovimiento,
)
from modules.movimientos.domain.errors import (
    ActivoNoDisponibleError,
    ActivoNoEncontradoParaMovimientoError,
    ActivosMovimientoObligatoriosError,
    BajaDeUnSoloActivoError,
    DescripcionMovimientoVaciaError,
    DestinatarioIgualAlResponsableError,
    DestinatarioNoPermitidoError,
    EventoNombreObligatorioError,
    FechasMovimientoInvalidasError,
    MovimientoActivoYaExisteError,
    NoEsResponsableDelActivoError,
    SentidoPrestamoObligatorioError,
    SolicitudDeBajaRequiereAdminError,
    UsuarioDestinoNoEncontradoError,
    UsuarioDestinoObligatorioError,
)
from modules.movimientos.domain.permisos import es_administrador
from modules.movimientos.domain.transiciones import calcular_estado
from shared.application.notifications.ports import NotificadorPort
from shared.domain.entities.audit import AuditPersona

_TIPOS_CON_DESTINO = (TipoMovimiento.PRESTAMO, TipoMovimiento.SALIDA_EVENTO)
_ESTADO_DISPONIBLE = "disponible"


class SolicitarMovimientoService:
    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        activo_movimiento: ActivoMovimientoPort,
        verificador_usuario: VerificadorUsuarioPort,
        notificador: NotificadorPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._activo_movimiento = activo_movimiento
        self._verificador_usuario = verificador_usuario
        self._notificador = notificador

    async def ejecutar(self, dto: SolicitarMovimientoDTO) -> MovimientoDTO:
        es_admin = es_administrador(dto.solicitante_rol)
        if dto.tipo == TipoMovimiento.BAJA and not es_admin:
            raise SolicitudDeBajaRequiereAdminError()

        activo_ids = list(dict.fromkeys(dto.activo_ids))
        self._validar(dto, activo_ids)
        destino_id = self._resolver_destino(dto, es_admin)

        resumenes = await self._activo_movimiento.obtener_resumenes(activo_ids)
        for activo_id in activo_ids:
            if activo_id not in resumenes:
                raise ActivoNoEncontradoParaMovimientoError(activo_id)

        if dto.tipo in _TIPOS_CON_DESTINO:
            for activo_id in activo_ids:
                if resumenes[activo_id].estado_ciclo_vida != _ESTADO_DISPONIBLE:
                    raise ActivoNoDisponibleError(activo_id)
            if not await self._verificador_usuario.existe(destino_id):
                raise UsuarioDestinoNoEncontradoError(destino_id)

        ocupados = await self._movimiento_repository.activos_ocupados(activo_ids)
        for activo_id in activo_ids:
            if activo_id in ocupados:
                raise MovimientoActivoYaExisteError(activo_id)

        if dto.tipo == TipoMovimiento.PRESTAMO and dto.sentido == SentidoPrestamo.PRESTAR:
            for activo_id in activo_ids:
                responsable = resumenes[activo_id].responsable_id
                if not es_admin and responsable != dto.solicitante_id:
                    raise NoEsResponsableDelActivoError(activo_id)
                if responsable == destino_id:
                    raise DestinatarioIgualAlResponsableError()

        items = [
            self._crear_item(dto, activo_id, resumenes[activo_id].responsable_id) for activo_id in activo_ids
        ]
        con_destino = dto.tipo in _TIPOS_CON_DESTINO

        movimiento = Movimiento(
            id=None,
            tipo=dto.tipo,
            sentido=dto.sentido if dto.tipo == TipoMovimiento.PRESTAMO else None,
            items=items,
            usuario_destino_id=destino_id if con_destino else None,
            descripcion=dto.descripcion,
            evento_nombre=dto.evento_nombre if dto.tipo == TipoMovimiento.SALIDA_EVENTO else None,
            fecha_salida_estimada=dto.fecha_salida_estimada if con_destino else None,
            fecha_retorno_estimada=dto.fecha_retorno_estimada if con_destino else None,
            fecha_entrega_real=None,
            fecha_devolucion_real=None,
            estado=calcular_estado(dto.tipo, items, EstadoMovimiento.SOLICITADO),
            aprobado_por_admin=None,
            comprobante_archivo_id=None,
            creado_por=AuditPersona(
                id_persona=dto.solicitante_id,
                nombre=dto.solicitante_nombre,
                fecha=datetime.now(UTC),
            ),
            actualizado_por=None,
        )

        movimiento_guardado = await self._movimiento_repository.guardar(movimiento)
        await avisar(self._notificador, EventoMovimiento.SOLICITADO, movimiento_guardado, resumenes)

        return movimiento_a_dto(movimiento_guardado)

    @staticmethod
    def _crear_item(dto: SolicitarMovimientoDTO, activo_id: str, responsable_id: str) -> ItemMovimiento:
        # La baja la decide solo administracion. En los demas, si quien lo pide ya es el responsable del activo,
        # ese paso esta dado: el activo espera directamente a administracion.
        ya_aprobado_por_responsable = dto.tipo == TipoMovimiento.BAJA or responsable_id == dto.solicitante_id
        estado = (
            EstadoItemMovimiento.PENDIENTE_ADMIN
            if ya_aprobado_por_responsable
            else EstadoItemMovimiento.PENDIENTE_RESPONSABLE
        )

        return ItemMovimiento(activo_id=activo_id, responsable_original_id=responsable_id, estado=estado)

    @staticmethod
    def _validar(dto: SolicitarMovimientoDTO, activo_ids: list[str]) -> None:
        if not dto.descripcion or not dto.descripcion.strip():
            raise DescripcionMovimientoVaciaError()

        if not activo_ids:
            raise ActivosMovimientoObligatoriosError()

        if dto.tipo == TipoMovimiento.BAJA and len(activo_ids) != 1:
            raise BajaDeUnSoloActivoError()

        if dto.tipo == TipoMovimiento.PRESTAMO and dto.sentido is None:
            raise SentidoPrestamoObligatorioError()

        if dto.tipo == TipoMovimiento.SALIDA_EVENTO and not (dto.evento_nombre or "").strip():
            raise EventoNombreObligatorioError()

        if (
            dto.fecha_salida_estimada
            and dto.fecha_retorno_estimada
            and dto.fecha_retorno_estimada < dto.fecha_salida_estimada
        ):
            raise FechasMovimientoInvalidasError()

    @staticmethod
    def _resolver_destino(dto: SolicitarMovimientoDTO, es_admin: bool) -> str | None:
        """Quien recibe los activos. Al prestar se elige; en los demas casos es quien lo pide, salvo que un
        administrador lo monte para otra persona."""
        if dto.tipo not in _TIPOS_CON_DESTINO:
            return None

        presta = dto.tipo == TipoMovimiento.PRESTAMO and dto.sentido == SentidoPrestamo.PRESTAR
        if presta:
            if not dto.usuario_destino_id:
                raise UsuarioDestinoObligatorioError()

            return dto.usuario_destino_id

        destino = dto.usuario_destino_id or dto.solicitante_id
        if destino != dto.solicitante_id and not es_admin:
            raise DestinatarioNoPermitidoError()

        return destino
