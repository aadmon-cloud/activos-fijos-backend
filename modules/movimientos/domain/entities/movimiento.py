from __future__ import annotations

from typing import Literal

from shared.domain.entities.audit_persona import AuditPersona
from shared.domain.entities.base import BaseDomainEntity

from modules.movimientos.domain.errors import (
    MovimientoSinProductosError,
    MovimientoUbicacionRequeridaError,
)

TipoMovimiento = Literal["entrada", "salida", "creacion_ubicacion", "transferencia_ubicacion"]
ModalidadMovimiento = Literal["individual", "kit", "multiple", "entrada_multiple", "mercado"]


class ItemMovimiento(BaseDomainEntity):
    producto_codigo: str
    producto_nombre: str
    cantidad: int
    ubicacion: str | None = None


class Movimiento(BaseDomainEntity):
    id: str | None = None
    tipo: TipoMovimiento
    modalidad: ModalidadMovimiento
    producto_codigo: str | None = None
    producto_nombre: str | None = None
    cantidad: int
    motivo: str | None = None
    tipo_origen: str | None = None
    origen_nombre: str | None = None
    cliente_destino: str | None = None
    ubicacion: str | None = None
    ubicacion_origen: str | None = None
    ubicacion_destino: str | None = None
    notas: str | None = None
    remision: str | None = None
    caso: str | None = None
    referencia: str | None = None
    numero_cajas: int | None = None
    kit_nombre: str | None = None
    nombre_mercado: str | None = None
    productos: list[ItemMovimiento] | None = None
    pdf_firmado: str | None = None
    pdf_nombre: str | None = None
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None = None

    @classmethod
    def registrar_entrada(
        cls,
        producto_codigo: str,
        producto_nombre: str,
        cantidad: int,
        motivo: str | None,
        tipo_origen: str | None,
        origen_nombre: str | None,
        ubicacion: str | None,
        notas: str | None,
        creado_por: AuditPersona,
    ) -> "Movimiento":
        return cls(
            id=None,
            tipo="entrada",
            modalidad="individual",
            producto_codigo=producto_codigo,
            producto_nombre=producto_nombre,
            cantidad=cantidad,
            motivo=motivo,
            tipo_origen=tipo_origen,
            origen_nombre=origen_nombre,
            ubicacion=ubicacion or "ALMACEN_GENERAL",
            notas=notas,
            creado_por=creado_por,
        )

    @classmethod
    def registrar_salida(
        cls,
        producto_codigo: str,
        producto_nombre: str,
        cantidad: int,
        motivo: str | None,
        cliente_destino: str | None,
        ubicacion: str,
        notas: str | None,
        remision: str,
        creado_por: AuditPersona,
    ) -> "Movimiento":
        if not ubicacion or not ubicacion.strip():
            raise MovimientoUbicacionRequeridaError()
        return cls(
            id=None,
            tipo="salida",
            modalidad="individual",
            producto_codigo=producto_codigo,
            producto_nombre=producto_nombre,
            cantidad=cantidad,
            motivo=motivo,
            cliente_destino=cliente_destino,
            ubicacion=ubicacion,
            notas=notas,
            remision=remision,
            creado_por=creado_por,
        )

    @classmethod
    def registrar_kit(
        cls,
        kit_nombre: str,
        productos: list[ItemMovimiento],
        cliente_destino: str | None,
        notas: str | None,
        caso: str | None,
        remision: str,
        creado_por: AuditPersona,
    ) -> "Movimiento":
        """Una sola salida representando la confirmación de un kit completo
        (`cantidad=1`, siempre). `numero_cajas` queda en 0 — el legacy lo
        trackeaba por item de reserva, pero ese campo no sobrevivió al
        `ItemReserva` del módulo `reservas` (ni aparece poblado en los kits
        reales existentes) — ver MIGRATION_PLAN.md, incremento 3."""
        return cls(
            id=None,
            tipo="salida",
            modalidad="kit",
            cantidad=1,
            motivo="Salida de Kit",
            cliente_destino=cliente_destino,
            notas=notas,
            remision=remision,
            caso=caso,
            numero_cajas=0,
            kit_nombre=kit_nombre,
            productos=productos,
            creado_por=creado_por,
        )

    @classmethod
    def registrar_entrada_multiple(
        cls,
        productos: list[ItemMovimiento],
        tipo_origen: str,
        origen_nombre: str,
        notas: str | None,
        creado_por: AuditPersona,
    ) -> "Movimiento":
        """Una sola entrada con varios productos, cada uno con su propia
        ubicación ya resuelta (ver Fase 2, incremento 4 — corrige un bug del
        legacy que registraba "ALMACEN_GENERAL" en el item aunque el stock
        real se hubiera aplicado a otra ubicación)."""
        if not productos:
            raise MovimientoSinProductosError()
        return cls(
            id=None,
            tipo="entrada",
            modalidad="entrada_multiple",
            cantidad=sum(item.cantidad for item in productos),
            motivo=tipo_origen.capitalize(),
            tipo_origen=tipo_origen,
            origen_nombre=origen_nombre,
            notas=notas,
            productos=productos,
            creado_por=creado_por,
        )

    @classmethod
    def registrar_multiple(
        cls,
        productos: list[ItemMovimiento],
        motivo: str | None,
        cliente_destino: str | None,
        notas: str | None,
        caso: str | None,
        remision: str,
        creado_por: AuditPersona,
    ) -> "Movimiento":
        """Una sola salida con varios productos embebidos — mismo patrón que
        `registrar_kit`, sin `kit_nombre`. Usada tanto por la confirmación de
        reserva modalidad múltiple (con `motivo` fijo) como por el registro
        directo de salida múltiple (con `motivo` provisto por quien la
        registra) — cada llamador decide su propio `motivo`."""
        if not productos:
            raise MovimientoSinProductosError()
        return cls(
            id=None,
            tipo="salida",
            modalidad="multiple",
            cantidad=1,
            motivo=motivo,
            cliente_destino=cliente_destino,
            notas=notas,
            remision=remision,
            caso=caso,
            numero_cajas=0,
            productos=productos,
            creado_por=creado_por,
        )

    @classmethod
    def registrar_mercado(
        cls,
        nombre_mercado: str,
        productos: list[ItemMovimiento],
        cantidad: int,
        cliente_destino: str | None,
        notas: str | None,
        referencia: str | None,
        remision: str,
        creado_por: AuditPersona,
    ) -> "Movimiento":
        """Una sola salida por mercado predefinido, con todos los productos
        del kit embebidos (multiplicados por `cantidad` mercados
        despachados). A diferencia de `registrar_kit`, `cantidad` no es fija
        en 1 — refleja cuántos mercados se despacharon en esta operación."""
        if not productos:
            raise MovimientoSinProductosError()
        return cls(
            id=None,
            tipo="salida",
            modalidad="mercado",
            cantidad=cantidad,
            motivo=f"Salida de {nombre_mercado}",
            cliente_destino=cliente_destino,
            notas=notas,
            referencia=referencia,
            remision=remision,
            nombre_mercado=nombre_mercado,
            productos=productos,
            creado_por=creado_por,
        )

    @classmethod
    def registrar_creacion_ubicacion(
        cls,
        producto_codigo: str,
        producto_nombre: str,
        ubicacion: str,
        cantidad: int,
        creado_por: AuditPersona,
    ) -> "Movimiento":
        """Bitácora de que `ubicaciones` creó esta ubicación con este stock
        inicial — no altera stock por sí mismo (`CrearUbicacionService` ya lo
        hizo); es solo el registro histórico en `movimientos`."""
        return cls(
            id=None,
            tipo="creacion_ubicacion",
            modalidad="individual",
            producto_codigo=producto_codigo,
            producto_nombre=producto_nombre,
            cantidad=cantidad,
            ubicacion=ubicacion,
            creado_por=creado_por,
        )

    @classmethod
    def registrar_transferencia_ubicacion(
        cls,
        producto_codigo: str,
        producto_nombre: str,
        ubicacion_origen: str,
        ubicacion_destino: str,
        cantidad: int,
        creado_por: AuditPersona,
    ) -> "Movimiento":
        """Bitácora de que `ubicaciones` movió stock entre dos ubicaciones
        del mismo producto — idem, solo registro histórico."""
        return cls(
            id=None,
            tipo="transferencia_ubicacion",
            modalidad="individual",
            producto_codigo=producto_codigo,
            producto_nombre=producto_nombre,
            cantidad=cantidad,
            ubicacion_origen=ubicacion_origen,
            ubicacion_destino=ubicacion_destino,
            creado_por=creado_por,
        )

    def adjuntar_pdf_firmado(
        self, pdf_ruta: str, pdf_nombre: str, actualizado_por: AuditPersona
    ) -> "Movimiento":
        return self.model_copy(
            update={
                "pdf_firmado": pdf_ruta,
                "pdf_nombre": pdf_nombre,
                "actualizado_por": actualizado_por,
            }
        )
