# app/crud.py - Versión MongoDB
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from .utils.codigos import generar_codigo_producto

# ==========================================
# CRUD Productos
# ==========================================

async def get_producto(db: AsyncIOMotorDatabase, producto_id: str):
    """
    Obtener un producto por ID (ahora es string)
    """
    collection = db["productos"]
    try:
        # El ID ahora es el código del producto o ObjectId
        if ObjectId.is_valid(producto_id):
            producto = await collection.find_one({"_id": ObjectId(producto_id)})
        else:
            producto = await collection.find_one({"codigo": producto_id})
        
        if producto and '_id' in producto:
            producto['id'] = str(producto['_id'])
            del producto['_id']
        return producto
    except:
        return None

async def get_producto_por_codigo(db: AsyncIOMotorDatabase, codigo: str):
    """Obtener un producto por código"""
    collection = db["productos"]
    producto = await collection.find_one({"codigo": codigo})
    if producto and '_id' in producto:
        producto['id'] = str(producto['_id'])
        del producto['_id']
    return producto

# app/crud.py
async def get_productos(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100):
    """
    Obtener productos con paginación
    """
    try:
        collection = db["productos"]
        print("🔵 Buscando productos en MongoDB...")
        
        cursor = collection.find().skip(skip).limit(limit).sort("fecha_creacion", -1)
        productos = await cursor.to_list(length=limit)
        
        print(f"✅ Encontrados {len(productos)} productos")
        
        # Convertir ObjectId a string para cada producto
        for producto in productos:
            if '_id' in producto:
                producto['id'] = str(producto['_id'])
                del producto['_id']
        
        return productos
    except Exception as e:
        print(f"❌ Error en get_productos: {e}")
        import traceback
        traceback.print_exc()
        raise e

async def crear_producto(db: AsyncIOMotorDatabase, producto):
    """
    Crear un nuevo producto
    """
    collection = db["productos"]
    
    # Generar código si no se proporcionó
    codigo = producto.codigo if producto.codigo else generar_codigo_producto()
    
    # Verificar si el código ya existe
    existente = await collection.find_one({"codigo": codigo})
    if existente:
        raise ValueError(f"El código {codigo} ya existe")
    
    # Crear documento
    producto_dict = {
        "codigo": codigo,
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "categoria": producto.categoria,
        "stock_minimo": producto.stock_minimo,
        "stock_actual": 0,
        "imagen_url": getattr(producto, 'imagen_url', None),
        "fecha_creacion": datetime.now(),
        "fecha_actualizacion": None
    }
    
    result = await collection.insert_one(producto_dict)
    nuevo_producto = await collection.find_one({"_id": result.inserted_id})
    
    if nuevo_producto and '_id' in nuevo_producto:
        nuevo_producto['id'] = str(nuevo_producto['_id'])
        del nuevo_producto['_id']
    
    return nuevo_producto

async def actualizar_producto(db: AsyncIOMotorDatabase, producto_id: str, producto):
    """
    Actualizar un producto existente
    """
    collection = db["productos"]
    
    # Preparar datos para actualizar
    update_data = producto.dict(exclude_unset=True)
    if update_data:
        update_data["fecha_actualizacion"] = datetime.now()
    
    # Buscar por ID o código
    query = {}
    if ObjectId.is_valid(producto_id):
        query["_id"] = ObjectId(producto_id)
    else:
        query["codigo"] = producto_id
    
    result = await collection.update_one(
        query,
        {"$set": update_data}
    )
    
    if result.modified_count > 0:
        producto_actualizado = await collection.find_one(query)
        if producto_actualizado and '_id' in producto_actualizado:
            producto_actualizado['id'] = str(producto_actualizado['_id'])
            del producto_actualizado['_id']
        return producto_actualizado
    
    return None

async def contar_productos(db: AsyncIOMotorDatabase):
    """
    Cuenta productos sin cargar todos los datos
    """
    collection = db["productos"]
    return await collection.count_documents({})

async def eliminar_producto(db: AsyncIOMotorDatabase, producto_id: str):
    """
    Eliminar un producto
    """
    collection = db["productos"]
    
    # Buscar por ID o código
    query = {}
    if ObjectId.is_valid(producto_id):
        query["_id"] = ObjectId(producto_id)
    else:
        query["codigo"] = producto_id
    
    result = await collection.delete_one(query)
    return result.deleted_count > 0

