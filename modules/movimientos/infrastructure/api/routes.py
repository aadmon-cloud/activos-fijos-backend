from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response

from modules.auth.domain.entities.usuario import Usuario
from modules.movimientos.application.dto.exportar_movimientos_excel import (
    ExportarMovimientosExcelInput,
)
from modules.movimientos.application.dto.listar_movimientos import ListarMovimientosInput
from modules.movimientos.application.dto.registrar_entrada import RegistrarEntradaInput
from modules.movimientos.application.dto.registrar_entrada_multiple import (
    ItemEntradaMultipleInput,
    RegistrarEntradaMultipleInput,
)
from modules.movimientos.application.dto.registrar_salida import RegistrarSalidaInput
from modules.movimientos.application.dto.registrar_salida_multiple import (
    ItemSalidaMultipleInput,
    RegistrarSalidaMultipleInput,
)
from modules.movimientos.application.dto.registrar_salida_por_mercado import (
    ItemSalidaPorMercadoInput,
    RegistrarSalidaPorMercadoInput,
)
from modules.movimientos.application.services.confirmar_reserva import ConfirmarReservaService
from modules.movimientos.application.services.exportar_movimientos_excel import (
    ExportarMovimientosExcelService,
)
from modules.movimientos.application.services.generar_comprobante_pdf import (
    GenerarComprobantePdfService,
)
from modules.movimientos.application.services.listar_movimientos import ListarMovimientosService
from modules.movimientos.application.services.obtener_pdf_firmado import (
    ObtenerPdfFirmadoService,
)
from modules.movimientos.application.services.registrar_entrada import RegistrarEntradaService
from modules.movimientos.application.services.registrar_entrada_multiple import (
    RegistrarEntradaMultipleService,
)
from modules.movimientos.application.services.registrar_salida import RegistrarSalidaService
from modules.movimientos.application.services.registrar_salida_multiple import (
    RegistrarSalidaMultipleService,
)
from modules.movimientos.application.services.registrar_salida_por_mercado import (
    RegistrarSalidaPorMercadoService,
)
from modules.movimientos.application.services.subir_pdf_firmado import SubirPdfFirmadoService
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.movimientos.domain.errors import ArchivoNoEsPdfError
from modules.movimientos.infrastructure.api.dependencies import (
    get_confirmar_reserva_service,
    get_exportar_movimientos_excel_input,
    get_exportar_movimientos_excel_service,
    get_generar_comprobante_pdf_service,
    get_listar_movimientos_input,
    get_listar_movimientos_service,
    get_obtener_pdf_firmado_service,
    get_registrar_entrada_multiple_service,
    get_registrar_entrada_service,
    get_registrar_salida_multiple_service,
    get_registrar_salida_por_mercado_service,
    get_registrar_salida_service,
    get_subir_pdf_firmado_service,
)
from modules.movimientos.infrastructure.api.schemas import (
    ConfirmacionReservaResponse,
    ItemMovimientoResponse,
    MovimientoResponse,
    MovimientosPaginadosResponse,
    RegistrarEntradaMultipleRequest,
    RegistrarEntradaRequest,
    RegistrarSalidaMultipleRequest,
    RegistrarSalidaPorMercadoRequest,
    RegistrarSalidaRequest,
)
from modules.movimientos.infrastructure.excel.movimientos_excel_exporter import generar_excel
from shared.domain.entities.audit_persona import AuditPersona
from shared.infrastructure.api.dependencies.auth import require_authenticated, require_super_admin

router = APIRouter(prefix="/api/movimientos", tags=["movimientos"])


def _audit_persona(usuario: Usuario) -> AuditPersona:
    return AuditPersona(id_persona=usuario.id, nombre=usuario.username, fecha=datetime.now(UTC))


def _movimiento_response(movimiento: Movimiento) -> MovimientoResponse:
    return MovimientoResponse(
        id=movimiento.id,
        tipo=movimiento.tipo,
        modalidad=movimiento.modalidad,
        producto_codigo=movimiento.producto_codigo,
        producto_nombre=movimiento.producto_nombre,
        cantidad=movimiento.cantidad,
        motivo=movimiento.motivo,
        tipo_origen=movimiento.tipo_origen,
        origen_nombre=movimiento.origen_nombre,
        cliente_destino=movimiento.cliente_destino,
        ubicacion=movimiento.ubicacion,
        ubicacion_origen=movimiento.ubicacion_origen,
        ubicacion_destino=movimiento.ubicacion_destino,
        notas=movimiento.notas,
        remision=movimiento.remision,
        caso=movimiento.caso,
        referencia=movimiento.referencia,
        numero_cajas=movimiento.numero_cajas,
        kit_nombre=movimiento.kit_nombre,
        nombre_mercado=movimiento.nombre_mercado,
        productos=(
            [ItemMovimientoResponse(**item.model_dump()) for item in movimiento.productos]
            if movimiento.productos
            else None
        ),
        pdf_nombre=movimiento.pdf_nombre,
        usuario=movimiento.creado_por.nombre,
        fecha=movimiento.creado_por.fecha,
    )


