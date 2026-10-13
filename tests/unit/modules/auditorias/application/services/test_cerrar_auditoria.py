from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.auditorias.application.dto.cerrar_auditoria_dto import CerrarAuditoriaDTO
from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditado
from modules.auditorias.application.services.cerrar_auditoria import CerrarAuditoriaService
from modules.auditorias.domain.entities import (
    Auditoria,
    EstadoAuditoria,
    ItemAuditoria,
    ResultadoVerificacion,
)
from modules.auditorias.domain.errors import AuditoriaNoEncontradaError, AuditoriaNoModificableError
from shared.application.file_storage.ports import ArchivoAlmacenado
from shared.domain.entities.audit import AuditPersona

_DTO = CerrarAuditoriaDTO(id_auditoria="aud-1", actor_id="admin-1", actor_nombre="Admin")


def _item(**overrides) -> ItemAuditoria:
    valores = dict(
        activo_id="a1",
        nombre="Laptop",
        numero_inventario="INV-1",
        tipo="activo_fijo",
        descripcion=None,
        serie=None,
        estado_ciclo_vida_al_inicio="disponible",
        resultado=None,
        observacion=None,
        verificado_en=None,
    )
    valores.update(overrides)
    return ItemAuditoria(**valores)


def _auditoria(**overrides) -> Auditoria:
    valores = dict(
        id="aud-1",
        usuario_auditado_id="u1",
        estado=EstadoAuditoria.EN_PROGRESO,
        items=[_item(resultado=ResultadoVerificacion.ENCONTRADO), _item(activo_id="a2")],
        fecha_cierre=None,
        pdf_archivo_id=None,
        detalle_error_notificacion=None,
        creado_por=AuditPersona(id_persona="admin-1", nombre="Admin", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Auditoria(**valores)


def _usuario() -> UsuarioAuditado:
    return UsuarioAuditado(
        id="u1", nombre_completo="Camilo Perez", identificacion="123", email="camilo@x.com", activo=True
    )


def _servicio(
    repo=None, usuario_auditado=None, historial_nota=None, generador_reporte=None,
    almacen_archivos=None, notificador=None,
):
    repo = repo or AsyncMock()
    usuario_auditado = usuario_auditado or AsyncMock()
    historial_nota = historial_nota or AsyncMock()
    generador_reporte = generador_reporte or AsyncMock()
    almacen_archivos = almacen_archivos or AsyncMock()
    notificador = notificador or AsyncMock()
    return CerrarAuditoriaService(
        repo, usuario_auditado, historial_nota, generador_reporte, almacen_archivos, notificador
    ), repo, usuario_auditado, historial_nota, generador_reporte, almacen_archivos, notificador


async def test_cerrar_falla_si_la_auditoria_no_existe():
    service, repo, *_ = _servicio()
    repo.obtener_por_id.return_value = None

    with pytest.raises(AuditoriaNoEncontradaError):
        await service.ejecutar(_DTO)


async def test_cerrar_falla_si_la_auditoria_ya_fue_cerrada():
    service, repo, *_ = _servicio()
    repo.obtener_por_id.return_value = _auditoria(estado=EstadoAuditoria.FINALIZADA)

    with pytest.raises(AuditoriaNoModificableError):
        await service.ejecutar(_DTO)


async def test_cerrar_marca_los_pendientes_como_no_encontrados():
    service, repo, usuario_auditado, *_ = _servicio()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    usuario_auditado.obtener.return_value = _usuario()

    resultado = await service.ejecutar(_DTO)

    pendiente_original = next(i for i in resultado.items if i.activo_id == "a2")
    assert pendiente_original.resultado == ResultadoVerificacion.NO_ENCONTRADO
    assert resultado.pendientes == 0


async def test_cerrar_guarda_primero_el_estado_finalizada_antes_de_cualquier_efecto_secundario():
    service, repo, usuario_auditado, historial_nota, generador_reporte, almacen_archivos, notificador = (
        _servicio()
    )
    repo.obtener_por_id.return_value = _auditoria()
    estados_guardados = []

    async def _guardar(auditoria):
        estados_guardados.append(auditoria.estado)
        return auditoria

    repo.guardar.side_effect = _guardar
    usuario_auditado.obtener.return_value = _usuario()
    generador_reporte.generar_pdf.side_effect = RuntimeError("fallo generando el pdf")

    await service.ejecutar(_DTO)

    assert estados_guardados[0] == EstadoAuditoria.FINALIZADA


async def test_cerrar_registra_una_nota_de_historial_por_cada_item():
    service, repo, usuario_auditado, historial_nota, *_ = _servicio()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    usuario_auditado.obtener.return_value = _usuario()

    await service.ejecutar(_DTO)

    assert historial_nota.registrar_nota.call_count == 2
    ids_notificados = {c.args[0] for c in historial_nota.registrar_nota.call_args_list}
    assert ids_notificados == {"a1", "a2"}


async def test_cerrar_no_aborta_si_falla_una_nota_de_historial():
    service, repo, usuario_auditado, historial_nota, *_ = _servicio()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    usuario_auditado.obtener.return_value = _usuario()
    historial_nota.registrar_nota.side_effect = RuntimeError("mongo caido")

    resultado = await service.ejecutar(_DTO)

    assert resultado.estado in (EstadoAuditoria.NOTIFICADA, EstadoAuditoria.ERROR_NOTIFICACION)


async def test_cerrar_genera_y_guarda_el_pdf():
    service, repo, usuario_auditado, _hn, generador_reporte, almacen_archivos, notificador = _servicio()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    usuario_auditado.obtener.return_value = _usuario()
    generador_reporte.generar_pdf.return_value = b"%PDF-contenido"
    almacen_archivos.guardar.return_value = "archivo-pdf-1"
    almacen_archivos.obtener.return_value = ArchivoAlmacenado(
        nombre="auditoria.pdf", tipo_mime="application/pdf", contenido=b"%PDF-contenido"
    )

    resultado = await service.ejecutar(_DTO)

    almacen_archivos.guardar.assert_called_once()
    assert resultado.pdf_archivo_id == "archivo-pdf-1"


async def test_cerrar_no_aborta_si_falla_la_generacion_del_pdf():
    service, repo, usuario_auditado, _hn, generador_reporte, almacen_archivos, notificador = _servicio()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    usuario_auditado.obtener.return_value = _usuario()
    generador_reporte.generar_pdf.side_effect = RuntimeError("fallo reportlab")

    resultado = await service.ejecutar(_DTO)

    assert resultado.estado == EstadoAuditoria.ERROR_NOTIFICACION
    assert resultado.pdf_archivo_id is None


async def test_cerrar_notifica_y_queda_en_estado_notificada_si_todo_sale_bien():
    service, repo, usuario_auditado, _hn, generador_reporte, almacen_archivos, notificador = _servicio()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    usuario_auditado.obtener.return_value = _usuario()
    generador_reporte.generar_pdf.return_value = b"%PDF-contenido"
    almacen_archivos.guardar.return_value = "archivo-pdf-1"
    almacen_archivos.obtener.return_value = ArchivoAlmacenado(
        nombre="auditoria.pdf", tipo_mime="application/pdf", contenido=b"%PDF-contenido"
    )

    resultado = await service.ejecutar(_DTO)

    assert resultado.estado == EstadoAuditoria.NOTIFICADA
    notificador.enviar.assert_called_once()
    destinatarios = notificador.enviar.call_args.kwargs["destinatarios"]
    assert "camilo@x.com" in destinatarios


async def test_cerrar_queda_en_error_notificacion_si_falla_el_envio_de_correo():
    service, repo, usuario_auditado, _hn, generador_reporte, almacen_archivos, notificador = _servicio()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    usuario_auditado.obtener.return_value = _usuario()
    generador_reporte.generar_pdf.return_value = b"%PDF-contenido"
    almacen_archivos.guardar.return_value = "archivo-pdf-1"
    almacen_archivos.obtener.return_value = ArchivoAlmacenado(
        nombre="auditoria.pdf", tipo_mime="application/pdf", contenido=b"%PDF-contenido"
    )
    notificador.enviar.side_effect = RuntimeError("smtp caido")

    resultado = await service.ejecutar(_DTO)

    assert resultado.estado == EstadoAuditoria.ERROR_NOTIFICACION
    assert resultado.detalle_error_notificacion == "smtp caido"
    # El cierre y el PDF ya guardados no se revierten por el fallo de correo.
    assert resultado.pdf_archivo_id == "archivo-pdf-1"
    assert all(i.resultado is not None for i in resultado.items)


async def test_el_detalle_del_error_de_correo_se_acota_para_no_guardar_mensajes_enormes():
    service, repo, usuario_auditado, _hn, generador_reporte, almacen_archivos, notificador = _servicio()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    usuario_auditado.obtener.return_value = _usuario()
    generador_reporte.generar_pdf.return_value = b"%PDF-contenido"
    almacen_archivos.guardar.return_value = "archivo-pdf-1"
    almacen_archivos.obtener.return_value = ArchivoAlmacenado(
        nombre="auditoria.pdf", tipo_mime="application/pdf", contenido=b"%PDF-contenido"
    )
    notificador.enviar.side_effect = RuntimeError("x" * 5000)

    resultado = await service.ejecutar(_DTO)

    assert len(resultado.detalle_error_notificacion) == 300