async def crear_movimiento(db: AsyncIOMotorDatabase, movimiento):
    """
    Crear un nuevo movimiento (entrada o salida)
    """
    productos_col = db["productos"]
    movimientos_col = db["movimientos"]
    ubicaciones_col = db["ubicaciones"]
    
    # Obtener producto por código
    producto = await productos_col.find_one({"codigo": movimiento.producto_id})
    if not producto:
        raise ValueError(f"Producto con código {movimiento.producto_id} no encontrado")
    
    # Generar número de remisión solo para salidas
    remision = None
    if movimiento.tipo == "salida":
        remision = await generar_numero_remision(db)
    
    # Crear movimiento
    movimiento_dict = {
        "producto_id": movimiento.producto_id,
        "producto_nombre": producto["nombre"],
        "tipo": movimiento.tipo,
        "cantidad": movimiento.cantidad,
        "motivo": movimiento.motivo,
        "tipo_origen": movimiento.tipo_origen,
        "origen_nombre": movimiento.origen_nombre,
        "ubicacion": movimiento.ubicacion,  # ← Usar la ubicación que viene del frontend
        "notas": movimiento.notas,
        "cliente_destino": movimiento.cliente_destino,
        "usuario": movimiento.usuario,
        "fecha_movimiento": datetime.utcnow(),
        "pdf_firmado": None,
        "pdf_nombre": None,
        "remision": remision,
        "caso": getattr(movimiento, 'caso', None),
        "numero_cajas": getattr(movimiento, 'numero_cajas', None)
    }
    
    # ==========================================
    # ACTUALIZAR STOCK DEL PRODUCTO
    # ==========================================
    if movimiento.tipo == "entrada":
        nuevo_stock = producto["stock_actual"] + movimiento.cantidad
    elif movimiento.tipo == "salida":
        if producto["stock_actual"] < movimiento.cantidad:
            raise ValueError("Stock insuficiente")
        nuevo_stock = producto["stock_actual"] - movimiento.cantidad
    else:
        raise ValueError("Tipo de movimiento inválido")
    
    # Actualizar producto (stock total)
    await productos_col.update_one(
        {"codigo": movimiento.producto_id},
        {"$set": {
            "stock_actual": nuevo_stock,
            "fecha_actualizacion": datetime.now()
        }}
    )
    
    # ==========================================
    # MANEJO DE UBICACIONES
    # ==========================================
    if movimiento.tipo == "entrada":
        # Para entradas, usar la ubicación especificada o ALMACEN_GENERAL por defecto
        ubicacion_nombre = movimiento.ubicacion if movimiento.ubicacion else "ALMACEN_GENERAL"
        
        ubicacion_existente = await ubicaciones_col.find_one({
            "producto_codigo": movimiento.producto_id,
            "ubicacion": ubicacion_nombre
        })
        
        if ubicacion_existente:
            # Sumar al stock de la ubicación existente
            await ubicaciones_col.update_one(
                {"_id": ubicacion_existente["_id"]},
                {"$inc": {"stock_fisico": movimiento.cantidad}}
            )
            print(f"📍 Entrada: +{movimiento.cantidad} a {ubicacion_nombre}")
        else:
            # Crear nueva ubicación
            await ubicaciones_col.insert_one({
                "producto_codigo": movimiento.producto_id,
                "ubicacion": ubicacion_nombre,
                "stock_fisico": movimiento.cantidad,
                "stock_reservado": 0,
                "fecha_creacion": datetime.now()
            })
            print(f"📍 Nueva ubicación creada: {ubicacion_nombre} con {movimiento.cantidad} unidades")
    
    elif movimiento.tipo == "salida":
        # Para salidas, descontar de la ubicación específica (obligatoria)
        if not movimiento.ubicacion:
            raise ValueError("Para salidas, la ubicación es obligatoria")
        
        ubicacion_existente = await ubicaciones_col.find_one({
            "producto_codigo": movimiento.producto_id,
            "ubicacion": movimiento.ubicacion
        })
        
        if not ubicacion_existente:
            raise ValueError(f"Ubicación {movimiento.ubicacion} no encontrada para el producto {movimiento.producto_id}")
        
        if ubicacion_existente.get("stock_fisico", 0) < movimiento.cantidad:
            raise ValueError(f"Stock insuficiente en ubicación {movimiento.ubicacion}. Disponible: {ubicacion_existente.get('stock_fisico', 0)}")
        
        await ubicaciones_col.update_one(
            {"_id": ubicacion_existente["_id"]},
            {"$inc": {"stock_fisico": -movimiento.cantidad}}
        )
        print(f"📍 Salida: -{movimiento.cantidad} de {movimiento.ubicacion}")
    
    # Insertar movimiento
    result = await movimientos_col.insert_one(movimiento_dict)
    nuevo_movimiento = await movimientos_col.find_one({"_id": result.inserted_id})
    
    if nuevo_movimiento and '_id' in nuevo_movimiento:
        nuevo_movimiento['id'] = str(nuevo_movimiento['_id'])
        del nuevo_movimiento['_id']
    
    return nuevo_movimiento

async def get_movimientos(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100):
    """
    Obtener lista de movimientos
    """
    collection = db["movimientos"]
    cursor = collection.find().sort("fecha_movimiento", -1).skip(skip).limit(limit)
    movimientos = await cursor.to_list(length=limit)
    
    for mov in movimientos:
        if '_id' in mov:
            mov['id'] = str(mov['_id'])
            del mov['_id']
    
    return movimientos

async def get_movimientos_por_producto(db: AsyncIOMotorDatabase, producto_id: str):
    """
    Obtener movimientos de un producto específico
    """
    collection = db["movimientos"]
    cursor = collection.find({"producto_id": producto_id}).sort("fecha_movimiento", -1)
    movimientos = await cursor.to_list(length=None)
    
    for mov in movimientos:
        if '_id' in mov:
            mov['id'] = str(mov['_id'])
            del mov['_id']
    
    return movimientos

# ==========================================
# Inventario y reportes
# ==========================================

async def get_productos_bajo_stock(db: AsyncIOMotorDatabase):
    """
    Obtener productos con stock por debajo del mínimo
    """
    collection = db["productos"]
    cursor = collection.find({
        "$expr": {"$lt": ["$stock_actual", "$stock_minimo"]}
    })
    productos = await cursor.to_list(length=None)
    
    for producto in productos:
        if '_id' in producto:
            producto['id'] = str(producto['_id'])
            del producto['_id']
    
    return productos

# ==========================================
# Búsqueda de productos
# ==========================================

async def buscar_productos(db: AsyncIOMotorDatabase, query: str):
    """
    Buscar productos por nombre, código o descripción
    """
    print(f"CRUD: Buscando '{query}'")
    
    collection = db["productos"]
    query_lower = query.lower()
    
    productos = await collection.find({
        "$or": [
            {"nombre": {"$regex": query_lower, "$options": "i"}},
            {"codigo": {"$regex": query_lower, "$options": "i"}},
            {"descripcion": {"$regex": query_lower, "$options": "i"}}
        ]
    }).to_list(length=None)
    
    print(f"CRUD: Encontrados {len(productos)} productos")
    
    for producto in productos:
        if '_id' in producto:
            producto['id'] = str(producto['_id'])
            del producto['_id']
    
    return productos

# ==========================================
# Salida múltiple
# ==========================================

async def crear_salida_multiple(
    db: AsyncIOMotorDatabase,
    productos: list,
    destino: str,
    razon: str,
    observaciones: str = None,
    usuario: str = "admin"
):
    """
    Crear múltiples salidas
    """
    movimientos_creados = []
    productos_col = db["productos"]
    movimientos_col = db["movimientos"]
    
    try:
        # Verificar stock primero
        for item in productos:
            producto = await productos_col.find_one({"codigo": item['producto_id']})
            if not producto:
                raise ValueError(f"Producto {item['producto_id']} no encontrado")
            if producto['stock_actual'] < item['cantidad']:
                raise ValueError(
                    f"Stock insuficiente para {producto['nombre']}. "
                    f"Solicitado: {item['cantidad']}, Disponible: {producto['stock_actual']}"
                )
        
        # Crear movimientos
        for item in productos:
            producto = await productos_col.find_one({"codigo": item['producto_id']})
            
            # Crear movimiento
            movimiento_dict = {
                "producto_id": item['producto_id'],
                "producto_nombre": producto["nombre"],
                "tipo": "salida",
                "cantidad": item['cantidad'],
                "motivo": razon,
                "notas": f"Destino: {destino}" + (f" - {observaciones}" if observaciones else ""),
                "usuario": usuario,
                "fecha_movimiento": datetime.utcnow(),
                "pdf_firmado": None,
                "pdf_nombre": None
            }
            
            # Actualizar stock
            nuevo_stock = producto['stock_actual'] - item['cantidad']
            await productos_col.update_one(
                {"codigo": item['producto_id']},
                {"$set": {
                    "stock_actual": nuevo_stock,
                    "fecha_actualizacion": datetime.now()
                }}
            )
            
            # Insertar movimiento
            result = await movimientos_col.insert_one(movimiento_dict)
            nuevo_movimiento = await movimientos_col.find_one({"_id": result.inserted_id})
            
            if nuevo_movimiento and '_id' in nuevo_movimiento:
                nuevo_movimiento['id'] = str(nuevo_movimiento['_id'])
                del nuevo_movimiento['_id']
            
            movimientos_creados.append(nuevo_movimiento)
        
        return movimientos_creados
        
    except Exception as e:
        # En MongoDB no hay rollback automático, pero lanzamos el error
        raise e

