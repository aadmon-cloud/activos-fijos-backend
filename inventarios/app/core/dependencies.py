# app/core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from ..database import get_database
from .security import decode_token

security = HTTPBearer()

# app/core/dependencies.py

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Obtener usuario actual desde el token JWT"""
    token = credentials.credentials
    
    # ✅ AGREGAR LOGS
    print(f"🔵 === get_current_user ===")
    print(f"🔵 Token recibido: {token[:50]}..." if token else "🔵 NO HAY TOKEN")
    
    payload = decode_token(token)
    
    if payload is None:
        print(f"❌ Token inválido o expirado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"🔵 Payload decodificado: {payload}")
    
    user_id = payload.get("sub")
    if user_id is None:
        print(f"❌ Token sin sub")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    
    # Buscar usuario por _id
    try:
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
        print(f"🔵 Usuario encontrado: {user.get('email') if user else 'No encontrado'}")
    except Exception as e:
        print(f"❌ Error buscando usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado",
        )
    
    # Convertir ObjectId a string
    user["id"] = str(user["_id"])
    del user["_id"]
    
    print(f"🔵 Usuario autenticado: {user.get('email')}, rol: {user.get('rol')}")
    
    return user

def require_role(required_roles: list):
    """Factory para crear dependencias de verificación de roles"""
    async def role_checker(user = Depends(get_current_user)):
        if user.get("rol") not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de los siguientes roles: {', '.join(required_roles)}"
            )
        return user
    return role_checker

# Dependencias predefinidas
require_super_admin = require_role(["super_admin"])
require_admin_or_super = require_role(["super_admin", "admin"])
require_authenticated = require_role(["super_admin", "admin", "operativo"])