@router.get(
    "",
    response_model=MovimientosPaginadosResponse,
    summary="Lista movimientos paginados, con filtros combinables",
)
async def listar_movimientos(
    entrada: Annotated[ListarMovimientosInput, Depends(get_listar_movimientos_input)],
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[ListarMovimientosService, Depends(get_listar_movimientos_service)],
) -> MovimientosPaginadosResponse:
    resultado = await service.ejecutar(entrada)
    return MovimientosPaginadosResponse(
        resultado=[_movimiento_response(m) for m in resultado.resultado],
        pagina_actual=resultado.pagina_actual,
        elementos_por_pagina=resultado.elementos_por_pagina,
        total_elementos=resultado.total_elementos,
        total_paginas=resultado.total_paginas,
    )


@router.get(
    "/exportar/excel",
    summary="Exporta movimientos a Excel (.xlsx), con filtros de fecha/tipo",
)
async def exportar_movimientos_excel(
    entrada: Annotated[
        ExportarMovimientosExcelInput, Depends(get_exportar_movimientos_excel_input)
    ],
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        ExportarMovimientosExcelService, Depends(get_exportar_movimientos_excel_service)
    ],
) -> Response:
    movimientos = await service.ejecutar(entrada)
    contenido = generar_excel(movimientos)
    nombre_archivo = f"movimientos_inventario_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={nombre_archivo}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post(
    "/entradas",
    response_model=MovimientoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra una entrada individual de inventario (requiere super_admin)",
    responses={404: {"description": "No existe un producto con ese código"}},
)
async def registrar_entrada(
    payload: RegistrarEntradaRequest,
    usuario_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[RegistrarEntradaService, Depends(get_registrar_entrada_service)],
) -> MovimientoResponse:
    movimiento = await service.ejecutar(
        RegistrarEntradaInput(
            producto_codigo=payload.producto_codigo,
            cantidad=payload.cantidad,
            motivo=payload.motivo,
            tipo_origen=payload.tipo_origen,
            origen_nombre=payload.origen_nombre,
            ubicacion=payload.ubicacion,
            notas=payload.notas,
        ),
        _audit_persona(usuario_actual),
    )
    return _movimiento_response(movimiento)


@router.post(
    "/entradas/multiple",
    response_model=MovimientoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra una sola entrada con varios productos (requiere super_admin)",
    responses={404: {"description": "Algún producto referenciado no existe"}},
)
async def registrar_entrada_multiple(
    payload: RegistrarEntradaMultipleRequest,
    usuario_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[
        RegistrarEntradaMultipleService, Depends(get_registrar_entrada_multiple_service)
    ],
) -> MovimientoResponse:
    movimiento = await service.ejecutar(
        RegistrarEntradaMultipleInput(
            productos=[
                ItemEntradaMultipleInput(
                    producto_codigo=item.producto_codigo,
                    cantidad=item.cantidad,
                    ubicacion=item.ubicacion,
                )
                for item in payload.productos
            ],
            tipo_origen=payload.tipo_origen,
            origen_nombre=payload.origen_nombre,
            ubicacion=payload.ubicacion,
            notas=payload.notas,
        ),
        _audit_persona(usuario_actual),
    )
    return _movimiento_response(movimiento)


@router.post(
    "/reservas/{session_id}/confirmar",
    response_model=ConfirmacionReservaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirma una reserva (normal, kit o múltiple) como salida(s) real(es) (requiere super_admin)",
    responses={
        404: {"description": "No existe una reserva para esa sesión, o algún producto/ubicación referenciado no existe"},
        400: {"description": "La reserva tiene una modalidad no soportada"},
        422: {"description": "Stock físico insuficiente en alguna ubicación"},
    },
)
async def confirmar_reserva(
    session_id: str,
    usuario_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[ConfirmarReservaService, Depends(get_confirmar_reserva_service)],
) -> ConfirmacionReservaResponse:
    movimientos = await service.ejecutar(session_id, _audit_persona(usuario_actual))
    return ConfirmacionReservaResponse(
        movimientos=[_movimiento_response(m) for m in movimientos],
        remision=movimientos[0].remision,
    )


