# app/models.py
from datetime import datetime
from typing import Optional, List, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator
from bson import ObjectId
from pydantic_core import core_schema
from enum import Enum

# Clase para manejar ObjectId de MongoDB (versión Pydantic v2)
class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        json_schema = handler(core_schema)
        json_schema.update(type="string")
        return json_schema

# Modelo de Producto
class Producto(BaseModel):
    id: Optional[Union[str, PyObjectId]] = Field(default_factory=PyObjectId, alias="_id")
    codigo: str
    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    stock_minimo: int = Field(default=0, ge=0)
    stock_actual: int = Field(default=0, ge=0)
    precio_unitario: float = Field(default=0.0, ge=0)
    ubicacion: Optional[str] = None
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "codigo": "PROD-20240101-ABC123",
                "nombre": "Laptop HP EliteBook",
                "categoria": "Electrónica",
                "stock_minimo": 5,
                "stock_actual": 10,
                "precio_unitario": 999.99
            }
        }
    )

# Modelo de Movimiento
class Movimiento(BaseModel):
    id: Optional[Union[str, PyObjectId]] = Field(default_factory=PyObjectId, alias="_id")
    producto_id: str
    producto_nombre: str
    tipo: str
    cantidad: int = Field(..., gt=0)
    motivo: Optional[str] = None
    tipo_origen: Optional[str] = None
    origen_nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    notas: Optional[str] = None
    cliente_destino: Optional[str] = None
    usuario: str = Field(default="admin")
    fecha_movimiento: datetime = Field(default_factory=datetime.utcnow)
    pdf_firmado: Optional[str] = None
    pdf_nombre: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "producto_id": "PROD-20240101-ABC123",
                "producto_nombre": "Laptop HP",
                "tipo": "entrada",
                "cantidad": 5,
                "motivo": "Compra",
                "origen_nombre": "Proveedor XYZ",
                "usuario": "admin"
            }
        }
    )
    
    @field_validator('tipo')
    def validate_tipo(cls, v):
        if v not in ['entrada', 'salida']:
            raise ValueError('tipo debe ser "entrada" o "salida"')
        return v

# Esquema para ProductoCreate (sin ID)
class ProductoCreate(BaseModel):
    codigo: Optional[str] = None
    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    stock_minimo: int = Field(default=0, ge=0)
    precio_unitario: float = Field(default=0.0, ge=0)
    ubicacion: Optional[str] = None

# Esquema para ProductoUpdate
class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    stock_minimo: Optional[int] = Field(None, ge=0)
    precio_unitario: Optional[float] = Field(None, ge=0)
    ubicacion: Optional[str] = None

# Esquema para MovimientoCreate
class MovimientoCreate(BaseModel):
    producto_id: str
    tipo: str
    cantidad: int = Field(..., gt=0)
    motivo: Optional[str] = None
    tipo_origen: Optional[str] = None
    origen_nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    notas: Optional[str] = None
    cliente_destino: Optional[str] = None
    usuario: str = "admin"
    usuario_id: Optional[str] = None
    
    @field_validator('tipo')
    def validate_tipo(cls, v):
        if v not in ['entrada', 'salida']:
            raise ValueError('tipo debe ser "entrada" o "salida"')
        return v

# Esquema para SalidaMultipleCreate
class SalidaMultipleCreate(BaseModel):
    productos: List[dict]
    destino: str = Field(..., min_length=1)
    razon: str = Field(..., min_length=1)
    observaciones: Optional[str] = None
    usuario: str = "admin"
    
    @field_validator('productos')
    def validar_productos(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Debe haber al menos un producto")
        
        for producto in v:
            if 'producto_id' not in producto or 'cantidad' not in producto:
                raise ValueError("Cada producto debe tener producto_id y cantidad")
            if producto['cantidad'] <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
        
        return v

# Esquema para EntradaMultipleCreate
class EntradaMultipleCreate(BaseModel):
    productos: List[dict]
    tipo_origen: str
    origen_nombre: str = Field(..., min_length=1)
    ubicacion: Optional[str] = None
    observaciones: Optional[str] = None
    usuario: str = "admin"
    
    @field_validator('productos')
    def validar_productos(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Debe haber al menos un producto")
        
        for producto in v:
            if 'producto_id' not in producto or 'cantidad' not in producto:
                raise ValueError("Cada producto debe tener producto_id y cantidad")
            if producto['cantidad'] <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
        
        return v
    
    @field_validator('tipo_origen')
    def validar_tipo_origen(cls, v):
        tipos_validos = ['compra', 'donacion', 'devolucion', 'traslado', 'ajuste']
        v_lower = v.lower()
        if v_lower not in tipos_validos:
            raise ValueError(f"Tipo de origen debe ser uno de: {', '.join(tipos_validos)}")
        return v_lower

# Esquemas para reportes
class InventarioProducto(BaseModel):
    producto: Producto
    historial: List[Movimiento] = []

class ReporteInventario(BaseModel):
    total_productos: int
    productos_bajo_stock: List[Producto]
    valor_total_inventario: float
    ultimos_movimientos: List[Movimiento]

class CodigoEscaneado(BaseModel):
    codigo: str
    tipo_operacion: str = "consulta"
    
    @field_validator('tipo_operacion')
    def validate_tipo_operacion(cls, v):
        if v not in ['entrada', 'salida', 'consulta']:
            raise ValueError('tipo_operacion debe ser "entrada", "salida" o "consulta"')
        return v
# Modelo para Reservas (salidas pendientes)
class Reserva(BaseModel):
    id: Optional[Union[str, PyObjectId]] = Field(default_factory=PyObjectId, alias="_id")
    session_id: str = Field(..., description="Identificador único de la sesión/ventana")
    items: List[dict] = Field(..., description="Lista de productos reservados")
    tipo: str = Field(default="salida_pendiente")
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: datetime = Field(default_factory=datetime.now)
    datos_adicionales: Optional[dict] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "session_id": "session_12345",
                "items": [
                    {"producto_id": "ALI1", "cantidad": 5, "producto_nombre": "ACEITE 1000 ML"},
                    {"producto_id": "ALI2", "cantidad": 3, "producto_nombre": "ACEITE 2000 CC"}
                ],
                "tipo": "salida_pendiente"
            }
        }
    )

# Esquema para crear/actualizar reserva
class ReservaCreate(BaseModel):
    session_id: str
    items: List[dict]
    datos_adicionales: Optional[dict] = None

# Esquema para respuesta de reserva
class ReservaResponse(BaseModel):
    id: str
    session_id: str
    items: List[dict]
    tipo: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    datos_adicionales: Optional[dict] = None

class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"  
    ADMIN = "admin"              
    OPERATIVO = "operativo"      

# clase UserInDB

class UserInDB(BaseModel):
    username: Optional[str] = None  # Opcional, mantiene compatibilidad
    email: str  # ← AHORA ES OBLIGATORIO
    password_hash: str
    rol: UserRole = UserRole.OPERATIVO
    created_at: datetime = datetime.now()
    is_active: bool = True
    email_verified: bool = False  # ← NUEVO: verificar email
    reset_password_token: Optional[str] = None  # ← NUEVO: token para recuperar contraseña
    reset_password_expires: Optional[datetime] = None  # ← NUEVO: expiración del token
    
# ==========================================
# Modelos para Número de Remisión
# ==========================================

class ContadorRemision(BaseModel):
    """Modelo para llevar el contador de remisiones"""
    id: Optional[Union[str, PyObjectId]] = Field(default_factory=PyObjectId, alias="_id")
    nombre: str = "remision"
    ultimo_numero: int = Field(default=0)
    prefijo: str = Field(default="RM")
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

# ==========================================
# Modelos para Mercados Predefinidos
# ==========================================

class MercadoPredefinido(BaseModel):
    """Modelo para mercados predefinidos (Básico, Grande)"""
    id: Optional[Union[str, PyObjectId]] = Field(default_factory=PyObjectId, alias="_id")
    nombre: str = Field(..., description="MERCADO_BASICO o MERCADO_GRANDE")
    descripcion: Optional[str] = None
    productos: List[dict] = Field(..., description="[{'producto_id': 'ALI1', 'cantidad': 2}, ...]")
    activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "nombre": "MERCADO_BASICO",
                "descripcion": "Mercado básico para familias",
                "productos": [
                    {"producto_id": "ALI1", "cantidad": 2, "producto_nombre": "ACEITE 1000 ML"},
                    {"producto_id": "ALI2", "cantidad": 1, "producto_nombre": "ACEITE 2000 CC"},
                    {"producto_id": "ALI6", "cantidad": 5, "producto_nombre": "ARROZ GOLONDRINA 500 GR"}
                ]
            }
        }
    )

# Esquema para crear/actualizar mercado
class MercadoPredefinidoCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    productos: List[dict]
    activo: bool = True

# Modelo de Movimiento actualizado con remision y referencia
class Movimiento(BaseModel):
    id: Optional[Union[str, PyObjectId]] = Field(default_factory=PyObjectId, alias="_id")
    producto_id: str
    producto_nombre: str
    tipo: str
    cantidad: int = Field(..., gt=0)
    motivo: Optional[str] = None
    tipo_origen: Optional[str] = None
    origen_nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    notas: Optional[str] = None
    cliente_destino: Optional[str] = None
    usuario: str = Field(default="admin")
    fecha_movimiento: datetime = Field(default_factory=datetime.utcnow)
    pdf_firmado: Optional[str] = None
    pdf_nombre: Optional[str] = None
    # NUEVOS CAMPOS
    remision: Optional[str] = None  # Número de remisión (ej: RM-001)
    referencia: Optional[str] = None  # Campo de referencia libre
    es_kit_mercado: Optional[bool] = False  # Si es salida de mercado predefinido
    nombre_mercado: Optional[str] = None  # Nombre del mercado seleccionado
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    @field_validator('tipo')
    def validate_tipo(cls, v):
        if v not in ['entrada', 'salida']:
            raise ValueError('tipo debe ser "entrada" o "salida"')
        return v