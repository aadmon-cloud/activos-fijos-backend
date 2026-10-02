# app/schemas.py
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Modelos de Autenticación 
class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATIVO = "operativo"

class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[EmailStr] = None
    rol: UserRole = UserRole.OPERATIVO
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('El username solo puede contener letras, números y guiones bajos')
        return v.lower()

class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str]
    rol: UserRole
    is_active: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
# Esquemas para Productos
class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    #precio_unitario: float = Field(ge=0, default=0.0)
    stock_minimo: int = Field(ge=0, default=0)
    #ubicacion: Optional[str] = None

class ProductoCreate(ProductoBase):
    codigo: Optional[str] = None  # Si no se proporciona, se generará

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    #precio_unitario: Optional[float] = Field(None, ge=0)
    stock_minimo: Optional[int] = Field(None, ge=0)
    #ubicacion: Optional[str] = None

class Producto(ProductoBase):
    id: int
    codigo: str
    stock_actual: int
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class MovimientoBase(BaseModel):
    producto_id: int
    tipo: str = Field(..., pattern="^(entrada|salida|creacion_ubicacion|transferencia_ubicacion)$")
    cantidad: int = Field(..., gt=0)
    motivo: Optional[str] = None
    tipo_origen: Optional[str] = Field(
        None, description="compra, donacion, devolucion, traslado"
    )
    origen_nombre: Optional[str] = Field(
        None, description="Proveedor, donante o tercero"
    )
    ubicacion: Optional[str] = None
    ubicacion_origen: Optional[str] = None  
    ubicacion_destino: Optional[str] = None  
    notas: Optional[str] = None
    usuario: str = "admin"
    cliente_destino: Optional[str] = Field(
        None, description="Cliente o destino (para salidas)"
    )
    remision: Optional[str] = None
    caso: Optional[str] = None
    numero_cajas: Optional[int] = Field(None, ge=0)

class MovimientoCreate(MovimientoBase):
    pass

class Movimiento(MovimientoBase):
    id: int
    fecha_movimiento: datetime
    producto: Optional[Producto] = None
    pdf_firmado: Optional[str] = None
    pdf_nombre: Optional[str] = None
    
    class Config:
        from_attributes = True

# Esquemas para respuestas API
class InventarioProducto(BaseModel):
    producto: Producto
    historial: List[Movimiento] = []

class ReporteInventario(BaseModel):
    total_productos: int
    productos_bajo_stock: List[Producto]
    valor_total_inventario: float
    ultimos_movimientos: List[Movimiento]

# Esquema para escaneo
class CodigoEscaneado(BaseModel):
    codigo: str
    tipo_operacion: str = "consulta"  # entrada, salida, consulta
    # app/schemas.py (agregar al final)

# Esquema para múltiples productos en una salida
class SalidaMultipleCreate(BaseModel):
    productos: List[dict] = Field(..., description="Lista de productos con cantidad")
    destino: str = Field(..., min_length=1, description="Destino o responsable")
    razon: str = Field(..., min_length=1, description="Razón de la salida")
    observaciones: Optional[str] = None
    usuario: str = "admin"
    
    @validator('productos')
    def validar_productos(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Debe haber al menos un producto")
        
        for producto in v:
            if 'producto_id' not in producto or 'cantidad' not in producto:
                raise ValueError("Cada producto debe tener producto_id y cantidad")
            if producto['cantidad'] <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
        
        return v
    # app/schemas.py - Agregar al final

class EntradaMultipleCreate(BaseModel):
    productos: List[dict] = Field(..., description="Lista de productos con cantidad")
    tipo_origen: str = Field(..., description="compra, donacion, devolucion, traslado, ajuste")
    origen_nombre: str = Field(..., min_length=1, description="Proveedor, donante o tercero")
    ubicacion: Optional[str] = Field(None, description="Ubicación donde se almacena")
    observaciones: Optional[str] = None
    usuario: str = "admin"
    
    @validator('productos')
    def validar_productos(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Debe haber al menos un producto")
        
        for producto in v:
            if 'producto_id' not in producto or 'cantidad' not in producto:
                raise ValueError("Cada producto debe tener producto_id y cantidad")
            if producto['cantidad'] <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
        
        return v
    
    @validator('tipo_origen')
    def validar_tipo_origen(cls, v):
        tipos_validos = ['compra', 'donacion', 'devolucion', 'traslado', 'ajuste']
        v_lower = v.lower()
        if v_lower not in tipos_validos:
            raise ValueError(f"Tipo de origen debe ser uno de: {', '.join(tipos_validos)}")
        return v_lower

# ==========================================
# Modelos para Ubicaciones

class UbicacionBase(BaseModel):
    ubicacion: str = Field(..., min_length=1, max_length=100)
    stock_fisico: int = Field(ge=0, default=0)
    stock_reservado: int = Field(ge=0, default=0)

class UbicacionCreate(BaseModel):
    ubicacion: str = Field(..., min_length=1, max_length=100)
    cantidad: int = Field(ge=0, default=0)

class UbicacionUpdate(BaseModel):
    cantidad: int = Field(ge=0)

class TransferenciaStock(BaseModel):
    origen: str
    destino: str
    cantidad: int = Field(ge=1)

class ProductoConUbicaciones(BaseModel):
    producto: Producto
    ubicaciones: List[UbicacionBase]
    stock_por_ubicacion: List[dict]
    total_ubicaciones: int

# campo imagen

class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    stock_minimo: int = Field(ge=0, default=0)
    imagen_url: Optional[str] = None  # ← AGREGAR ESTE CAMPO

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    stock_minimo: Optional[int] = Field(None, ge=0)
    imagen_url: Optional[str] = None  # ← AGREGAR ESTE CAMPO

# ==========================================
# Esquemas para autenticación con email
# ==========================================

class UserLoginEmail(BaseModel):
    email: str = Field(..., description="Correo electrónico")
    password: str = Field(..., min_length=6)

class UserRegisterEmail(BaseModel):
    email: str = Field(..., description="Correo electrónico")
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)
    username: Optional[str] = None
    rol: UserRole = UserRole.OPERATIVO

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)