@router.post(
    "/salidas",
    response_model=MovimientoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra una salida individual de inventario (requiere super_admin)",
    responses={
        404: {"description": "No existe el producto o la ubicación indicada"},
        422: {"description": "Stock físico insuficiente en esa ubicación"},
    },
)
async def registrar_salida(
    payload: RegistrarSalidaRequest,
    usuario_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[RegistrarSalidaService, Depends(get_registrar_salida_service)],
) -> MovimientoResponse:
    movimiento = await service.ejecutar(
        RegistrarSalidaInput(
            producto_codigo=payload.producto_codigo,
            cantidad=payload.cantidad,
            ubicacion=payload.ubicacion,
            motivo=payload.motivo,
            cliente_destino=payload.cliente_destino,
            notas=payload.notas,
        ),
        _audit_persona(usuario_actual),
    )
    return _movimiento_response(movimiento)


@router.post(
    "/salidas/multiple",
    response_model=MovimientoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra una sola salida con varios productos, cada uno con su propia ubicación (requiere super_admin)",
    responses={
        404: {"description": "Algún producto o ubicación referenciada no existe"},
        422: {"description": "Stock físico insuficiente en alguna ubicación"},
    },
)
async def registrar_salida_multiple(
    payload: RegistrarSalidaMultipleRequest,
    usuario_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[
        RegistrarSalidaMultipleService, Depends(get_registrar_salida_multiple_service)
    ],
) -> MovimientoResponse:
    movimiento = await service.ejecutar(
        RegistrarSalidaMultipleInput(
            productos=[
                ItemSalidaMultipleInput(
                    producto_codigo=item.producto_codigo,
                    cantidad=item.cantidad,
                    ubicacion=item.ubicacion,
                )
                for item in payload.productos
            ],
            motivo=payload.motivo,
            cliente_destino=payload.cliente_destino,
            notas=payload.notas,
        ),
        _audit_persona(usuario_actual),
    )
    return _movimiento_response(movimiento)


@router.post(
    "/salida-por-mercado",
    response_model=MovimientoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra la salida de un mercado predefinido, indicando la ubicación de origen de cada producto (requiere super_admin)",
    responses={
        400: {"description": "Falta indicar la ubicación de origen de algún producto del mercado"},
        404: {"description": "No existe el mercado predefinido indicado, o algún producto no existe"},
        422: {"description": "Stock físico insuficiente en la ubicación indicada"},
    },
)
async def registrar_salida_por_mercado(
    payload: RegistrarSalidaPorMercadoRequest,
    usuario_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[
        RegistrarSalidaPorMercadoService, Depends(get_registrar_salida_por_mercado_service)
    ],
) -> MovimientoResponse:
    movimiento = await service.ejecutar(
        RegistrarSalidaPorMercadoInput(
            mercado_nombre=payload.mercado_nombre,
            productos=[
                ItemSalidaPorMercadoInput(
                    producto_codigo=item.producto_codigo,
                    ubicacion=item.ubicacion,
                )
                for item in payload.productos
            ],
            cantidad=payload.cantidad,
            cliente_destino=payload.cliente_destino,
            notas=payload.notas,
            referencia=payload.referencia,
        ),
        _audit_persona(usuario_actual),
    )
    return _movimiento_response(movimiento)


@router.get(
    "/{movimiento_id}/comprobante",
    summary="Genera el comprobante PDF de una salida (individual o kit) ya registrada",
    responses={404: {"description": "No existe una salida con ese id"}},
)
async def generar_comprobante(
    movimiento_id: str,
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        GenerarComprobantePdfService, Depends(get_generar_comprobante_pdf_service)
    ],
) -> Response:
    contenido = await service.ejecutar(movimiento_id)
    nombre_archivo = f"comprobante_{movimiento_id}.pdf"
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )


@router.post(
    "/{movimiento_id}/pdf-firmado",
    response_model=MovimientoResponse,
    summary="Sube el PDF firmado manualmente para una salida ya registrada",
    responses={
        404: {"description": "No existe una salida con ese id"},
        400: {"description": "El archivo subido no es un PDF"},
    },
)
async def subir_pdf_firmado(
    movimiento_id: str,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[SubirPdfFirmadoService, Depends(get_subir_pdf_firmado_service)],
    archivo: UploadFile = File(...),
) -> MovimientoResponse:
    if not archivo.filename:
        raise ArchivoNoEsPdfError("(sin nombre)")
    contenido = await archivo.read()
    movimiento = await service.ejecutar(
        movimiento_id, archivo.filename, contenido, _audit_persona(usuario_actual)
    )
    return _movimiento_response(movimiento)


@router.get(
    "/{movimiento_id}/pdf-firmado",
    summary="Descarga el PDF firmado subido para una salida",
    responses={404: {"description": "No existe la salida, o todavía no tiene un PDF firmado"}},
)
async def obtener_pdf_firmado(
    movimiento_id: str,
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[ObtenerPdfFirmadoService, Depends(get_obtener_pdf_firmado_service)],
) -> Response:
    contenido, nombre_archivo = await service.ejecutar(movimiento_id)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )
