# app/routers/auth.py - VERSIÓN COMPLETA CON EMAIL

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
import secrets
from bson import ObjectId
import httpx 
from urllib.parse import urlencode
from authlib.integrations.starlette_client import OAuthError
from app.core.oauth import google
import os
from ..database import get_database
from ..schemas import UserLoginEmail, UserRegisterEmail, UserResponse, TokenResponse, UserRole
from ..schemas import ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
from ..core.security import hash_password, verify_password, create_access_token
from ..core.dependencies import get_current_user, require_super_admin, require_authenticated
from ..core.email import send_password_reset_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["autenticacion"])

# ==========================================
# LOGIN CON EMAIL
# ==========================================

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLoginEmail,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Iniciar sesión con email y contraseña"""
    # Buscar usuario por email (convertir a minúsculas)
    user = await db["users"].find_one({"email": login_data.email.lower()})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )
    
    if not verify_password(login_data.password, user.get("password_hash")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado. Contacte al administrador"
        )
    
    # Crear token con _id del usuario
    access_token = create_access_token(data={"sub": str(user["_id"]), "rol": user.get("rol")})
    
    # Usar username o email como nombre de usuario
    username = user.get("username") or user.get("email").split("@")[0]
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(user["_id"]),
            username=username,
            email=user.get("email"),
            rol=user.get("rol"),
            is_active=user.get("is_active", True)
        )
    )

# ==========================================
# REGISTRO DE USUARIOS (PÚBLICO)
# ==========================================

@router.post("/register", response_model=UserResponse)
async def register(
    register_data: UserRegisterEmail,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Registrar nuevo usuario (público)"""
    
    # Verificar si el email ya existe
    existing = await db["users"].find_one({"email": register_data.email.lower()})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Verificar que las contraseñas coincidan
    if register_data.password != register_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas no coinciden"
        )
    
    # Generar username si no se proporcionó
    username = register_data.username or register_data.email.split("@")[0]
    
    # Verificar si el username ya existe
    existing_username = await db["users"].find_one({"username": username})
    if existing_username:
        # Agregar sufijo al username
        username = f"{username}_{secrets.token_hex(3)}"
    
    # Crear nuevo usuario (email no verificado inicialmente)
    user_data = {
        "username": username,
        "email": register_data.email.lower(),
        "password_hash": hash_password(register_data.password),
        "rol": UserRole.OPERATIVO,  # Por defecto, rol operativo
        "created_at": datetime.utcnow(),
        "is_active": True,
        "email_verified": False,
        "reset_password_token": None,
        "reset_password_expires": None
    }
    
    result = await db["users"].insert_one(user_data)
    
    # Obtener usuario creado
    new_user = await db["users"].find_one({"_id": result.inserted_id})
    
    # Enviar email de bienvenida en segundo plano
    background_tasks.add_task(send_welcome_email, new_user["email"], new_user["username"])
    
    return UserResponse(
        id=str(new_user["_id"]),
        username=new_user["username"],
        email=new_user.get("email"),
        rol=new_user.get("rol"),
        is_active=new_user.get("is_active", True)
    )

# ==========================================
# RECUPERACIÓN DE CONTRASEÑA
# ==========================================

@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Solicitar recuperación de contraseña"""
    
    user = await db["users"].find_one({"email": request.email.lower()})
    
    if not user:
        # Por seguridad, no revelar si el email existe o no
        return {"message": "Si el email está registrado, recibirás un enlace de recuperación"}
    
    # Generar token único
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)
    
    # Guardar token en la base de datos
    await db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {
            "reset_password_token": token,
            "reset_password_expires": expires
        }}
    )
    
    # Enviar email en segundo plano
    background_tasks.add_task(send_password_reset_email, user["email"], token)
    
    return {"message": "Si el email está registrado, recibirás un enlace de recuperación"}

@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Restablecer contraseña con token"""
    
    # Verificar que las contraseñas coincidan
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas no coinciden"
        )
    
    # Buscar usuario con token válido
    user = await db["users"].find_one({
        "reset_password_token": request.token,
        "reset_password_expires": {"$gt": datetime.utcnow()}
    })
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado"
        )
    
    # Actualizar contraseña y eliminar token
    await db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password_hash": hash_password(request.new_password),
            "reset_password_token": None,
            "reset_password_expires": None
        }}
    )
    
    return {"message": "Contraseña actualizada exitosamente"}

# ==========================================
# CAMBIAR CONTRASEÑA (USUARIO AUTENTICADO)
# ==========================================

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(require_authenticated),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Cambiar contraseña del usuario autenticado"""
    
    # Verificar que las contraseñas coincidan
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas no coinciden"
        )
    
    # Verificar contraseña actual
    if not verify_password(request.current_password, current_user.get("password_hash")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña actual incorrecta"
        )
    
    # Actualizar contraseña
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="ID de usuario no encontrado")
    await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": hash_password(request.new_password)}}
    )
    
    return {"message": "Contraseña actualizada exitosamente"}

# ==========================================
# VERIFICAR EMAIL
# ==========================================

@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Verificar email del usuario"""
    
    # Buscar usuario con token de verificación (implementar si se desea)
    # Por ahora, retornamos mensaje
    return {"message": "Función de verificación de email en desarrollo"}

# ==========================================
# OBTENER USUARIO ACTUAL
# ==========================================

