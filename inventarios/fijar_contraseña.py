# fijar_contraseña.py
import bcrypt
from pymongo import MongoClient

# CONTRASEÑA SIMPLE - FÁCIL DE ESCRIBIR
# 👇 CAMBIA SOLO ESTA LÍNEA con la contraseña que QUIERAS
MI_CONTRASENA = "admin123"

# Generar hash
hash_generado = bcrypt.hashpw(MI_CONTRASENA.encode(), bcrypt.gensalt())

print("=" * 50)
print("🔧 ACTUALIZANDO CONTRASEÑA")
print("=" * 50)
print(f"Usuario: Dsalazar")
print(f"Contraseña: {MI_CONTRASENA}")
print(f"Hash: {hash_generado.decode()}")

# Conectar a MongoDB
client = MongoClient('mongodb://localhost:27017')
db = client['inventario_db']

# Actualizar usuario
result = db.users.update_one(
    {"username": "Dsalazar"},
    {"$set": {"password_hash": hash_generado.decode()}}
)

if result.modified_count > 0:
    print("\n✅ CONTRASEÑA ACTUALIZADA EXITOSAMENTE")
    print(f"\n🎉 CREDENCIALES CORRECTAS:")
    print(f"   Usuario: Dsalazar")
    print(f"   Contraseña: {MI_CONTRASENA}")
else:
    print("\n❌ Usuario no encontrado")

# Verificar
user = db.users.find_one({"username": "Dsalazar"})
if bcrypt.checkpw(MI_CONTRASENA.encode(), user['password_hash'].encode()):
    print("\n✅ VERIFICACIÓN EXITOSA")
else:
    print("\n❌ VERIFICACIÓN FALLIDA")

client.close()