# ==========================================
# Entrada múltiple
# ==========================================

async def crear_entrada_multiple(
    db: AsyncIOMotorDatabase,
    productos: list,
    tipo_origen: str,
    origen_nombre: str,
    ubicacion: str = None,
    observaciones: str = None,
    usuario: str = "admin"
):
    """
    Crear una sola entrada con múltiples productos (compra, donación, devolución, etc.)
    """
    productos_col = db["productos"]
    movimientos_col = db["movimientos"]
    ubicaciones_col = db["ubicaciones"]
    
    # Lista para guardar los productos con sus ubicaciones
    productos_con_ubicacion = []
    
    try:
        for item in productos:
            producto = await productos_col.find_one({"codigo": item['producto_id']})
            if not producto:
                raise ValueError(f"Producto {item['producto_id']} no encontrado")
            
            # Obtener la ubicación del producto (si viene en el item) o usar la global
            ubicacion_producto = item.get('ubicacion') or ubicacion or 'ALMACEN_GENERAL'
            
            # Guardar producto para el movimiento múltiple
            productos_con_ubicacion.append({
                "producto_id": item['producto_id'],
                "producto_nombre": producto["nombre"],
                "producto_codigo": item['producto_id'],
                "cantidad": item['cantidad'],
                "ubicacion": item.get('ubicacion', 'ALMACEN_GENERAL')
            })
            
            # Actualizar stock del producto
            nuevo_stock = producto['stock_actual'] + item['cantidad']
            await productos_col.update_one(
                {"codigo": item['producto_id']},
                {"$set": {
                    "stock_actual": nuevo_stock,
                    "fecha_actualizacion": datetime.now()
                }}
            )
            
            # Actualizar stock en la ubicación específica
            ubicacion_existente = await ubicaciones_col.find_one({
                "producto_codigo": item['producto_id'],
                "ubicacion": ubicacion_producto
            })
            
            if ubicacion_existente:
                await ubicaciones_col.update_one(
                    {"_id": ubicacion_existente["_id"]},
                    {"$inc": {"stock_fisico": item['cantidad']}}
                )
                print(f"📍 Entrada: +{item['cantidad']} a {ubicacion_producto} para {producto['nombre']}")
            else:
                await ubicaciones_col.insert_one({
                    "producto_codigo": item['producto_id'],
                    "ubicacion": ubicacion_producto,
                    "stock_fisico": item['cantidad'],
                    "stock_reservado": 0,
                    "fecha_creacion": datetime.now()
                })
                print(f"📍 Nueva ubicación creada: {ubicacion_producto} con {item['cantidad']} unidades para {producto['nombre']}")
        
        # Crear UN SOLO movimiento con todos los productos
        movimiento_multiple = {
            "producto_id": f"ENTRADA_MULTIPLE_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "producto_nombre": "Entrada Múltiple",
            "tipo": "entrada",
            "cantidad": sum(p['cantidad'] for p in productos_con_ubicacion),
            "motivo": tipo_origen.capitalize(),
            "tipo_origen": tipo_origen,
            "origen_nombre": origen_nombre,
            "ubicacion": None,  # No hay una ubicación única
            "notas": observaciones,
            "usuario": usuario,
            "fecha_movimiento": datetime.utcnow(),
            "pdf_firmado": None,
            "pdf_nombre": None,
            "productos_multiple": productos_con_ubicacion,  # ← Lista de productos con ubicaciones
            "es_entrada_multiple": True
        }
        
        # Insertar el movimiento múltiple
        result = await movimientos_col.insert_one(movimiento_multiple)
        nuevo_movimiento = await movimientos_col.find_one({"_id": result.inserted_id})
        
        if nuevo_movimiento and '_id' in nuevo_movimiento:
            nuevo_movimiento['id'] = str(nuevo_movimiento['_id'])
            del nuevo_movimiento['_id']
        
        return [nuevo_movimiento]  # Retornar lista con un solo movimiento
        
    except Exception as e:
        raise e

# ==========================================
# Funciones adicionales para reportes
# ==========================================

async def get_valor_total_inventario(db: AsyncIOMotorDatabase):
    """
    Calcular valor total del inventario (si tienes precio_unitario)
    """
    collection = db["productos"]
    
    pipeline = [
        {"$group": {
            "_id": None,
            "valor_total": {"$sum": {"$multiply": ["$stock_actual", "$precio_unitario"]}}
        }}
    ]
    
    result = await collection.aggregate(pipeline).to_list(length=1)
    return result[0]["valor_total"] if result else 0.0

async def get_estadisticas_dashboard(db: AsyncIOMotorDatabase):
    """
    Obtener estadísticas para el dashboard
    """
    productos_col = db["productos"]
    movimientos_col = db["movimientos"]
    
    # Total de productos
    total_productos = await productos_col.count_documents({})
    
    # Productos bajo stock
    productos_bajo_stock = await productos_col.count_documents({
        "$expr": {"$lt": ["$stock_actual", "$stock_minimo"]}
    })
    
    # Últimos 10 movimientos
    ultimos_movimientos = await movimientos_col.find().sort("fecha_movimiento", -1).limit(10).to_list(length=10)
    
    # Movimientos de hoy
    hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    movimientos_hoy = await movimientos_col.count_documents({
        "fecha_movimiento": {"$gte": hoy_inicio}
    })
    
    # Convertir ObjectId a string para los movimientos
    for mov in ultimos_movimientos:
        if '_id' in mov:
            mov['id'] = str(mov['_id'])
            del mov['_id']
    
    return {
        "total_productos": total_productos,
        "productos_bajo_stock": productos_bajo_stock,
        "ultimos_movimientos": ultimos_movimientos,
        "movimientos_hoy": movimientos_hoy
    }

async def guardar_reserva(
    db: AsyncIOMotorDatabase,
    session_id: str,
    items: list,
    datos_adicionales: dict = None
) -> Dict[str, Any]:
    """
    Guardar o actualizar una reserva de salida pendiente
    """
    reservas_col = db["reservas"]
    ubicaciones_col = db["ubicaciones"]
    
    # Buscar reserva existente
    reserva_existente = await reservas_col.find_one({"session_id": session_id})
    
    # Obtener items existentes
    items_existentes = reserva_existente.get('items', []) if reserva_existente else []
    
    # Crear diccionario con items existentes (clave: producto_id|ubicacion)
    items_dict = {}
    for item in items_existentes:
        key = f"{item.get('producto_id')}|{item.get('ubicacion', 'SIN_UBICACION')}"
        items_dict[key] = item.copy()
    
    # Procesar nuevos items
    for item_nuevo in items:
        key = f"{item_nuevo.get('producto_id')}|{item_nuevo.get('ubicacion', 'SIN_UBICACION')}"
        cantidad_nueva = item_nuevo.get('cantidad', 0)
        
        if key in items_dict:
            # Actualizar cantidad existente
            cantidad_anterior = items_dict[key]['cantidad']
            nueva_cantidad = cantidad_anterior + cantidad_nueva
            items_dict[key]['cantidad'] = nueva_cantidad
            
            # ACTUALIZAR stock_reservado en ubicación (diferencia)
            diferencia = cantidad_nueva
            ubicacion_nombre = item_nuevo.get('ubicacion')
            if ubicacion_nombre:
                await ubicaciones_col.update_one(
                    {
                        "producto_codigo": item_nuevo.get('producto_id'),
                        "ubicacion": ubicacion_nombre
                    },
                    {"$inc": {"stock_reservado": diferencia}}
                )
                print(f"➕ Actualizando reserva en {ubicacion_nombre}: +{diferencia} (total ahora: {nueva_cantidad})")
        else:
            # Nuevo item
            items_dict[key] = {
                'producto_id': item_nuevo.get('producto_id'),
                'producto_nombre': item_nuevo.get('producto_nombre'),
                'producto_codigo': item_nuevo.get('producto_codigo'),
                'ubicacion': item_nuevo.get('ubicacion'),
                'cantidad': cantidad_nueva,
                'stock_actual': item_nuevo.get('stock_actual', 0),
                'stock_minimo': item_nuevo.get('stock_minimo', 5),
                'tipo': item_nuevo.get('tipo'),
                'nombre': item_nuevo.get('nombre'),
                'cantidad_kits': item_nuevo.get('cantidad_kits')
            }
            
            # RESERVAR stock en ubicación
            ubicacion_nombre = item_nuevo.get('ubicacion')
            if ubicacion_nombre:
                await ubicaciones_col.update_one(
                    {
                        "producto_codigo": item_nuevo.get('producto_id'),
                        "ubicacion": ubicacion_nombre
                    },
                    {"$inc": {"stock_reservado": cantidad_nueva}}
                )
                print(f"🔒 Nueva reserva en {ubicacion_nombre}: +{cantidad_nueva}")
    
    # Convertir diccionario a lista
    nuevos_items = list(items_dict.values())
    
    # Guardar o actualizar reserva
    if reserva_existente:
        await reservas_col.update_one(
            {"session_id": session_id},
            {"$set": {
                "items": nuevos_items,
                "datos_adicionales": datos_adicionales,
                "fecha_actualizacion": datetime.now()
            }}
        )
    else:
        reserva_dict = {
            "session_id": session_id,
            "items": nuevos_items,
            "tipo": "salida_pendiente",
            "datos_adicionales": datos_adicionales,
            "fecha_creacion": datetime.now(),
            "fecha_actualizacion": datetime.now()
        }
        await reservas_col.insert_one(reserva_dict)
    
    reserva = await reservas_col.find_one({"session_id": session_id})
    
    if reserva and '_id' in reserva:
        reserva['id'] = str(reserva['_id'])
        del reserva['_id']
    
    return reserva


async def obtener_reserva(
    db: AsyncIOMotorDatabase,
    session_id: str
) -> Optional[Dict[str, Any]]:
    """
    Obtener la reserva de una sesión
    """
    reservas_col = db["reservas"]
    reserva = await reservas_col.find_one({"session_id": session_id})
    
    if reserva and '_id' in reserva:
        reserva['id'] = str(reserva['_id'])
        del reserva['_id']
    
    return reserva

async def eliminar_reserva(
    db: AsyncIOMotorDatabase,
    session_id: str
) -> bool:
    """
    Eliminar reserva de una sesión (liberar stock de ubicaciones)
    """
    reservas_col = db["reservas"]
    ubicaciones_col = db["ubicaciones"]
    
    # Obtener la reserva antes de eliminarla
    reserva = await reservas_col.find_one({"session_id": session_id})
    if not reserva:
        print(f"❌ No se encontró reserva para session_id: {session_id}")
        return False
    
    print(f"🔍 Eliminando reserva: {reserva.get('_id')}")

    # Liberar stock reservado en cada ubicación
    items = reserva.get('items', [])
    for item in items:
        producto_codigo = item.get('producto_id')
        ubicacion_nombre = item.get('ubicacion')
        cantidad = item.get('cantidad', 0)
        
        print(f"   Liberando: {producto_codigo} en {ubicacion_nombre} - cantidad: {cantidad}")
        
        if ubicacion_nombre and cantidad > 0:
            resultado = await ubicaciones_col.update_one(
                {
                    "producto_codigo": producto_codigo,
                    "ubicacion": ubicacion_nombre
                },
                {"$inc": {"stock_reservado": -cantidad}}
            )
            print(f"🔓 Liberando {cantidad} unidades reservadas en {ubicacion_nombre} para {producto_codigo}")
            print(f"   Documento modificado: {resultado.modified_count}")
    
    # Eliminar la reserva
    result = await reservas_col.delete_one({"session_id": session_id})
    
    return result.deleted_count > 0


async def obtener_stock_con_reservas(
    db: AsyncIOMotorDatabase,
    producto_id: str,
    session_id_actual: str = None
) -> Dict[str, Any]:
    """Obtener stock actual considerando reservas de otros usuarios"""
    productos_col = db["productos"]
    reservas_col = db["reservas"]
    
    producto = await productos_col.find_one({"codigo": producto_id})
    if not producto:
        return {"error": "Producto no encontrado"}
    
    # Stock físico actual
    stock_fisico = producto.get("stock_actual", 0)
    
    # Calcular stock reservado por OTROS usuarios (excluyendo al actual)
    otras_reservas = await reservas_col.find({
        "session_id": {"$ne": session_id_actual} if session_id_actual else {},
        "items.producto_id": producto_id
    }).to_list(length=None)
    
    cantidad_reservada_otros = 0
    for reserva in otras_reservas:
        for item in reserva['items']:
            if item.get('producto_id') == producto_id:
                cantidad_reservada_otros += item.get('cantidad', 0)
    
    # Stock disponible = stock físico - reservas de otros
    stock_disponible = stock_fisico - cantidad_reservada_otros
    
    # Calcular reserva del usuario actual (solo para información)
    cantidad_reservada_actual = 0
    if session_id_actual:
        reserva_actual = await reservas_col.find_one({"session_id": session_id_actual})
        if reserva_actual:
            for item in reserva_actual['items']:
                if item.get('producto_id') == producto_id:
                    cantidad_reservada_actual += item.get('cantidad', 0)
    
    stock_disponible = stock_fisico - cantidad_reservada_otros - cantidad_reservada_actual
    
    print(f"📊 Cálculo stock para {producto_id}:")
    print(f"   Stock físico: {stock_fisico}")
    print(f"   Reservado por otros: {cantidad_reservada_otros}")
    print(f"   Reservado por actual: {cantidad_reservada_actual}")
    print(f"   Stock disponible: {stock_disponible}")
    
    return {
        "stock_fisico": stock_fisico,
        "stock_reservado_otros": cantidad_reservada_otros,
        "stock_reservado_actual": cantidad_reservada_actual,
        "stock_disponible": max(0, stock_disponible),  # No puede ser negativo
        "producto": {
            "codigo": producto.get("codigo"),
            "nombre": producto.get("nombre"),
            "stock_minimo": producto.get("stock_minimo", 0)
        }
    }
async def ajustar_reserva(
    db: AsyncIOMotorDatabase,
    session_id: str,
    ajustes: list,
    datos_adicionales: dict = None
) -> Dict[str, Any]:
    """
    Ajustar una reserva existente aplicando diferencias
    """
    reservas_col = db["reservas"]
    ubicaciones_col = db["ubicaciones"]
    
    reserva_existente = await reservas_col.find_one({"session_id": session_id})
    
    if not reserva_existente:
        # Si no existe reserva, crear una nueva solo con ajustes positivos
        items = [{
            'producto_id': a['producto_id'],
            'producto_nombre': a.get('producto_nombre', ''),
            'producto_codigo': a.get('producto_codigo', ''),
            'ubicacion': a.get('ubicacion', ''),
            'cantidad': a['diferencia'] if a['diferencia'] > 0 else 0,
            'stock_actual': 0,
            'stock_minimo': 5
        } for a in ajustes if a['diferencia'] > 0]
        
        if items:
            return await guardar_reserva(db, session_id, items, datos_adicionales)
        return reserva_existente
    
    items_actuales = reserva_existente.get('items', [])
    items_dict = {}
    
    # Cargar items actuales
    for item in items_actuales:
        key = f"{item.get('producto_id')}|{item.get('ubicacion', 'SIN_UBICACION')}"
        items_dict[key] = item.copy()
    
    # Aplicar ajustes
    for ajuste in ajustes:
        producto_id = ajuste['producto_id']
        ubicacion = ajuste.get('ubicacion', '')
        diferencia = ajuste['diferencia']
        key = f"{producto_id}|{ubicacion}"
        
        print(f"🔄 Procesando ajuste: {producto_id} en {ubicacion}, diferencia: {diferencia}")
        
        if key in items_dict:
            cantidad_anterior = items_dict[key]['cantidad']
            nueva_cantidad = cantidad_anterior + diferencia
            
            if nueva_cantidad > 0:
                items_dict[key]['cantidad'] = nueva_cantidad
                
                # ACTUALIZAR stock_reservado en ubicación
                if ubicacion and diferencia != 0:
                    resultado = await ubicaciones_col.update_one(
                        {
                            "producto_codigo": producto_id,
                            "ubicacion": ubicacion
                        },
                        {"$inc": {"stock_reservado": diferencia}}
                    )
                    print(f"   📍 Actualizando {ubicacion}: {diferencia:+d} (matched: {resultado.matched_count}, modified: {resultado.modified_count})")
            else:
                # Eliminar item si cantidad llega a 0 o menos
                del items_dict[key]
                
                # LIBERAR todo el stock_reservado de esta ubicación
                if ubicacion and cantidad_anterior > 0:
                    resultado = await ubicaciones_col.update_one(
                        {
                            "producto_codigo": producto_id,
                            "ubicacion": ubicacion
                        },
                        {"$inc": {"stock_reservado": -cantidad_anterior}}
                    )
                    print(f"   🔓 Liberando {cantidad_anterior} unidades de {ubicacion} (matched: {resultado.matched_count}, modified: {resultado.modified_count})")
        else:
            if diferencia > 0:
                # Nuevo producto/ubicación
                items_dict[key] = {
                    'producto_id': producto_id,
                    'producto_nombre': ajuste.get('producto_nombre', ''),
                    'producto_codigo': ajuste.get('producto_codigo', ''),
                    'ubicacion': ubicacion,
                    'cantidad': diferencia,
                    'stock_actual': 0,
                    'stock_minimo': 5
                }
                
                # RESERVAR stock
                if ubicacion:
                    resultado = await ubicaciones_col.update_one(
                        {
                            "producto_codigo": producto_id,
                            "ubicacion": ubicacion
                        },
                        {"$inc": {"stock_reservado": diferencia}}
                    )
                    print(f"   🔒 Nueva reserva en {ubicacion}: +{diferencia} (matched: {resultado.matched_count})")
            elif diferencia < 0:
                # Intentar liberar stock de un item que no existe (error)
                print(f"   ⚠️ Intento de liberar {abs(diferencia)} unidades de {producto_id} en {ubicacion} pero no existe en la reserva")
    
    nuevos_items = list(items_dict.values())
    
    # Actualizar reserva
    if nuevos_items:
        await reservas_col.update_one(
            {"session_id": session_id},
            {"$set": {
                "items": nuevos_items,
                "datos_adicionales": datos_adicionales,
                "fecha_actualizacion": datetime.now()
            }}
        )
    else:
        # Si no quedan items, eliminar la reserva
        await reservas_col.delete_one({"session_id": session_id})
        print(f"🗑️ Reserva eliminada porque no quedan items")
    
    reserva = await reservas_col.find_one({"session_id": session_id})
    
    if reserva and '_id' in reserva:
        reserva['id'] = str(reserva['_id'])
        del reserva['_id']
    
    return reserva

async def get_movimientos_para_exportar(
    db: AsyncIOMotorDatabase,
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    tipo: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtener movimientos para exportar a Excel con filtros opcionales
    """
    movimientos_col = db["movimientos"]
    productos_col = db["productos"]
    
    # Construir filtro
    filtro = {}
    
    if fecha_inicio or fecha_fin:
        filtro["fecha_movimiento"] = {}
        if fecha_inicio:
            filtro["fecha_movimiento"]["$gte"] = fecha_inicio
        if fecha_fin:
            filtro["fecha_movimiento"]["$lte"] = fecha_fin
    
    if tipo and tipo in ["entrada", "salida"]:
        filtro["tipo"] = tipo
    
    # Obtener movimientos
    cursor = movimientos_col.find(filtro).sort("fecha_movimiento", -1)
    movimientos = await cursor.to_list(length=None)
    
    # Enriquecer movimientos con información del producto
    for mov in movimientos:
        # Obtener producto si no tiene la información
        if 'producto_nombre' not in mov or not mov.get('producto_nombre'):
            producto = await productos_col.find_one({"codigo": mov.get('producto_id')})
            if producto:
                mov['producto_nombre'] = producto.get('nombre', 'N/A')
                mov['producto_codigo'] = producto.get('codigo', mov.get('producto_id', 'N/A'))
            else:
                mov['producto_nombre'] = 'Producto no encontrado'
                mov['producto_codigo'] = mov.get('producto_id', 'N/A')
        
        # Si es un kit, obtener los productos del kit
        if mov.get('es_kit') and mov.get('productos_kit'):
            # Para kits, crear una representación en texto de los productos
            productos_texto = []
            for p in mov.get('productos_kit', []):
                productos_texto.append(f"{p.get('producto_nombre', 'N/A')}: {p.get('cantidad', 0)}")
            mov['productos_kit_texto'] = '; '.join(productos_texto)
            mov['cantidad_productos_kit'] = len(mov.get('productos_kit', []))
        
        # Convertir ObjectId a string
        if '_id' in mov:
            mov['id'] = str(mov['_id'])
            del mov['_id']
    
    return movimientos

async def get_producto_con_ubicaciones(db: AsyncIOMotorDatabase, codigo: str):
    """Obtener producto con todas sus ubicaciones"""
    try:
        # Buscar producto por código
        producto = await get_producto_por_codigo(db, codigo)
        if not producto:
            return None
        
        # Buscar ubicaciones del producto
        ubicaciones_col = db["ubicaciones"]
        ubicaciones = await ubicaciones_col.find({"producto_codigo": codigo}).to_list(length=None)
        
        # Procesar ubicaciones
        stock_por_ubicacion = []
        for ub in ubicaciones:
            stock_fisico = ub.get("stock_fisico", 0)
            stock_reservado = ub.get("stock_reservado", 0)
            stock_disponible = stock_fisico - stock_reservado
            
            stock_por_ubicacion.append({
                "id": str(ub["_id"]),
                "ubicacion": ub.get("ubicacion"),
                "stock_fisico": stock_fisico,
                "stock_reservado": stock_reservado,
                "stock_disponible": max(0, stock_disponible)
            })
        
        return {
            "producto": producto,
            "ubicaciones": stock_por_ubicacion,
            "stock_por_ubicacion": stock_por_ubicacion,
            "total_ubicaciones": len(stock_por_ubicacion)
        }
    except Exception as e:
        print(f"❌ Error en get_producto_con_ubicaciones: {e}")
        import traceback
        traceback.print_exc()
        return None

async def crear_ubicacion(db: AsyncIOMotorDatabase, producto_codigo: str, ubicacion: str, cantidad: int = 0, usuario: str = "admin"):
    """Crear una nueva ubicación para un producto"""
    ubicaciones_col = db["ubicaciones"]
    productos_col = db["productos"]
    
    # Obtener producto
    producto = await productos_col.find_one({"codigo": producto_codigo})
    if not producto:
        raise ValueError(f"Producto {producto_codigo} no encontrado")
    
    # Verificar si la ubicación ya existe
    existente = await ubicaciones_col.find_one({
        "producto_codigo": producto_codigo,
        "ubicacion": ubicacion
    })
    
    if existente:
        raise ValueError(f"La ubicación '{ubicacion}' ya existe para este producto")
    
    # Calcular stock actual en todas las ubicaciones
    todas_ubicaciones = await ubicaciones_col.find({"producto_codigo": producto_codigo}).to_list(length=None)
    stock_actual_en_ubicaciones = sum(ub.get("stock_fisico", 0) for ub in todas_ubicaciones)
    
    # Stock disponible para asignar = stock_total - stock_asignado
    stock_total = producto.get("stock_actual", 0)
    stock_disponible = stock_total - stock_actual_en_ubicaciones
    
    # Validar que no exceda el stock disponible
    if cantidad > stock_disponible:
        raise ValueError(f"No hay suficiente stock disponible. Stock total: {stock_total}, ya asignado: {stock_actual_en_ubicaciones}, disponible: {stock_disponible}")
    
    # Crear nueva ubicación
    nueva_ubicacion = {
        "producto_codigo": producto_codigo,
        "ubicacion": ubicacion,
        "stock_fisico": cantidad,
        "stock_reservado": 0,
        "fecha_creacion": datetime.now()
    }
    
    result = await ubicaciones_col.insert_one(nueva_ubicacion)
    
    # ✅ REGISTRAR MOVIMIENTO EN EL HISTORIAL
    notas = f"Se creó la ubicación '{ubicacion}' con {cantidad} unidades"
    await crear_movimiento_ubicacion(
        db, producto_codigo, producto["nombre"],
        "creacion_ubicacion", cantidad, ubicacion, notas, usuario
    )

    nueva_ubicacion["id"] = str(result.inserted_id)
    # No devolver el _id directamente (FastAPI no puede serializarlo)
    if "_id" in nueva_ubicacion:
        del nueva_ubicacion["_id"]
    
    return nueva_ubicacion

async def actualizar_ubicacion(db: AsyncIOMotorDatabase, producto_codigo: str, ubicacion: str, nueva_cantidad: int):
    """Actualizar stock de una ubicación (redistribuyendo stock total)"""
    ubicaciones_col = db["ubicaciones"]
    productos_col = db["productos"]
    
    # Obtener producto
    producto = await productos_col.find_one({"codigo": producto_codigo})
    if not producto:
        raise ValueError(f"Producto {producto_codigo} no encontrado")
    
    # Obtener ubicación actual
    ubicacion_actual = await ubicaciones_col.find_one({
        "producto_codigo": producto_codigo,
        "ubicacion": ubicacion
    })
    
    if not ubicacion_actual:
        raise ValueError(f"Ubicación '{ubicacion}' no encontrada")
    
    cantidad_anterior = ubicacion_actual.get("stock_fisico", 0)
    
    # Calcular stock total actual en todas las ubicaciones
    todas_ubicaciones = await ubicaciones_col.find({"producto_codigo": producto_codigo}).to_list(length=None)
    stock_actual_en_ubicaciones = sum(ub.get("stock_fisico", 0) for ub in todas_ubicaciones)
    
    # Stock total del producto
    stock_total = producto.get("stock_actual", 0)
    
    # Nueva suma después del cambio
    nueva_suma = stock_actual_en_ubicaciones - cantidad_anterior + nueva_cantidad
    
    # Validar que no exceda el stock total
    if nueva_suma > stock_total:
        raise ValueError(f"No hay suficiente stock total. Stock total: {stock_total}, suma de ubicaciones actual: {stock_actual_en_ubicaciones}, nueva suma: {nueva_suma}")
    
    # Actualizar ubicación
    await ubicaciones_col.update_one(
        {"_id": ubicacion_actual["_id"]},
        {"$set": {"stock_fisico": nueva_cantidad}}
    )
    
    return {"success": True, "diferencia": nueva_cantidad - cantidad_anterior}

async def eliminar_ubicacion(db: AsyncIOMotorDatabase, producto_codigo: str, ubicacion: str):
    """Eliminar una ubicación (el stock vuelve a estar disponible sin ubicación)"""
    ubicaciones_col = db["ubicaciones"]
    
    ubicacion_actual = await ubicaciones_col.find_one({
        "producto_codigo": producto_codigo,
        "ubicacion": ubicacion
    })
    
    if not ubicacion_actual:
        raise ValueError(f"Ubicación '{ubicacion}' no encontrada")
    
    # Eliminar ubicación
    await ubicaciones_col.delete_one({"_id": ubicacion_actual["_id"]})

    return {"success": True}

async def transferir_stock_entre_ubicaciones(
    db: AsyncIOMotorDatabase,
    producto_codigo: str,
    origen: str,
    destino: str,
    cantidad: int,
    usuario: str = "admin"
):
    """Transferir stock entre ubicaciones del mismo producto"""
    ubicaciones_col = db["ubicaciones"]
    
    # Obtener ubicación origen
    ubicacion_origen = await ubicaciones_col.find_one({
        "producto_codigo": producto_codigo,
        "ubicacion": origen
    })
    
    if not ubicacion_origen:
        raise ValueError(f"Ubicación origen '{origen}' no encontrada")
    
    if ubicacion_origen.get("stock_fisico", 0) < cantidad:
        raise ValueError(f"Stock insuficiente en origen. Disponible: {ubicacion_origen.get('stock_fisico', 0)}")
    
    # Obtener o crear ubicación destino
    ubicacion_destino = await ubicaciones_col.find_one({
        "producto_codigo": producto_codigo,
        "ubicacion": destino
    })
    
    # Realizar transferencia
    await ubicaciones_col.update_one(
        {"_id": ubicacion_origen["_id"]},
        {"$inc": {"stock_fisico": -cantidad}}
    )
    
    if ubicacion_destino:
        await ubicaciones_col.update_one(
            {"_id": ubicacion_destino["_id"]},
            {"$inc": {"stock_fisico": cantidad}}
        )
    else:
        await ubicaciones_col.insert_one({
            "producto_codigo": producto_codigo,
            "ubicacion": destino,
            "stock_fisico": cantidad,
            "stock_reservado": 0,
            "fecha_creacion": datetime.now()
        })
    
    producto = await db["productos"].find_one({"codigo": producto_codigo})
    if producto:
        notas = f"Transferencia de {cantidad} unidades de '{origen}' a '{destino}'"
        movimientos_col = db["movimientos"]
        
        movimiento_dict = {
            "producto_id": producto_codigo,
            "producto_nombre": producto["nombre"],
            "tipo": "transferencia_ubicacion",
            "cantidad": cantidad,
            "motivo": "Transferencia entre ubicaciones",
            "notas": notas,
            "ubicacion_origen": origen,
            "ubicacion_destino": destino,
            "usuario": usuario,
            "fecha_movimiento": datetime.utcnow(),
            "pdf_firmado": None,
            "pdf_nombre": None
        }
        
        result = await movimientos_col.insert_one(movimiento_dict)
    
    return {"success": True}

async def obtener_stock_con_reservas_por_ubicacion(
    db: AsyncIOMotorDatabase,
    producto_codigo: str,
    ubicacion: str,
    session_id_actual: str = None
) -> Dict[str, Any]:
    """Obtener stock disponible para una ubicación específica"""
    ubicaciones_col = db["ubicaciones"]
    reservas_col = db["reservas"]
    
    ubicacion_doc = await ubicaciones_col.find_one({
        "producto_codigo": producto_codigo,
        "ubicacion": ubicacion
    })
    
    if not ubicacion_doc:
        return {
            "stock_fisico": 0,
            "stock_reservado_otros": 0,
            "stock_reservado_actual": 0,
            "stock_disponible": 0
        }
    
    stock_fisico = ubicacion_doc.get("stock_fisico", 0)
    
    # Calcular reservas de otros en esta ubicación
    otras_reservas = await reservas_col.find({
        "session_id": {"$ne": session_id_actual} if session_id_actual else {},
        "items.producto_id": producto_codigo,
        "items.ubicacion": ubicacion
    }).to_list(length=None)
    
    cantidad_reservada_otros = 0
    for reserva in otras_reservas:
        for item in reserva.get('items', []):
            if item.get('producto_id') == producto_codigo and item.get('ubicacion') == ubicacion:
                cantidad_reservada_otros += item.get('cantidad', 0)
    
    # Reserva del usuario actual
    cantidad_reservada_actual = 0
    if session_id_actual:
        reserva_actual = await reservas_col.find_one({"session_id": session_id_actual})
        if reserva_actual:
            for item in reserva_actual.get('items', []):
                if item.get('producto_id') == producto_codigo and item.get('ubicacion') == ubicacion:
                    cantidad_reservada_actual += item.get('cantidad', 0)
    
    stock_disponible = stock_fisico - cantidad_reservada_otros - cantidad_reservada_actual
    
    return {
        "stock_fisico": stock_fisico,
        "stock_reservado_otros": cantidad_reservada_otros,
        "stock_reservado_actual": cantidad_reservada_actual,
        "stock_disponible": max(0, stock_disponible),
        "ubicacion": ubicacion
    }
async def crear_movimiento_ubicacion(
    db: AsyncIOMotorDatabase,
    producto_codigo: str,
    producto_nombre: str,
    tipo: str,
    cantidad: int,
    ubicacion: str,
    notas: str,
    usuario: str = "admin"
):
    """Crear un movimiento en el historial (para creación/transferencia de ubicaciones)"""
    movimientos_col = db["movimientos"]
    
    movimiento_dict = {
        "producto_id": producto_codigo,
        "producto_nombre": producto_nombre,
        "tipo": tipo,
        "cantidad": cantidad,
        "motivo": "Gestión de Ubicaciones",
        "notas": notas,
        "ubicacion": ubicacion,
        "usuario": usuario,
        "fecha_movimiento": datetime.utcnow(),
        "pdf_firmado": None,
        "pdf_nombre": None,
        "remision": getattr(movimiento, 'remision', None),      # ← MODIFICAR
        "caso": getattr(movimiento, 'caso', None),              # ← MODIFICAR
        "numero_cajas": getattr(movimiento, 'numero_cajas', None)  # ← MODIFICAR
    }
    
    result = await movimientos_col.insert_one(movimiento_dict)
    nuevo_movimiento = await movimientos_col.find_one({"_id": result.inserted_id})
    
    if nuevo_movimiento and '_id' in nuevo_movimiento:
        nuevo_movimiento['id'] = str(nuevo_movimiento['_id'])
        del nuevo_movimiento['_id']
    
    return nuevo_movimiento

# ==========================================
# Funciones para Número de Remisión
# ==========================================

async def generar_numero_remision(db: AsyncIOMotorDatabase) -> str:
    """Generar el siguiente número de remisión (RM-001, RM-002, ...)"""
    contador_col = db["contadores"]
    
    # Buscar contador de remisión
    contador = await contador_col.find_one({"nombre": "remision"})
    
    if not contador:
        # Crear contador si no existe
        nuevo_numero = 1
        await contador_col.insert_one({
            "nombre": "remision",
            "ultimo_numero": nuevo_numero
        })
        print(f"📊 Contador creado: ultimo_numero={nuevo_numero}")
    else:
        # ✅ Obtener el número actual y incrementarlo
        ultimo = contador.get("ultimo_numero", 0)
        nuevo_numero = ultimo + 1
        
        # ✅ Actualizar el contador
        resultado = await contador_col.update_one(
            {"nombre": "remision"},
            {"$set": {"ultimo_numero": nuevo_numero}}
        )
        print(f"📊 Contador actualizado: {ultimo} → {nuevo_numero} (modified: {resultado.modified_count})")
    
    return f"RM-{nuevo_numero:03d}"

# ==========================================
# Funciones para Mercados Predefinidos
# ==========================================

async def get_mercados_predefinidos(db: AsyncIOMotorDatabase, activo_only: bool = True) -> List[Dict[str, Any]]:
    """Obtener todos los mercados predefinidos"""
    collection = db["mercados_predefinidos"]
    query = {"activo": True} if activo_only else {}
    mercados = await collection.find(query).to_list(length=None)
    
    for m in mercados:
        if '_id' in m:
            m['id'] = str(m['_id'])
            del m['_id']
    
    return mercados


async def get_mercado_predefinido(db: AsyncIOMotorDatabase, nombre: str) -> Optional[Dict[str, Any]]:
    """Obtener un mercado predefinido por nombre"""
    collection = db["mercados_predefinidos"]
    mercado = await collection.find_one({"nombre": nombre})
    
    if mercado and '_id' in mercado:
        mercado['id'] = str(mercado['_id'])
        del mercado['_id']
    
    return mercado


async def crear_mercado_predefinido(db: AsyncIOMotorDatabase, mercado_data: dict, usuario: str = "admin") -> Dict[str, Any]:
    """Crear un nuevo mercado predefinido"""
    collection = db["mercados_predefinidos"]
    
    mercado_dict = {
        "nombre": mercado_data["nombre"],
        "descripcion": mercado_data.get("descripcion"),
        "productos": mercado_data["productos"],
        "activo": mercado_data.get("activo", True),
        "created_at": datetime.now(),
        "updated_at": None,
        "created_by": usuario
    }
    
    result = await collection.insert_one(mercado_dict)
    nuevo_mercado = await collection.find_one({"_id": result.inserted_id})
    
    if nuevo_mercado and '_id' in nuevo_mercado:
        nuevo_mercado['id'] = str(nuevo_mercado['_id'])
        del nuevo_mercado['_id']
    
    return nuevo_mercado


async def actualizar_mercado_predefinido(db: AsyncIOMotorDatabase, nombre: str, mercado_data: dict) -> Optional[Dict[str, Any]]:
    """Actualizar un mercado predefinido"""
    collection = db["mercados_predefinidos"]
    
    update_data = {
        "descripcion": mercado_data.get("descripcion"),
        "productos": mercado_data.get("productos"),
        "activo": mercado_data.get("activo", True),
        "updated_at": datetime.now()
    }
    
    await collection.update_one(
        {"nombre": nombre},
        {"$set": update_data}
    )
    
    mercado = await collection.find_one({"nombre": nombre})
    
    if mercado and '_id' in mercado:
        mercado['id'] = str(mercado['_id'])
        del mercado['_id']
    
    return mercado


async def init_mercados_predefinidos(db: AsyncIOMotorDatabase):
    """Inicializar mercados predefinidos (Básico y Grande)"""
    collection = db["mercados_predefinidos"]
    
    # Verificar si ya existen
    existentes = await collection.count_documents({})
    if existentes > 0:
        return {"message": "Los mercados ya existen", "count": existentes}
    
    mercados = [
        {
            "nombre": "MERCADO_BASICO",
            "descripcion": "Mercado básico para familias vulnerables",
            "productos": [
                {"producto_id": "ALI1", "cantidad": 2, "producto_nombre": "ACEITE 1000 ML"},
                {"producto_id": "ALI6", "cantidad": 5, "producto_nombre": "ARROZ GOLONDRINA 500 GR"},
                {"producto_id": "ALI10", "cantidad": 2, "producto_nombre": "AZUCAR 1000 GR"},
                {"producto_id": "ALI14", "cantidad": 2, "producto_nombre": "HARINA DE TRIGO 500 GR"},
                {"producto_id": "ALI22", "cantidad": 2, "producto_nombre": "SARDINAS 425 GR"}
            ],
            "activo": True
        },
        {
            "nombre": "MERCADO_GRANDE",
            "descripcion": "Mercado grande para familias numerosas",
            "productos": [
                {"producto_id": "ALI1", "cantidad": 4, "producto_nombre": "ACEITE 1000 ML"},
                {"producto_id": "ALI6", "cantidad": 10, "producto_nombre": "ARROZ GOLONDRINA 500 GR"},
                {"producto_id": "ALI10", "cantidad": 4, "producto_nombre": "AZUCAR 1000 GR"},
                {"producto_id": "ALI14", "cantidad": 4, "producto_nombre": "HARINA DE TRIGO 500 GR"},
                {"producto_id": "ALI22", "cantidad": 4, "producto_nombre": "SARDINAS 425 GR"},
                {"producto_id": "ALI2", "cantidad": 2, "producto_nombre": "ACEITE 2000 CC"},
                {"producto_id": "ALI11", "cantidad": 2, "producto_nombre": "CHOCOLATE TRADICIONAL 500 GR"},
                {"producto_id": "ALI16", "cantidad": 1, "producto_nombre": "LECHE EN POLVO 380 GR"}
            ],
            "activo": True
        }
    ]
    
    for mercado in mercados:
        mercado["created_at"] = datetime.now()
        mercado["created_by"] = "system"
        await collection.insert_one(mercado)
    
    return {"message": "Mercados inicializados", "creados": len(mercados)}