# ==========================================
# OBTENER USUARIO ACTUAL
# ==========================================

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(require_authenticated)):
    """Obtener información del usuario actual"""
    # En dependencies.py, _id se convirtió a 'id'
    user_id = current_user.get("id")
    
    if not user_id:
        # Fallback: intentar obtener de otra forma
        user_id = current_user.get("_id")
        if user_id:
            user_id = str(user_id)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo identificar al usuario"
        )
    
    username = current_user.get("username") or current_user.get("email", "").split("@")[0]
    
    return UserResponse(
        id=str(user_id),
        username=username,
        email=current_user.get("email"),
        rol=current_user.get("rol", "operativo"),
        is_active=current_user.get("is_active", True)
    )

# ==========================================
# INICIALIZAR USUARIOS POR DEFECTO
# ==========================================

@router.post("/init-users")
async def init_users(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Inicializar usuarios por defecto (solo ejecutar una vez)"""
    
    count = await db["users"].count_documents({})
    if count > 0:
        return {"message": "Los usuarios ya existen", "users_count": count}
    
    default_users = [
        {
            "username": "superadmin",
            "email": "superadmin@fimlm.org",
            "password_hash": hash_password("admin123"),
            "rol": UserRole.SUPER_ADMIN,
            "created_at": datetime.utcnow(),
            "is_active": True,
            "email_verified": True,
            "reset_password_token": None,
            "reset_password_expires": None
        },
        {
            "username": "admin",
            "email": "admin@fimlm.org",
            "password_hash": hash_password("admin123"),
            "rol": UserRole.ADMIN,
            "created_at": datetime.utcnow(),
            "is_active": True,
            "email_verified": True,
            "reset_password_token": None,
            "reset_password_expires": None
        },
        {
            "username": "operativo",
            "email": "operativo@fimlm.org",
            "password_hash": hash_password("operativo123"),
            "rol": UserRole.OPERATIVO,
            "created_at": datetime.utcnow(),
            "is_active": True,
            "email_verified": True,
            "reset_password_token": None,
            "reset_password_expires": None
        }
    ]
    
    await db["users"].insert_many(default_users)
    
    return {"message": "Usuarios creados exitosamente", "users_created": len(default_users)}
# ==========================================
# LOGIN CON GOOGLE - INICIO
# ==========================================

@router.get("/google")
async def google_login():
    """Iniciar sesión con Google - Redirige a Google OAuth"""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
    
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_CLIENT_ID no configurado"
        )
    
    # Construir URL de autorización de Google
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url)
# ==========================================
# LOGIN CON GOOGLE OAuth (VERSIÓN COMPLETA)
# ==========================================

@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Callback de Google OAuth"""
    try:
        # Obtener el código de autorización
        code = request.query_params.get('code')
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se recibió código de autorización"
            )
        
        # Intercambiar código por token usando HTTP directamente
        import httpx
        
        token_url = "https://oauth2.googleapis.com/token"
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data={
                    'code': code,
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code'
                }
            )
            token_data = token_response.json()
            
            if 'error' in token_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error obteniendo token: {token_data.get('error_description', token_data['error'])}"
                )
            
            # Obtener información del usuario con el token
            access_token = token_data.get('access_token')
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            
            user_response = await client.get(
                userinfo_url,
                headers={'Authorization': f'Bearer {access_token}'}
            )
            user_info = user_response.json()
        
        # Extraer datos de Google
        email = user_info.get('email')
        google_id = user_info.get('id')
        name = user_info.get('name', email.split('@')[0] if email else 'usuario')
        picture = user_info.get('picture')
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo obtener el email de Google"
            )
        
        # Buscar usuario por email o google_id
        user = await db["users"].find_one({
            "$or": [
                {"email": email.lower()},
                {"google_id": google_id}
            ]
        })
        
        if not user:
            # Crear nuevo usuario con Google
            username = name.lower().replace(" ", "_")
            
            # Verificar si username existe
            existing_username = await db["users"].find_one({"username": username})
            if existing_username:
                username = f"{username}_{google_id[-6:]}"
            
            user_data = {
                "username": username,
                "email": email.lower(),
                "google_id": google_id,
                "google_picture": picture,
                "password_hash": None,
                "rol": "operativo",
                "created_at": datetime.utcnow(),
                "is_active": True,
                "email_verified": True
            }
            
            result = await db["users"].insert_one(user_data)
            user = await db["users"].find_one({"_id": result.inserted_id})
        else:
            # Actualizar usuario existente con información de Google si falta
            update_data = {}
            if not user.get('google_id'):
                update_data['google_id'] = google_id
            if not user.get('google_picture') and picture:
                update_data['google_picture'] = picture
            if not user.get('email_verified'):
                update_data['email_verified'] = True
            
            if update_data:
                await db["users"].update_one(
                    {"_id": user["_id"]},
                    {"$set": update_data}
                )
                user = await db["users"].find_one({"_id": user["_id"]})
        
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario desactivado. Contacte al administrador"
            )
        
        # Crear token JWT
        access_token = create_access_token(data={
            "sub": str(user["_id"]), 
            "rol": user.get("rol")
        })
        
        # Redirigir al frontend con el token
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        redirect_url = f"{frontend_url}/auth/google-callback?token={access_token}"
        
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error inesperado: {e}")
        print(f"Detalles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )