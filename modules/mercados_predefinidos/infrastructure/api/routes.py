from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from modules.auth.domain.entities.usuario import Usuario
from modules.mercados_predefinidos.application.dto.actualizar_mercado_predefinido import (
    ActualizarMercadoPredefinidoInput,
)
from modules.mercados_predefinidos.application.dto.crear_mercado_predefinido import (
    CrearMercadoPredefinidoInput,
)
from modules.mercados_predefinidos.application.dto.producto_kit import ProductoKitInput
from modules.mercados_predefinidos.application.services.actualizar_mercado_predefinido import (
    ActualizarMercadoPredefinidoService,
)
from modules.mercados_predefinidos.application.services.crear_mercado_predefinido import (
    CrearMercadoPredefinidoService,
)
from modules.mercados_predefinidos.application.services.listar_mercados_predefinidos import (
    ListarMercadosPredefinidosService,
)
from modules.mercados_predefinidos.application.services.obtener_mercado_predefinido import (
    ObtenerMercadoPredefinidoService,
)
from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
)
from modules.mercados_predefinidos.infrastructure.api.dependencies import (
    get_actualizar_mercado_predefinido_service,
    get_crear_mercado_predefinido_service,
    get_listar_mercados_predefinidos_service,
    get_obtener_mercado_predefinido_service,
)
from modules.mercados_predefinidos.infrastructure.api.schemas import (
    ActualizarMercadoPredefinidoRequest,
    CrearMercadoPredefinidoRequest,
    MercadoPredefinidoResponse,
)
from shared.domain.entities.audit_persona import AuditPersona
from shared.infrastructure.api.dependencies.auth import require_authenticated

router = APIRouter(prefix="/api/mercados-predefinidos", tags=["mercados-predefinidos"])


def _audit_persona(usuario: Usuario) -> AuditPersona:
    return AuditPersona(id_persona=usuario.id, nombre=usuario.username, fecha=datetime.now(UTC))


def _mercado_response(mercado: MercadoPredefinido) -> MercadoPredefinidoResponse:
    return MercadoPredefinidoResponse.model_validate(mercado.model_dump())


@router.get(
    "",
    response_model=list[MercadoPredefinidoResponse],
    summary="Lista los mercados predefinidos",
)
async def listar_mercados_predefinidos(
    service: Annotated[
        ListarMercadosPredefinidosService, Depends(get_listar_mercados_predefinidos_service)
    ],
    solo_activos: bool = Query(default=True),
) -> list[MercadoPredefinidoResponse]:
    mercados = await service.ejecutar(solo_activos)
    return [_mercado_response(m) for m in mercados]


@router.get(
    "/{nombre}",
    response_model=MercadoPredefinidoResponse,
    summary="Obtiene un mercado predefinido por su nombre",
    responses={404: {"description": "No existe un mercado predefinido con ese nombre"}},
)
async def obtener_mercado_predefinido(
    nombre: str,
    service: Annotated[
        ObtenerMercadoPredefinidoService, Depends(get_obtener_mercado_predefinido_service)
    ],
) -> MercadoPredefinidoResponse:
    mercado = await service.ejecutar(nombre)
    return _mercado_response(mercado)


@router.post(
    "",
    response_model=MercadoPredefinidoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crea un mercado predefinido",
    responses={
        404: {"description": "Algún producto referenciado no existe"},
        409: {"description": "Ya existe un mercado predefinido con ese nombre"},
    },
)
async def crear_mercado_predefinido(
    payload: CrearMercadoPredefinidoRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        CrearMercadoPredefinidoService, Depends(get_crear_mercado_predefinido_service)
    ],
) -> MercadoPredefinidoResponse:
    mercado = await service.ejecutar(
        CrearMercadoPredefinidoInput(
            nombre=payload.nombre,
            descripcion=payload.descripcion,
            productos=[
                ProductoKitInput(producto_id=p.producto_id, cantidad=p.cantidad)
                for p in payload.productos
            ],
        ),
        _audit_persona(usuario_actual),
    )
    return _mercado_response(mercado)


@router.put(
    "/{nombre}",
    response_model=MercadoPredefinidoResponse,
    summary="Actualiza un mercado predefinido existente",
    responses={
        404: {
            "description": "No existe el mercado, o algún producto referenciado no existe"
        },
    },
)
async def actualizar_mercado_predefinido(
    nombre: str,
    payload: ActualizarMercadoPredefinidoRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        ActualizarMercadoPredefinidoService, Depends(get_actualizar_mercado_predefinido_service)
    ],
) -> MercadoPredefinidoResponse:
    productos = (
        [
            ProductoKitInput(producto_id=p.producto_id, cantidad=p.cantidad)
            for p in payload.productos
        ]
        if payload.productos is not None
        else None
    )
    mercado = await service.ejecutar(
        nombre,
        ActualizarMercadoPredefinidoInput(
            descripcion=payload.descripcion, productos=productos, activo=payload.activo
        ),
        _audit_persona(usuario_actual),
    )
    return _mercado_response(mercado)
