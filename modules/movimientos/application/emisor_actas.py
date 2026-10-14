"""Emision de las actas de salida y de ingreso: arma el PDF con los sellos y lo guarda."""

from dataclasses import replace
from uuid import uuid4

from modules.movimientos.application.ports.generador_acta_port import (
    DatosActaPdf,
    GeneradorActaPort,
    LineaActaPdf,
)
from modules.movimientos.application.ports.resolutor_nombres_port import (
    ReferenciasMovimiento,
    ResolutorNombresMovimientoPort,
)
from modules.movimientos.domain.entities import (
    ActaMovimiento,
    LineaActa,
    Movimiento,
    SelloActa,
    TipoActa,
)
from shared.application.file_storage.ports import AlmacenArchivosPort

_TIPO_MIME_PDF = "application/pdf"
_SIN_DATO = "-"


class EmisorActas:
    """Crea el acta al cerrar un chequeo y la vuelve a imprimir cuando el responsable la acepta (con los dos sellos)."""

    def __init__(
        self,
        generador: GeneradorActaPort,
        almacen_archivos: AlmacenArchivosPort,
        resolutor_nombres: ResolutorNombresMovimientoPort,
    ):
        self._generador = generador
        self._almacen_archivos = almacen_archivos
        self._resolutor_nombres = resolutor_nombres

    async def emitir(
        self,
        movimiento: Movimiento,
        tipo: TipoActa,
        lineas: list[LineaActa],
        cerrada_por: SelloActa,
    ) -> ActaMovimiento:
        """Acta nueva con el sello de administracion; el del responsable queda pendiente."""
        acta = ActaMovimiento(
            id=uuid4().hex,
            tipo=tipo,
            numero=1 + sum(1 for existente in movimiento.actas if existente.tipo == tipo),
            lineas=lineas,
            cerrada_por=cerrada_por,
        )

        return await self._con_pdf(movimiento, acta)

    async def aceptar(self, movimiento: Movimiento, acta: ActaMovimiento, aceptada_por: SelloActa) -> ActaMovimiento:
        """El mismo acta con el sello del responsable; el PDF anterior se reemplaza por el completo."""
        aceptada = replace(acta, aceptada_por=aceptada_por)
        completa = await self._con_pdf(movimiento, aceptada)

        if acta.archivo_id:
            await self._almacen_archivos.eliminar(acta.archivo_id)

        return completa

    async def _con_pdf(self, movimiento: Movimiento, acta: ActaMovimiento) -> ActaMovimiento:
        responsable_id = movimiento.usuario_destino_id
        nombres = await self._resolutor_nombres.resolver(
            ReferenciasMovimiento(
                activo_ids={linea.activo_id for linea in acta.lineas},
                usuario_ids={responsable_id} if responsable_id else set(),
            )
        )

        contenido = await self._generador.generar_pdf(
            DatosActaPdf(
                movimiento=movimiento,
                acta=acta,
                lineas=[
                    LineaActaPdf(
                        descripcion=_descripcion(nombres.activos.get(linea.activo_id), linea.activo_id),
                        resultado=linea.resultado,
                        observacion=linea.observacion,
                    )
                    for linea in acta.lineas
                ],
                responsable_nombre=nombres.usuarios.get(responsable_id, _SIN_DATO) if responsable_id else _SIN_DATO,
                responsable_correo=nombres.correos.get(responsable_id, _SIN_DATO) if responsable_id else _SIN_DATO,
            )
        )
        archivo_id = await self._almacen_archivos.guardar(
            movimiento.id, f"acta-{acta.tipo.value}-{acta.numero}.pdf", contenido, _TIPO_MIME_PDF
        )

        return replace(acta, archivo_id=archivo_id)


def _descripcion(activo, activo_id: str) -> str:
    if activo is None or not activo.nombre:
        return activo_id

    return f"{activo.numero_inventario} - {activo.nombre}" if activo.numero_inventario else activo.nombre
