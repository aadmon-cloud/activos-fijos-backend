# app/database.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
import os
from typing import Optional
import asyncio

# Configuración
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "inventario_db"

# Cliente MongoDB
client: Optional[AsyncIOMotorClient] = None

async def connect_to_mongo():
    """Conectar a MongoDB con manejo de errores"""
    global client
    try:
        print(f"🔌 Intentando conectar a MongoDB en: {MONGO_URL}")
        print(f"📁 Base de datos: {DATABASE_NAME}")
        
        # Crear cliente con timeout
        client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        
        # Verificar conexión (esto lanzará una excepción si no puede conectar)
        await client.admin.command('ping')
        print("✅ Conexión a MongoDB establecida exitosamente")
        
        # Verificar que la base de datos existe o crearla
        db = client[DATABASE_NAME]
        await db.command("ping")
        print(f"✅ Base de datos '{DATABASE_NAME}' disponible")
        
        # Crear índices
        await create_indexes()
        
    except Exception as e:
        print(f"❌ Error conectando a MongoDB: {e}")
        print("💡 Soluciones posibles:")
        print("   1. Verifica que MongoDB esté corriendo: 'net start MongoDB'")
        print("   2. Verifica la URL de conexión en .env")
        print("   3. Espera unos segundos y reintenta")
        raise

async def close_mongo_connection():
    """Cerrar conexión a MongoDB"""
    global client
    if client:
        client.close()
        print("✅ Conexión a MongoDB cerrada")

def get_database() -> AsyncIOMotorDatabase:
    """Obtener la base de datos"""
    if client is None:
        raise Exception("MongoDB no está conectado. Llama a connect_to_mongo() primero.")
    return client[DATABASE_NAME]

def get_collection(collection_name: str):
    """Obtener una colección"""
    db = get_database()
    return db[collection_name]

async def create_indexes():
    """Crear índices para optimizar consultas"""
    try:
        db = get_database()
        print("🔧 Creando índices...")
        
        # Índices para productos
        productos = db["productos"]
        await productos.create_indexes([
            IndexModel([("codigo", ASCENDING)], unique=True),
            IndexModel([("nombre", TEXT)], default_language="spanish"),
            IndexModel([("categoria", ASCENDING)]),
            IndexModel([("stock_actual", ASCENDING)]),
            IndexModel([("fecha_creacion", DESCENDING)])
        ])
        
        # Índices para movimientos
        movimientos = db["movimientos"]
        await movimientos.create_indexes([
            IndexModel([("producto_id", ASCENDING)]),
            IndexModel([("fecha_movimiento", DESCENDING)]),
            IndexModel([("tipo", ASCENDING)]),
            IndexModel([("producto_id", ASCENDING), ("fecha_movimiento", DESCENDING)])
        ])
        
        print("✅ Índices creados correctamente")
        
    except Exception as e:
        print(f"⚠️ Error creando índices: {e}")
        print("   Los índices se crearán automáticamente cuando se use la base de datos")

async def init_db():
    """Inicializar la base de datos (crear índices)"""
    await create_indexes()
    print("✅ Base de datos inicializada correctamente")

# Función síncrona para obtener la base de datos en dependencias
def get_db():
    """Generator para obtener la base de datos en dependencias"""
    return get_database()