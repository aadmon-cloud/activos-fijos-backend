from collections.abc import Mapping
from enum import Enum

from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    ItemMovimiento,
    Movimiento,
    TipoMovimiento,
)

_ROL_ADMINISTRADOR_GENERAL = "administrador_general"


class AccionMovimiento(str, Enum):
    """Acciones que un usuario puede ejecutar sobre un movimiento (o sobre alguno de sus items)."""

    APROBAR = "aprobar"
    RECHAZAR = "rechazar"
    CONFIRMAR_SALIDA = "confirmar_salida"
    SOLICITAR_DEVOLUCION = "solicitar_devolucion"
    CONFIRMAR_DEVOLUCION = "confirmar_devolucion"
    EJECUTAR_BAJA = "ejecutar_baja"


def es_administrador(actor_rol: str) -> bool:
    return actor_rol == _ROL_ADMINISTRADOR_GENERAL


def tiene_el_activo(movimiento: Movimiento, actor_id: str, responsable_actual_id: str | None) -> bool:
    """Quien tiene el activo ahora: el destinatario, o quien figura como su responsable (tras la salida son el mismo)."""
    return actor_id == movimiento.usuario_destino_id or (
        responsable_actual_id is not None and actor_id == responsable_actual_id
    )


def acciones_de_item(
    movimiento: Movimiento,
    item: ItemMovimiento,
    actor_id: str,
    actor_rol: str,
    responsable_actual_id: str | None,
) -> list[AccionMovimiento]:
    """Acciones de este usuario sobre UN activo del movimiento. Es la fuente de verdad que consume el frontend.

    - Un activo que espera al responsable lo decide ese responsable (aprobar o rechazar).
    - Uno que espera a administracion lo decide el administrador: confirma la salida (en prestamos y salidas) o
      aprueba la baja; en ambos casos tambien puede rechazarlo.
    - Uno que esta fuera lo puede pedir de vuelta quien lo tiene; administracion lo recibe.
    """
    es_admin = es_administrador(actor_rol)
    acciones: list[AccionMovimiento] = []

    if item.estado == EstadoItemMovimiento.PENDIENTE_RESPONSABLE:
        if responsable_actual_id is not None and actor_id == responsable_actual_id:
            acciones += [AccionMovimiento.APROBAR, AccionMovimiento.RECHAZAR]

    elif item.estado == EstadoItemMovimiento.PENDIENTE_ADMIN:
        if es_admin:
            if movimiento.tipo == TipoMovimiento.BAJA:
                if movimiento.estado == EstadoMovimiento.SOLICITADO:
                    acciones += [AccionMovimiento.APROBAR, AccionMovimiento.RECHAZAR]
                elif movimiento.estado == EstadoMovimiento.APROBADO:
                    acciones.append(AccionMovimiento.EJECUTAR_BAJA)
            else:
                acciones += [AccionMovimiento.CONFIRMAR_SALIDA, AccionMovimiento.RECHAZAR]

    elif item.estado == EstadoItemMovimiento.EN_CURSO:
        if tiene_el_activo(movimiento, actor_id, responsable_actual_id):
            acciones.append(AccionMovimiento.SOLICITAR_DEVOLUCION)
        if es_admin:
            acciones.append(AccionMovimiento.CONFIRMAR_DEVOLUCION)

    elif item.estado == EstadoItemMovimiento.DEVOLUCION_SOLICITADA:
        if es_admin:
            acciones.append(AccionMovimiento.CONFIRMAR_DEVOLUCION)

    return acciones


def acciones_permitidas(
    movimiento: Movimiento,
    actor_id: str,
    actor_rol: str,
    responsables_actuales: Mapping[str, str | None],
) -> list[AccionMovimiento]:
    """Acciones disponibles para este usuario sobre el movimiento: la union de las de cada activo."""
    acciones: list[AccionMovimiento] = []

    for item in movimiento.items:
        for accion in acciones_de_item(
            movimiento, item, actor_id, actor_rol, responsables_actuales.get(item.activo_id)
        ):
            if accion not in acciones:
                acciones.append(accion)

    return acciones


def puede_ver(
    movimiento: Movimiento,
    actor_id: str,
    actor_rol: str,
    responsables_actuales: Mapping[str, str | None],
) -> bool:
    """Ve el movimiento el administrador, quien lo creo, el destinatario y quien tiene a cargo alguno de sus
    activos (el responsable actual o el original)."""
    if es_administrador(actor_rol):
        return True

    relacionados = {movimiento.creado_por.id_persona, movimiento.usuario_destino_id}
    for item in movimiento.items:
        relacionados.add(item.responsable_original_id)
        relacionados.add(responsables_actuales.get(item.activo_id))

    return actor_id in relacionados
