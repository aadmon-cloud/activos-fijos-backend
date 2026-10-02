# app/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
import secrets

from ..database import get_database
from ..core.security import hash_password
from ..core.dependencies import require_super_admin

router = APIRouter(prefix="/admin", tags=["administracion"])

@router.get("/users")
async def get_all_users(
    current_user: dict = Depends(require_super_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Obtener todos los usuarios (solo super_admin)"""
    users = await db["users"].find().to_list(length=100)
    
    result = []
    for user in users:
        result.append({
            "id": str(user["_id"]),
            "username": user.get("username", ""),
            "email": user.get("email", ""),
            "rol": user.get("rol", "operativo"),
            "is_active": user.get("is_active", True),
            "created_at": user.get("created_at", datetime.utcnow()),
            "google_id": user.get("google_id"),
            "email_verified": user.get("email_verified", False)
        })
    
    return result

@router.post("/users")
async def create_user(
    user_data: dict,
    current_user: dict = Depends(require_super_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Crear un nuevo usuario (solo super_admin)"""
    print(f"📝 Creando usuario con datos: {user_data}")  # Debug
    
    email = user_data.get("email", "").lower()
    username = user_data.get("username") or email.split("@")[0]
    rol = user_data.get("rol", "operativo")
    password = user_data.get("password")
    
    # Validar rol
    if rol not in ["super_admin", "admin", "operativo"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol inválido: {rol}. Debe ser super_admin, admin o operativo"
        )
    
    # Verificar si el email ya existe
    existing = await db["users"].find_one({"email": email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Verificar si el username ya existe
    existing_username = await db["users"].find_one({"username": username})
    if existing_username:
        username = f"{username}_{secrets.token_hex(3)}"
    
    # Crear usuario
    user_document = {
        "username": username,
        "email": email,
        "password_hash": hash_password(password) if password else None,
        "rol": rol,
        "created_at": datetime.utcnow(),
        "is_active": True,
        "email_verified": False,
        "reset_password_token": None,
        "reset_password_expires": None
    }
    
    result = await db["users"].insert_one(user_document)
    
    print(f"✅ Usuario creado: {email} con rol {rol}")  # Debug
    
    return {
        "id": str(result.inserted_id),
        "username": username,
        "email": email,
        "rol": rol,
        "is_active": True,
        "message": "Usuario creado exitosamente"
    }

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: dict,
    current_user: dict = Depends(require_super_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Actualizar un usuario existente (solo super_admin)"""
    
    # No permitir modificar al propio super_admin
    if user_id == current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes modificar tu propio usuario aquí"
        )
    
    # Buscar usuario
    try:
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
    except:
        user = None
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Preparar datos a actualizar
    update_fields = {}
    
    if "username" in user_data and user_data["username"]:
        update_fields["username"] = user_data["username"]
    
    if "rol" in user_data and user_data["rol"]:
        if user_data["rol"] not in ["super_admin", "admin", "operativo"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rol inválido: {user_data['rol']}"
            )
        update_fields["rol"] = user_data["rol"]
    
    if "password" in user_data and user_data["password"]:
        update_fields["password_hash"] = hash_password(user_data["password"])
    
    if "is_active" in user_data:
        update_fields["is_active"] = user_data["is_active"]
    
    if update_fields:
        await db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_fields}
        )
    
    return {"message": "Usuario actualizado exitosamente"}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_super_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Eliminar un usuario (solo super_admin)"""
    
    # No permitir eliminar al propio super_admin
    if user_id == current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propio usuario"
        )
    
    # Buscar usuario
    try:
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
    except:
        user = None
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Eliminar usuario
    await db["users"].delete_one({"_id": ObjectId(user_id)})
    
    return {"message": "Usuario eliminado exitosamente"}