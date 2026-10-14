"""Los correos de cada etapa de un movimiento: a quien avisar y con que texto.

Funciones puras (no envian nada): `avisar` las une con el notificador. Los destinatarios son los del sistema
de notificaciones (`usuario:<id>`, `rol:<rol>`); un usuario que ya no existe o esta desactivado se ignora.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from modules.movimientos.application.ports.activo_movimiento_port import ActivoResumenMovimiento
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    ItemMovimiento,
    Movimiento,
    TipoMovimiento,
)
from shared.application.notifications.enlaces import enlace
from shared.application.notifications.ports import NotificadorPort
from shared.domain.roles import ROL_ADMINISTRADOR_GENERAL, ROL_SUPER_ADMINISTRADOR

# Los avisos para "el administrador" le llegan al Administrador General y al Super administrador.
_ROLES_ADMINISTRADORES = (f"rol:{ROL_ADMINISTRADOR_GENERAL}", f"rol:{ROL_SUPER_ADMINISTRADOR}")

_ETIQUETA_TIPO = {
    TipoMovimiento.PRESTAMO: "prestamo",
    TipoMovimiento.SALIDA_EVENTO: "salida a evento",
    TipoMovimiento.BAJA: "baja",
}

_MAXIMO_ACTIVOS_EN_TEXTO = 8


class EventoMovimiento(str, Enum):
    SOLICITADO = "solicitado"
    APROBADO_RESPONSABLE = "aprobado_responsable"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    SALIDA_CONFIRMADA = "salida_confirmada"
    DEVOLUCION_SOLICITADA = "devolucion_solicitada"
    DEVOLUCION_CONFIRMADA = "devolucion_confirmada"
    BAJA_EJECUTADA = "baja_ejecutada"
    RECORDATORIO_DEVOLUCION = "recordatorio_devolucion"


@dataclass(frozen=True)
class Aviso:
    destinatarios: list[str]
    asunto: str
    cuerpo: str


def _usuario(id_usuario: str | None) -> list[str]:
    return [f"usuario:{id_usuario}"] if id_usuario else []


def _sin_repetidos(destinatarios: list[str]) -> list[str]:
    return list(dict.fromkeys(destinatarios))


def _nombre_activo(activo: ActivoResumenMovimiento | None) -> str:
    return f"{activo.nombre} ({activo.numero_inventario})" if activo and activo.nombre else "un activo"


def _lista(items: list[ItemMovimiento], activos: Mapping[str, ActivoResumenMovimiento]) -> str:
    """'Laptop (INV-1), Monitor (INV-2)'; si son muchos, los primeros y cuantos mas."""
    nombres = [_nombre_activo(activos.get(item.activo_id)) for item in items]
    if len(nombres) <= _MAXIMO_ACTIVOS_EN_TEXTO:
        return ", ".join(nombres)

    resto = len(nombres) - _MAXIMO_ACTIVOS_EN_TEXTO

    return f"{', '.join(nombres[:_MAXIMO_ACTIVOS_EN_TEXTO])} y {resto} mas"


def _titulo(items: list[ItemMovimiento], activos: Mapping[str, ActivoResumenMovimiento]) -> str:
    """Para el asunto: el activo, o 'N activos' si son varios."""
    if len(items) == 1:
        return _nombre_activo(activos.get(items[0].activo_id))

    return f"{len(items)} activos"


def _participantes(movimiento: Movimiento) -> list[str]:
    """Quien lo pidio, quien lo recibe y quienes tenian los activos."""
    responsables = [r for item in movimiento.items for r in _usuario(item.responsable_original_id)]

    return _usuario(movimiento.creado_por.id_persona) + _usuario(movimiento.usuario_destino_id) + responsables


def _cuerpo(movimiento: Movimiento, texto: str, extra: str = "") -> str:
    partes = [texto]
    if movimiento.evento_nombre:
        partes.append(f"Evento: {movimiento.evento_nombre}")
    if extra:
        partes.append(extra)
    partes.append(f"Ver el movimiento: {enlace(f'/movimientos/detalle?id={movimiento.id}')}")

    return "\n\n".join(partes)


def _con_estado(movimiento: Movimiento, *estados: EstadoItemMovimiento) -> list[ItemMovimiento]:
    return [item for item in movimiento.items if item.estado in estados]


def construir_aviso(
    evento: EventoMovimiento,
    movimiento: Movimiento,
    activos: Mapping[str, ActivoResumenMovimiento],
) -> Aviso:
    tipo = _ETIQUETA_TIPO.get(movimiento.tipo, movimiento.tipo.value)
    todos = movimiento.items
    lista, titulo = _lista(todos, activos), _titulo(todos, activos)

    if evento == EventoMovimiento.SOLICITADO:
        texto = f"{movimiento.creado_por.nombre} solicito {tipo} de: {lista}.\n\n{movimiento.descripcion}"

        # Cada responsable decide sobre sus activos; a administracion le llega cuando ya no falta ninguno.
        pendientes = _con_estado(movimiento, EstadoItemMovimiento.PENDIENTE_RESPONSABLE)
        if pendientes:
            return Aviso(
                _sin_repetidos([r for item in pendientes for r in _usuario(item.responsable_original_id)]),
                f"{_ETIQUETA_TIPO[movimiento.tipo].capitalize()} pendiente de tu aprobacion: {titulo}",
                _cuerpo(movimiento, texto + "\n\nComo responsable de alguno de estos activos, debes aprobar o rechazar."),
            )

        return Aviso(
            _sin_repetidos([*_ROLES_ADMINISTRADORES]),
            f"Nueva solicitud de {tipo}: {titulo}",
            _cuerpo(movimiento, texto),
        )

    if evento == EventoMovimiento.APROBADO_RESPONSABLE:
        espera_admin = movimiento.estado == EstadoMovimiento.APROBADO_RESPONSABLE
        destinatarios = _usuario(movimiento.creado_por.id_persona)
        if espera_admin:
            destinatarios = [*_ROLES_ADMINISTRADORES, *destinatarios]

        return Aviso(
            _sin_repetidos(destinatarios),
            f"Aprobado por los responsables: {titulo}",
            _cuerpo(
                movimiento,
                f"Los responsables aprobaron {tipo} de: {lista}."
                + (" Falta la confirmacion de administracion." if espera_admin else " Faltan otros responsables."),
            ),
        )

    if evento == EventoMovimiento.APROBADO:
        return Aviso(
            _sin_repetidos(_participantes(movimiento)),
            f"Movimiento aprobado: {titulo}",
            _cuerpo(movimiento, f"Se aprobo la solicitud de {tipo} de: {lista}."),
        )

    if evento == EventoMovimiento.RECHAZADO:
        rechazados = _con_estado(movimiento, EstadoItemMovimiento.RECHAZADO)
        motivos = "\n".join(
            f"- {_nombre_activo(activos.get(item.activo_id))}: {item.motivo_rechazo}"
            for item in rechazados
            if item.motivo_rechazo
        )

        return Aviso(
            _sin_repetidos(_participantes(movimiento)),
            f"Movimiento rechazado: {_titulo(rechazados or todos, activos)}",
            _cuerpo(
                movimiento,
                f"Se rechazo {tipo} de: {_lista(rechazados or todos, activos)}.",
                f"Motivo:\n{motivos}" if motivos else "",
            ),
        )

    if evento == EventoMovimiento.SALIDA_CONFIRMADA:
        salieron = _con_estado(movimiento, EstadoItemMovimiento.EN_CURSO, EstadoItemMovimiento.DEVOLUCION_SOLICITADA)
        extra = (
            "El comprobante esta disponible para descargar en el sistema." if movimiento.comprobante_archivo_id else ""
        )

        return Aviso(
            _sin_repetidos(_participantes(movimiento)),
            f"Salida confirmada: {_titulo(salieron, activos)}",
            _cuerpo(movimiento, f"Salieron y quedaron a cargo de quien los recibio: {_lista(salieron, activos)}.", extra),
        )

    if evento == EventoMovimiento.DEVOLUCION_SOLICITADA:
        pedidos = _con_estado(movimiento, EstadoItemMovimiento.DEVOLUCION_SOLICITADA)

        return Aviso(
            _sin_repetidos([*_ROLES_ADMINISTRADORES, *_participantes(movimiento)]),
            f"Devolucion solicitada: {_titulo(pedidos, activos)}",
            _cuerpo(
                movimiento,
                f"Se solicito devolver: {_lista(pedidos, activos)}. Administracion debe recibirlos.",
            ),
        )

    if evento == EventoMovimiento.DEVOLUCION_CONFIRMADA:
        devueltos = _con_estado(movimiento, EstadoItemMovimiento.DEVUELTO)
        novedades = "\n".join(
            f"- {_nombre_activo(activos.get(item.activo_id))}: {item.novedad_devolucion}"
            for item in devueltos
            if item.novedad_devolucion
        )

        return Aviso(
            _sin_repetidos(_participantes(movimiento)),
            f"Devolucion confirmada: {_titulo(devueltos, activos)}",
            _cuerpo(
                movimiento,
                f"Fueron recibidos de vuelta y volvieron a su responsable: {_lista(devueltos, activos)}.",
                f"Novedades al recibirlos:\n{novedades}" if novedades else "",
            ),
        )

    if evento == EventoMovimiento.BAJA_EJECUTADA:
        return Aviso(
            _sin_repetidos([*_ROLES_ADMINISTRADORES, *_participantes(movimiento)]),
            f"Baja de activo ejecutada: {titulo}",
            _cuerpo(movimiento, f"{lista} fue dado de baja de forma definitiva.", movimiento.descripcion),
        )

    # RECORDATORIO_DEVOLUCION
    fuera = _con_estado(movimiento, EstadoItemMovimiento.EN_CURSO, EstadoItemMovimiento.DEVOLUCION_SOLICITADA)
    fecha = movimiento.fecha_retorno_estimada.strftime("%d/%m/%Y") if movimiento.fecha_retorno_estimada else ""

    return Aviso(
        _sin_repetidos(_participantes(movimiento)),
        f"Recordatorio de devolucion: {_titulo(fuera, activos)}",
        _cuerpo(
            movimiento,
            f"Se acerca (o ya paso) la fecha de devolucion de: {_lista(fuera, activos)}.",
            f"Fecha de devolucion estimada: {fecha}" if fecha else "",
        ),
    )


async def avisar(
    notificador: NotificadorPort,
    evento: EventoMovimiento,
    movimiento: Movimiento,
    activos: Mapping[str, ActivoResumenMovimiento],
) -> None:
    aviso = construir_aviso(evento, movimiento, activos)

    await notificador.notificar(
        destinatarios=aviso.destinatarios, asunto=aviso.asunto, cuerpo=aviso.cuerpo
    )
