# app/routers/movimientos.py
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form, Request
from typing import List, Optional
from datetime import datetime
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import pandas as pd
import io
import json
import os
import shutil

from .. import crud
from ..models import MovimientoCreate, SalidaMultipleCreate, EntradaMultipleCreate
from ..database import get_database
from ..utils.pdf_generator import PDFGenerator
from ..core.dependencies import require_authenticated, require_super_admin
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..core.security import decode_token

security = HTTPBearer()

router = APIRouter(prefix="/movimientos", tags=["movimientos"])

PDF_UPLOAD_DIR = "app/static/pdfs/salidas"
os.makedirs(PDF_UPLOAD_DIR, exist_ok=True)

@router.get("/")
async def leer_movimientos(
    skip: int = 0,
    limit: int = 100,
    producto_id: str = None,
    tipo: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    motivo: str = None,
    remision: str = None,  # ← AGREGAR
    caso: str = None, 
    origen_destino: str = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Obtener lista de movimientos (incluye búsqueda dentro de kits)"""
    try:
        movimientos_col = db["movimientos"]
        users_col = db["users"]
        
        filtro = {}
        
        # Filtro por tipo
        if tipo and tipo in ["entrada", "salida"]:
            filtro["tipo"] = tipo
        
        # Filtro por producto (busca también dentro de kits)
        if producto_id:
            filtro = {
                "$or": [
                    {"producto_id": producto_id},  # Movimientos normales
                    {"productos_kit.producto_id": producto_id},  # Movimientos de kit que contienen este producto
                    {"productos_multiple.producto_id": producto_id}  # Movimientos múltiples que contienen este producto
                ]
            }
            # Mantener filtro de tipo si existe
            if tipo:
                filtro["tipo"] = tipo
        
        # Filtro por motivo
        if motivo:
            filtro["motivo"] = motivo
        if remision:
            filtro["remision"] = remision
      
         # Filtro por caso
        if caso:
            filtro["caso"] = caso
        # ✅ NUEVO FILTRO: Proveedor/Destino
        if origen_destino:
            filtro["$or"] = [
                {"origen_nombre": {"$regex": origen_destino, "$options": "i"}},
                {"cliente_destino": {"$regex": origen_destino, "$options": "i"}}
            ]

        # Filtro por fechas
        if fecha_desde or fecha_hasta:
            filtro["fecha_movimiento"] = {}
            if fecha_desde:
                filtro["fecha_movimiento"]["$gte"] = datetime.fromisoformat(fecha_desde)
            if fecha_hasta:
                filtro["fecha_movimiento"]["$lte"] = datetime.fromisoformat(fecha_hasta)
        
        print(f"🔍 Filtro aplicado: {filtro}")
        
        cursor = movimientos_col.find(filtro).sort("fecha_movimiento", -1).skip(skip).limit(limit)
        movimientos = await cursor.to_list(length=limit)

        for mov in movimientos:
            if '_id' in mov:
                mov['id'] = str(mov['_id'])
                del mov['_id']

            usuario_id = mov.get('usuario_id')
            if usuario_id:
                try:
                    user = await users_col.find_one({"_id": ObjectId(usuario_id)})
                    if user:
                        mov['usuario'] = user.get('email', mov.get('usuario', 'Desconocido'))
                    else:
                        mov['usuario'] = mov.get('usuario', 'admin')
                except:
                    mov['usuario'] = mov.get('usuario', 'admin')
            else:
                mov['usuario'] = mov.get('usuario', 'admin')
                
        # ✅ AHORA sí puedes hacer print de movimientos
        print(f"🔍 Total movimientos en BD: {await movimientos_col.count_documents({})}")
        print(f"🔍 Movimientos devueltos: {len(movimientos)}")
        
        
        return movimientos
    except Exception as e:
        print(f"❌ Error en leer_movimientos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/producto/{producto_id}")
async def leer_movimientos_producto(
    producto_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Obtener movimientos de un producto específico"""
    try:
        movimientos = await crud.get_movimientos_por_producto(db, producto_id=producto_id)
        return movimientos
    except Exception as e:
        print(f"❌ Error en leer_movimientos_producto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def crear_movimiento(
    movimiento: MovimientoCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_authenticated)
):
    """Crear un nuevo movimiento (entrada o salida)"""
    try:
       # ✅ MODIFICAR: Asignar email real del usuario
        movimiento.usuario = current_user.get("email", "admin")
        movimiento.usuario_id = current_user.get("id")

        print(f"🔵 Recibido movimiento: {movimiento}")
        nuevo_mov = await crud.crear_movimiento(db=db, movimiento=movimiento)
        print(f"✅ Movimiento creado: {nuevo_mov}")
        return nuevo_mov
    except ValueError as e:
        print(f"❌ Error de validación: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error inesperado en crear_movimiento: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/entrada-rapida")
async def entrada_rapida(
    producto_id: str,
    cantidad: int,
    motivo: str = "Entrada rápida",
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_authenticated)
):
    """Registrar una entrada rápida de productos"""
    movimiento = MovimientoCreate(
        producto_id=producto_id,
        tipo="entrada",
        cantidad=cantidad,
        motivo=motivo,
        usuario=current_user.get("email", "admin"), 
        usuario_id=current_user.get("id")
    )
    
    try:
        resultado = await crud.crear_movimiento(db=db, movimiento=movimiento)
        producto = await crud.get_producto_por_codigo(db, producto_id)
        return {
            "message": "Entrada registrada exitosamente",
            "movimiento_id": resultado['id'] if 'id' in resultado else str(resultado.get('_id', '')),
            "stock_actual": producto['stock_actual'] if producto else 0
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/salida-rapida")
async def salida_rapida(
    producto_id: str,
    cantidad: int,
    motivo: str = "Salida rápida",
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_authenticated)
):
    """Registrar una salida rápida de productos"""
    movimiento = MovimientoCreate(
        producto_id=producto_id,
        tipo="salida",
        cantidad=cantidad,
        motivo=motivo,
        usuario=current_user.get("email", "admin"),  # ← MODIFICAR
        usuario_id=current_user.get("id")
    )
    
    try:
        resultado = await crud.crear_movimiento(db=db, movimiento=movimiento)
        producto = await crud.get_producto_por_codigo(db, producto_id)
        return {
            "message": "Salida registrada exitosamente",
            "movimiento_id": resultado['id'] if 'id' in resultado else str(resultado.get('_id', '')),
            "stock_actual": producto['stock_actual'] if producto else 0
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/salida-multiple")
async def crear_salida_multiple(
    salida: SalidaMultipleCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_authenticated)
):
    """Crear una salida con múltiples productos"""
    try:
        salida.usuario = current_user.get("email", "admin")
        salida.usuario_id = current_user.get("id")

        movimientos = await crud.crear_salida_multiple(
            db=db,
            productos=salida.productos,
            destino=salida.destino,
            razon=salida.razon,
            observaciones=salida.observaciones,
            usuario=salida.usuario,
            usuario_id=salida.usuario_id
        )
        return movimientos
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/entrada-multiple")
async def crear_entrada_multiple(
    entrada: EntradaMultipleCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_authenticated)
):
    """Crear una entrada con múltiples productos"""
    try:
        entrada.usuario = current_user.get("email", "admin")
        entrada.usuario_id = current_user.get("id")

        print("=" * 60)
        print("🔵 ENTRADA MÚLTIPLE RECIBIDA")
        print(f"📦 Datos recibidos: {entrada}")
        print(f"📦 Tipo de entrada: {type(entrada)}")
        print(f"📦 Productos: {entrada.productos}")
        print(f"📦 Tipo origen: {entrada.tipo_origen}")
        print(f"📦 Origen nombre: {entrada.origen_nombre}")
        print("=" * 60)
        
        # Validaciones explícitas
        if not entrada.origen_nombre or entrada.origen_nombre.strip() == "":
            raise ValueError("El campo 'origen_nombre' es requerido")
        
        if not entrada.productos or len(entrada.productos) == 0:
            raise ValueError("Debe haber al menos un producto")
        
        for i, prod in enumerate(entrada.productos):
            if 'producto_id' not in prod:
                raise ValueError(f"Producto {i}: falta el campo 'producto_id'")
            if 'cantidad' not in prod:
                raise ValueError(f"Producto {i}: falta el campo 'cantidad'")
            if prod['cantidad'] <= 0:
                raise ValueError(f"Producto {i}: la cantidad debe ser mayor a 0")
        
        movimientos = await crud.crear_entrada_multiple(
            db=db,
            productos=entrada.productos,
            tipo_origen=entrada.tipo_origen,
            origen_nombre=entrada.origen_nombre,
            ubicacion=entrada.ubicacion,
            observaciones=entrada.observaciones,
            usuario=entrada.usuario,
            usuario_id=entrada.usuario_id
        )
        return movimientos
        
    except ValueError as e:
        print(f"❌ Error de validación: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/exportar/excel")
async def exportar_movimientos_excel(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    tipo: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Exportar movimientos a Excel"""
    try:
        print(f"=== INICIANDO EXPORTACIÓN EXCEL ===")
        
        # Convertir fechas
        fecha_inicio_dt = None
        fecha_fin_dt = None
        
        if fecha_inicio:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        if fecha_fin:
            fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        
        movimientos = await crud.get_movimientos_para_exportar(
            db, fecha_inicio_dt, fecha_fin_dt, tipo
        )
        
        print(f"Total movimientos encontrados: {len(movimientos)}")
        
        if not movimientos:
            df = pd.DataFrame({"Mensaje": ["No hay movimientos para exportar"]})
        else:
            data = []
            for mov in movimientos:
                # Calcular stock anterior
                stock_actual = mov.get('stock_actual', 0)
                cantidad = mov['cantidad']
                if mov['tipo'] == "salida":
                    stock_anterior = stock_actual + cantidad
                else:
                    stock_anterior = stock_actual - cantidad
                
                origen_destino = mov.get('origen_nombre') or mov.get('cliente_destino') or "-"
                
                data.append({
                    "ID": str(mov.get('_id', '')),
                    "Fecha": mov['fecha_movimiento'].strftime("%Y-%m-%d %H:%M:%S"),
                    "Tipo": "ENTRADA" if mov['tipo'] == "entrada" else "SALIDA",
                    "Producto ID": mov['producto_id'],
                    "Código Producto": mov.get('producto_codigo', 'N/A'),
                    "Nombre Producto": mov.get('producto_nombre', 'N/A'),
                    "Cantidad": mov['cantidad'],
                    "Motivo": mov.get('motivo', '-'),
                    "Proveedor/Cliente": origen_destino,
                    "Ubicación": mov.get('ubicacion', '-'),
                    "Tipo Origen": mov.get('tipo_origen', '-'),
                    "Notas": mov.get('notas', '-'),
                    "Usuario": mov.get('usuario', 'admin'),
                    "Stock Anterior": stock_anterior,
                    "Stock Actual": stock_actual,
                    "Diferencia": f"+{mov['cantidad']}" if mov['tipo'] == "entrada" else f"-{mov['cantidad']}"
                })
            
            df = pd.DataFrame(data)
        
        # Crear Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Movimientos', index=False)
            
            # Ajustar ancho de columnas
            worksheet = writer.sheets['Movimientos']
            for column in df.columns:
                max_length = max(len(str(column)), df[column].astype(str).map(len).max() if len(df) > 0 else 0)
                adjusted_width = min(max_length + 2, 50)
                col_letter = chr(65 + df.columns.get_loc(column))
                worksheet.column_dimensions[col_letter].width = adjusted_width
        
        output.seek(0)
        
        fecha_descarga = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"movimientos_inventario_{fecha_descarga}.xlsx"
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Error al generar archivo Excel: {str(e)}")

@router.post("/generar-pdf-salida")
async def generar_pdf_salida_endpoint(
    salida_data: dict,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Generar PDF de comprobante de salida"""
    try:
        productos = salida_data.get('productos', [])
        destino = salida_data.get('destino', 'No especificado')
        razon = salida_data.get('razon', 'Salida de inventario')
        observaciones = salida_data.get('observaciones', '')
        usuario = salida_data.get('usuario', 'admin')
        
        # Preparar información de productos
        productos_info = []
        for item in productos:
            producto_id = item.get('producto_id')
            cantidad = item.get('cantidad')
            
            producto = await crud.get_producto_por_codigo(db, producto_id)
            if producto:
                productos_info.append({
                    'producto_nombre': producto['nombre'],
                    'producto_codigo': producto['codigo'],
                    'cantidad': cantidad
                })
        
        datos_salida = {
            'destino': destino,
            'razon': razon,
            'observaciones': observaciones,
            'usuario': usuario,
            'fecha': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        
        pdf_generator = PDFGenerator()
        pdf_bytes = pdf_generator.generar_comprobante_salida(datos_salida, productos_info)
        
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_limpio = "".join([c for c in destino if c.isalnum() or c in [' ', '_', '-']])[:30].replace(' ', '_')
        filename = f"salida_{nombre_limpio}_{fecha_str}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")

@router.post("/{movimiento_id}/subir-pdf")
async def subir_pdf_salida(
    movimiento_id: str,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Subir PDF firmado para una salida específica"""
    try:
        # Buscar movimiento
        movimientos_col = db["movimientos"]
        movimiento = await movimientos_col.find_one({"_id": ObjectId(movimiento_id)})
        
        if not movimiento or movimiento.get('tipo') != "salida":
            raise HTTPException(status_code=404, detail="Salida no encontrada")
        
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
        
        # Guardar archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino_limpio = "".join([c for c in (movimiento.get('cliente_destino', 'salida')) if c.isalnum() or c == ' '])[:20].replace(' ', '_')
        
        filename = f"salida_{movimiento_id}_{destino_limpio}_{timestamp}.pdf"
        file_path = os.path.join(PDF_UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Actualizar movimiento
        await movimientos_col.update_one(
            {"_id": ObjectId(movimiento_id)},
            {"$set": {
                "pdf_firmado": f"/static/pdfs/salidas/{filename}",
                "pdf_nombre": file.filename
            }}
        )
        
        return {
            "success": True,
            "message": "PDF subido exitosamente",
            "pdf_url": f"/static/pdfs/salidas/{filename}",
            "movimiento_id": movimiento_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir PDF: {str(e)}")

# Importar ObjectId
from bson import ObjectId

# Endpoints para Reservas (Salidas Pendientes)

@router.post("/reservas/guardar")
async def guardar_reserva_endpoint(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Guardar reserva de salida pendiente
    """
    try:
        # Obtener session_id de los query params
        session_id = request.query_params.get("session_id")
        
        # Obtener el body de la petición
        body = await request.json()
        items = body.get("items", [])
        datos_adicionales = body.get("datos_adicionales", {})
        
        print(f"🔵 Guardando reserva para sesión: {session_id}")
        print(f"📦 Items: {items}")
        print(f"📦 Datos adicionales: {datos_adicionales}")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id es requerido")
        
        if not items or len(items) == 0:
            raise HTTPException(status_code=400, detail="Debe haber al menos un item")
        
        reserva = await crud.guardar_reserva(db, session_id, items, datos_adicionales)
        return {"success": True, "reserva": reserva}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error guardando reserva: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reservas/obtener")
async def obtener_reserva_endpoint(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Obtener reserva de una sesión
    """
    try:
        reserva = await crud.obtener_reserva(db, session_id)
        return {"success": True, "reserva": reserva}
        
    except Exception as e:
        print(f"❌ Error obteniendo reserva: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reservas/eliminar")
async def eliminar_reserva_endpoint(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Eliminar reserva de una sesión (liberar stock)
    """
    try:
        print(f"🔵 Eliminando reserva para session_id: {session_id}")
        eliminado = await crud.eliminar_reserva(db, session_id)
        print(f"✅ Resultado: {eliminado}")
        return {"success": eliminado, "message": "Reserva eliminada" if eliminado else "No se encontró reserva"}
        
    except Exception as e:
        print(f"❌ Error eliminando reserva: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reservas/stock-disponible/{producto_id}")
async def obtener_stock_disponible(
    producto_id: str,
    session_id: str = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Obtener stock disponible considerando reservas
    """
    try:
        stock_info = await crud.obtener_stock_con_reservas(db, producto_id, session_id)
        return stock_info
        
    except Exception as e:
        print(f"❌ Error obteniendo stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reservas/confirmar")
async def confirmar_reserva(
    session_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    print(f"🔵 CONFIRMAR RESERVA - session_id: {session_id}")
    print(f"🔵 CONFIRMAR RESERVA - session_id: {session_id}")
    
    # Decodificar token manualmente
    token = credentials.credentials
    print(f"🔵 Token recibido: {token[:50]}...")
    
    payload = decode_token(token)
    print(f"🔵 Payload decodificado: {payload}")
    
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    if payload.get('rol') != 'super_admin':
        raise HTTPException(status_code=403, detail="No tienes permisos para confirmar salidas")
    
    # Crear current_user a partir del payload
    current_user = {
        "id": payload.get('sub'),
        "email": payload.get('email', 'admin'),
        "rol": payload.get('rol')
    }
    
    print(f"🔵 Usuario autenticado: {current_user}")
    
    remision = None
    try:
        reserva = await crud.obtener_reserva(db, session_id)
        if not reserva:
            print("❌ No hay reserva pendiente")
            raise HTTPException(status_code=404, detail="No hay reserva pendiente")
        
        print(f"📦 Reserva encontrada: {reserva.get('_id')}")
        print(f"📦 Items: {len(reserva.get('items', []))}")
        if not reserva:
            raise HTTPException(status_code=404, detail="No hay reserva pendiente")
        
        movimientos_creados = []
        datos_adicionales = reserva.get('datos_adicionales', {})
        tipo_reserva = datos_adicionales.get('tipo', 'normal')
        if not tipo_reserva or tipo_reserva == 'normal':
            if datos_adicionales.get('kitNombre'):
                tipo_reserva = 'kit'
        # ==========================================
        # MODO KIT
        # ==========================================
        if tipo_reserva == 'kit':
            kit_nombre = datos_adicionales.get('kitNombre', 'Kit')
            cliente = datos_adicionales.get('cliente', '')
            notas = datos_adicionales.get('notas', '')
    
            # ✅ Generar número de remisión
            remision = await crud.generar_numero_remision(db)
            print(f"📊 RM generado: {remision}")
    
             # Crear un solo movimiento con todos los productos del kit
            movimiento_kit = {
                 "producto_id": f"KIT_{kit_nombre.replace(' ', '_')}",
                 "producto_nombre": f"KIT: {kit_nombre}",
                 "tipo": "salida",
        "cantidad": 1,
        "motivo": "Salida de Kit",
        "notas": notas,
        "cliente_destino": cliente,
        "usuario": current_user.get("email", "admin"),  # ← MODIFICAR
        "usuario_id": current_user.get("id"),
        "fecha_movimiento": datetime.utcnow(),
        "kit_nombre": kit_nombre,
        "es_kit": True,
        "productos_kit": [],
        "remision": remision,  # ✅ Generado aquí
        "caso": datos_adicionales.get('caso', ''),  # ✅ Desde datos_adicionales
        "numero_cajas": 0  # Temporal, se actualizará por item
            }
    
            productos_col = db["productos"]
            ubicaciones_col = db["ubicaciones"]
            total_cajas = 0
    
            # Agregar los productos del kit y actualizar stock
            for item in reserva['items']:
                movimiento_kit["productos_kit"].append({
                    "producto_id": item['producto_id'],
                    "producto_nombre": item['producto_nombre'],
            "producto_codigo": item['producto_codigo'],
            "cantidad": item['cantidad']
                })
        
                # Sumar cajas si el item tiene el campo
                if item.get('cajas'):
                    total_cajas += item.get('cajas', 0)
        
                # Obtener el código real del producto
                codigo_producto = item.get('producto_codigo') or item.get('producto_id')
                if codigo_producto and len(str(codigo_producto)) == 24 and str(codigo_producto).isalnum():
                    from bson import ObjectId
                    producto_doc = await productos_col.find_one({"_id": ObjectId(codigo_producto)})
                    if producto_doc:
                        codigo_producto = producto_doc.get('codigo')
        
                 # Actualizar stock del producto
                producto = await productos_col.find_one({"codigo": codigo_producto})
                if producto:
                    nuevo_stock = producto['stock_actual'] - item['cantidad']
                    await productos_col.update_one(
                         {"codigo": codigo_producto},
                         {"$set": {"stock_actual": nuevo_stock, "fecha_actualizacion": datetime.now()}}
                    )
            
                     # Actualizar ubicación
                    await ubicaciones_col.update_one(
                        {
                          "producto_codigo": codigo_producto,
                          "ubicacion": item.get('ubicacion')
                        },
                        {
                          "$inc": {
                             "stock_fisico": -item['cantidad'],
                             "stock_reservado": -item['cantidad']
                           }
                        }
                    )
                    print(f"📍 Kit - Actualizando ubicación: {item.get('ubicacion')}, producto: {codigo_producto}, cantidad: -{item['cantidad']}")
     
            # Actualizar el número de cajas en el movimiento
            movimiento_kit["numero_cajas"] = total_cajas
    
    # Insertar el movimiento del kit
            movimientos_col = db["movimientos"]
            result = await movimientos_col.insert_one(movimiento_kit)
            nuevo_movimiento = await movimientos_col.find_one({"_id": result.inserted_id})
    
            if nuevo_movimiento and '_id' in nuevo_movimiento:
                nuevo_movimiento['id'] = str(nuevo_movimiento['_id'])
                del nuevo_movimiento['_id']
    
            movimientos_creados.append(nuevo_movimiento)
         
        # ==========================================
        # MODO MÚLTIPLE
        # ==========================================
        elif tipo_reserva == 'multiple':
            cliente = datos_adicionales.get('cliente', '')
            notas = datos_adicionales.get('notas', '')
           # ✅ Generar número de remisión
            remision = await crud.generar_numero_remision(db)
            print(f"📊 RM generado: {remision}")
            # Crear un solo movimiento con todos los productos
            movimiento_multiple = {
                "producto_id": f"MULTIPLE_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "producto_nombre": "Salida Múltiple",
        "tipo": "salida",
        "cantidad": 1,
        "motivo": "Entrega de Ayudas/Unidades",
        "notas": notas,
        "cliente_destino": cliente,
        "usuario": current_user.get("email", "admin"),  # ← MODIFICAR
        "usuario_id": current_user.get("id"),
        "fecha_movimiento": datetime.utcnow(),
        "es_multiple": True,
        "productos_multiple": [],
        "remision": remision,
        "caso": datos_adicionales.get('caso', ''),
        "numero_cajas": 0
            }
            
            productos_col = db["productos"]
            ubicaciones_col = db["ubicaciones"]
            total_cajas = 0
            
            # Agregar los productos y actualizar stock
            for item in reserva['items']:
                movimiento_multiple["productos_multiple"].append({
                    "producto_id": item['producto_id'],
                    "producto_nombre": item['producto_nombre'],
                    "producto_codigo": item['producto_codigo'],
                    "cantidad": item['cantidad']
                })
                
                if item.get('cajas'):
                    total_cajas += item.get('cajas', 0)
        
                codigo_producto = item.get('producto_codigo') or item.get('producto_id')
                if codigo_producto and len(str(codigo_producto)) == 24 and str(codigo_producto).isalnum():
                    from bson import ObjectId
                    producto_doc = await productos_col.find_one({"_id": ObjectId(codigo_producto)})
                    if producto_doc:
                        codigo_producto = producto_doc.get('codigo')
                
                # Actualizar stock del producto
                producto = await productos_col.find_one({"codigo": codigo_producto})
                if producto:
                    nuevo_stock = producto['stock_actual'] - item['cantidad']
                    await productos_col.update_one(
                        {"codigo": codigo_producto},
                        {"$set": {"stock_actual": nuevo_stock, "fecha_actualizacion": datetime.now()}}
                    )
                    
                    # Actualizar ubicación
                    await ubicaciones_col.update_one(
                        {
                            "producto_codigo": codigo_producto,
                            "ubicacion": item.get('ubicacion')
                        },
                        {
                            "$inc": {
                                "stock_fisico": -item['cantidad'],
                                "stock_reservado": -item['cantidad']
                            }
                        }
                    )
                    print(f"📍 Múltiple - Actualizando ubicación: {item.get('ubicacion')}, producto: {codigo_producto}, cantidad: -{item['cantidad']}")
            
            # Insertar el movimiento múltiple
            movimiento_multiple["numero_cajas"] = total_cajas
            
            movimientos_col = db["movimientos"]
            result = await movimientos_col.insert_one(movimiento_multiple)
            nuevo_movimiento = await movimientos_col.find_one({"_id": result.inserted_id})
            
            if nuevo_movimiento and '_id' in nuevo_movimiento:
                nuevo_movimiento['id'] = str(nuevo_movimiento['_id'])
                del nuevo_movimiento['_id']
            
            movimientos_creados.append(nuevo_movimiento)
        
        # ==========================================
        # MODO NORMAL (un solo producto)
        # ==========================================
        else:

            remision = await crud.generar_numero_remision(db)
            print(f"📊 RM generado para modo normal: {remision}")

            for item in reserva['items']:
                # Siempre usar producto_codigo, nunca producto_id
                codigo_producto = item.get('producto_codigo') or item.get('producto_id')
                
                # Si es ObjectId, obtener el código real
                if codigo_producto and len(str(codigo_producto)) == 24 and str(codigo_producto).isalnum():
                    from bson import ObjectId
                    producto_doc = await db["productos"].find_one({"_id": ObjectId(codigo_producto)})
                    if producto_doc:
                        codigo_producto = producto_doc.get('codigo')
                    else:
                        raise HTTPException(status_code=400, detail=f"Producto con ID {codigo_producto} no encontrado")
                
                movimiento = MovimientoCreate(
                    producto_id=codigo_producto,
                    tipo="salida",
                    cantidad=item['cantidad'],
                    motivo="Salida pendiente confirmada",
                    notas=datos_adicionales.get('notas', ''),
                    cliente_destino=datos_adicionales.get('cliente', ''),
                    ubicacion=item.get('ubicacion'),
                    usuario=current_user.get("email", "admin"),  # ← MODIFICAR
                    usuario_id=current_user.get("id"),
                    remision=remision
                )
                
                nuevo_mov = await crud.crear_movimiento(db=db, movimiento=movimiento)
                
                ubicaciones_col = db["ubicaciones"]
                await ubicaciones_col.update_one(
                    {
                        "producto_codigo": codigo_producto,
                        "ubicacion": item.get('ubicacion')
                    },
                    {
                        "$inc": {
                            "stock_fisico": -item['cantidad'],
                            "stock_reservado": -item['cantidad']
                        }
                    }
                )
                
                print(f"📍 Normal - Actualizando ubicación: {item.get('ubicacion')}, producto: {codigo_producto}, cantidad: -{item['cantidad']}")
                
                movimientos_creados.append(nuevo_mov)
        
        # ==========================================
        # ELIMINAR RESERVA (después de todos los casos)
        # ==========================================
        await crud.eliminar_reserva(db, session_id)
        
        return {
            "success": True,
            "movimientos": movimientos_creados,
            "remision": remision,
            "message": f"{len(movimientos_creados)} salida(s) confirmada(s)"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error confirmando reserva: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reservas/ajustar")
async def ajustar_reserva_endpoint(
    session_id: str,
    request: dict,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Ajustar reserva existente (aplica diferencias)
    """
    try:
        ajustes = request.get('ajustes', [])
        datos_adicionales = request.get('datos_adicionales', {})
        
        print(f"🔵 Ajustando reserva para sesión: {session_id}")
        print(f"📦 Ajustes: {ajustes}")
        
        reserva = await crud.ajustar_reserva(db, session_id, ajustes, datos_adicionales)
        return {"success": True, "reserva": reserva}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error ajustando reserva: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/salida/{movimiento_id}/pdf")
async def generar_pdf_salida_existente(
    movimiento_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Generar PDF de comprobante para una salida ya registrada
    """
    try:
        # Buscar el movimiento
        movimientos_col = db["movimientos"]
        
        try:
            movimiento = await movimientos_col.find_one({"_id": ObjectId(movimiento_id)})
        except:
            movimiento = await movimientos_col.find_one({"id": movimiento_id})
        
        if not movimiento:
            raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        

        print(f"🔍 === MOVIMIENTO ENCONTRADO ===")
        print(f"🔍 ID: {movimiento_id}")
        print(f"🔍 remision en BD: {movimiento.get('remision')}")
        print(f"🔍 caso en BD: {movimiento.get('caso')}")
        print(f"🔍 tipo: {movimiento.get('tipo')}")
        print(f"🔍 es_kit: {movimiento.get('es_kit')}")
        print(f"🔍 es_multiple: {movimiento.get('es_multiple')}")
        print(f"🔍 cliente_destino: {movimiento.get('cliente_destino')}")
        print(f"🔍 ==========================")
        
        if movimiento.get('tipo') != "salida":
            raise HTTPException(status_code=400, detail="El movimiento no es una salida")
        
        # Verificar si es un KIT o MÚLTIPLE
        es_kit = movimiento.get('es_kit', False)
        es_multiple = movimiento.get('es_multiple', False)
        
        if es_kit or es_multiple:
            # Es un KIT o salida múltiple con varios productos
            productos_kit = movimiento.get('productos_kit') or movimiento.get('productos_multiple', [])
            kit_nombre = movimiento.get('kit_nombre', 'Kit')
            
            salida_data = {
                'destino': movimiento.get('cliente_destino', 'No especificado'),
                'razon': movimiento.get('motivo', 'Salida de inventario'),
                'observaciones': movimiento.get('notas', ''),
                'usuario': movimiento.get('usuario', 'admin'),
                'fecha': movimiento.get('fecha_movimiento', datetime.now()).strftime("%d/%m/%Y %H:%M:%S"),
                'kit_nombre': kit_nombre if es_kit else None,
                'remision': movimiento.get('remision', 'N/A'),
                'caso': movimiento.get('caso', 'N/A'),
                'numero_cajas': movimiento.get('numero_cajas', 'N/A')
            }
            

            print(f"📊 === SALIDA_DATA (KIT/MULTIPLE) ===")
            print(f"📊 remision: {salida_data.get('remision')}")
            print(f"📊 caso: {salida_data.get('caso')}")
            print(f"📊 destino: {salida_data.get('destino')}")
            print(f"📊 =================================")

            productos_data = []
            for p in productos_kit:
                productos_data.append({
                    'producto_nombre': p.get('producto_nombre', 'Producto'),
                    'producto_codigo': p.get('producto_codigo', p.get('producto_id', 'N/A')),
                    'cantidad': p.get('cantidad', 0),
                    'cantidad_por_kit': p.get('cantidad', 0) if es_kit else None,
                    'cantidad_total': p.get('cantidad', 0)
                })
        else:
            # Salida normal (un solo producto)
            producto_id = movimiento.get('producto_id')
            producto = await crud.get_producto_por_codigo(db, producto_id)
            
            salida_data = {
                'destino': movimiento.get('cliente_destino', 'No especificado'),
                'razon': movimiento.get('motivo', 'Salida de inventario'),
                'observaciones': movimiento.get('notas', ''),
                'usuario': movimiento.get('usuario', 'admin'),
                'fecha': movimiento.get('fecha_movimiento', datetime.now()).strftime("%d/%m/%Y %H:%M:%S")
            }
            
            # ✅ LOG 3: Verificar que NO tiene remision en modo normal
            print(f"📊 === SALIDA_DATA (NORMAL) ===")
            print(f"📊 remision: {salida_data.get('remision', 'NO TIENE CAMPO REMISION')}")
            print(f"📊 ===========================")

            productos_data = [{
                'producto_nombre': movimiento.get('producto_nombre', producto.get('nombre') if producto else 'Producto'),
                'producto_codigo': producto_id,
                'cantidad': movimiento.get('cantidad', 0)
            }]
        
        print(f"📄 === ENVIANDO AL PDF ===")
        print(f"📄 salida_data completo: {salida_data}")
        print(f"📄 ======================")

        # Generar PDF
        pdf_generator = PDFGenerator()
        pdf_bytes = pdf_generator.generar_comprobante_salida(salida_data, productos_data)
        
        # Nombre del archivo
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        if es_kit:
            kit_nombre = movimiento.get('kit_nombre', 'kit')
            nombre_limpio = "".join([c for c in kit_nombre if c.isalnum() or c in [' ', '_', '-']])[:30].replace(' ', '_')
            filename = f"comprobante_kit_{nombre_limpio}_{fecha_str}.pdf"
        else:
            nombre_limpio = "".join([c for c in (movimiento.get('cliente_destino') or 'salida') if c.isalnum() or c in [' ', '_', '-']])[:30].replace(' ', '_')
            filename = f"comprobante_salida_{movimiento_id}_{nombre_limpio}_{fecha_str}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")
   
   
@router.get("/{movimiento_id}/pdf-info")
async def obtener_info_pdf(
    movimiento_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Obtener información del PDF asociado a un movimiento"""
    try:
        movimientos_col = db["movimientos"]
        
        try:
            movimiento = await movimientos_col.find_one({"_id": ObjectId(movimiento_id)})
        except:
            movimiento = await movimientos_col.find_one({"id": movimiento_id})
        
        if not movimiento:
            return {"tiene_pdf": False}
        
        tiene_pdf = movimiento.get("pdf_firmado") is not None
        pdf_url = None
        pdf_nombre = None
        
        if tiene_pdf:
            pdf_nombre = movimiento.get("pdf_nombre", "documento.pdf")
            pdf_url = movimiento.get("pdf_firmado")
        
        # También verificar si es un kit para mostrar información adicional
        es_kit = movimiento.get('es_kit', False)
        kit_nombre = movimiento.get('kit_nombre', None) if es_kit else None
        
        return {
            "tiene_pdf": tiene_pdf,
            "pdf_url": pdf_url,
            "pdf_nombre": pdf_nombre,
            "es_kit": es_kit,
            "kit_nombre": kit_nombre,
            "cantidad_productos": len(movimiento.get('productos_kit', [])) if es_kit else 1
        }
        
    except Exception as e:
        print(f"❌ Error en pdf-info: {e}")
        return {"tiene_pdf": False}

# ==========================================
# Endpoints para Mercados Predefinidos
# ==========================================

@router.get("/mercados")
async def get_mercados(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Obtener todos los mercados predefinidos"""
    try:
        mercados = await crud.get_mercados_predefinidos(db)
        return mercados
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mercados/{nombre}")
async def get_mercado_por_nombre(
    nombre: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Obtener un mercado predefinido por su nombre"""
    try:
        mercado = await crud.get_mercado_predefinido(db, nombre)
        if not mercado:
            raise HTTPException(status_code=404, detail=f"Mercado '{nombre}' no encontrado")
        return mercado
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/mercados/iniciar")
async def init_mercados(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Inicializar mercados predefinidos (Básico y Grande)"""
    try:
        resultado = await crud.init_mercados_predefinidos(db)
        return resultado
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# app/routers/movimientos.py - Modificar la función salida_por_mercado

@router.post("/salida-por-mercado")
async def salida_por_mercado(
    mercado_nombre: str,
    cantidad: int = 1,
    cliente: str = "",
    notas: str = "",
    referencia: str = "",
    usuario: str = "admin",
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Registrar salida de un mercado predefinido (Básico o Grande)
    """
    try:
        # Obtener el mercado
        mercado = await crud.get_mercado_predefinido(db, mercado_nombre)
        if not mercado:
            raise HTTPException(status_code=404, detail=f"Mercado '{mercado_nombre}' no encontrado")
        
        # Verificar stock para cada producto
        detalles_productos = []
        errores = []
        
        for producto in mercado["productos"]:
            cantidad_total = producto["cantidad"] * cantidad
            
            # Obtener stock disponible y ubicación
            stock_info = await crud.obtener_stock_con_reservas(db, producto["producto_id"])
            ubicaciones = await crud.get_ubicaciones_producto(db, producto["producto_id"])
            ubicacion = ubicaciones[0]["ubicacion"] if ubicaciones else "Sin ubicación"
            
            if stock_info.get("stock_disponible", 0) < cantidad_total:
                errores.append({
                    "producto_nombre": producto.get("producto_nombre", producto["producto_id"]),
                    "necesario": cantidad_total,
                    "disponible": stock_info.get("stock_disponible", 0)
                })
            
            detalles_productos.append({
                "producto_id": producto["producto_id"],
                "producto_nombre": producto.get("producto_nombre", producto["producto_id"]),
                "cantidad": cantidad_total,
                "ubicacion": ubicacion
            })
        
        if errores:
            return {
                "success": False,
                "error": "Stock insuficiente",
                "detalles": errores
            }
        
        # Generar número de remisión
        remision = await crud.generar_numero_remision(db)
        print(f"📊 RM generado: {remision}")


              
        # Crear movimientos y descontar stock
        movimientos_creados = []
        items_para_pdf = []
        
        for detalle in detalles_productos:
            # Buscar ubicación real con stock
            ubicaciones = await crud.get_ubicaciones_producto(db, detalle["producto_id"])
            ubicacion_seleccionada = None
            for ub in ubicaciones:
                if ub.get("stock_fisico", 0) >= detalle["cantidad"]:
                    ubicacion_seleccionada = ub["ubicacion"]
                    # Descontar de la ubicación
                    await db["ubicaciones"].update_one(
                        {"producto_codigo": detalle["producto_id"], "ubicacion": ubicacion_seleccionada},
                        {"$inc": {"stock_fisico": -detalle["cantidad"]}}
                    )
                    break
            
            if not ubicacion_seleccionada:
                ubicacion_seleccionada = "Sin ubicación disponible"
            
            # Obtener producto
            producto = await crud.get_producto_por_codigo(db, detalle["producto_id"])
            
            # Actualizar stock total del producto
            todas_ubicaciones = await db["ubicaciones"].find({"producto_codigo": detalle["producto_id"]}).to_list(length=None)
            nuevo_stock_total = sum(u.get("stock_fisico", 0) for u in todas_ubicaciones)
            
            await db["productos"].update_one(
                {"codigo": detalle["producto_id"]},
                {"$set": {"stock_actual": nuevo_stock_total, "stock_total": nuevo_stock_total}}
            )
            
            # Crear movimiento
            movimiento_dict = {
                "producto_id": detalle["producto_id"],
                "producto_nombre": detalle["producto_nombre"],
                "tipo": "salida",
                "cantidad": detalle["cantidad"],
                "motivo": f"Salida de {mercado_nombre}",
                "ubicacion": ubicacion_seleccionada,
                "notas": f"Mercado: {mercado_nombre} | {notas}",
                "cliente_destino": cliente,
                "usuario": usuario,
                "fecha_movimiento": datetime.utcnow(),
                "remision": remision,
                "referencia": referencia,
                "es_kit_mercado": True,
                "nombre_mercado": mercado_nombre,
                "pdf_firmado": None,
                "pdf_nombre": None
            }
            
            result = await db["movimientos"].insert_one(movimiento_dict)
            movimiento_dict['id'] = str(result.inserted_id)
            movimientos_creados.append(movimiento_dict)
            
            items_para_pdf.append({
                "producto_nombre": detalle["producto_nombre"],
                "producto_codigo": detalle["producto_id"],
                "cantidad": detalle["cantidad"],
                "ubicacion": ubicacion_seleccionada
            })
        
        # Generar PDF
        pdf_generator = PDFGenerator()
        
        datos_salida = {
            'destino': cliente,
            'razon': f'Salida de {mercado_nombre}',
            'observaciones': notas,
            'usuario': usuario,
            'fecha': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'remision': remision,
            'referencia': referencia,
            'es_mercado': True,
            'nombre_mercado': mercado_nombre,
            'cantidad_kits': cantidad
        }
        
        pdf_bytes = pdf_generator.generar_comprobante_salida_mercado(datos_salida, items_para_pdf)
        
        # Guardar PDF en el servidor (opcional)
        import os
        pdf_dir = "app/static/pdfs/salidas"
        os.makedirs(pdf_dir, exist_ok=True)
        
        nombre_limpio = "".join([c for c in cliente if c.isalnum() or c in [' ', '_', '-']])[:30].replace(' ', '_')
        filename = f"mercado_{mercado_nombre}_{remision}_{nombre_limpio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path = os.path.join(pdf_dir, filename)
        
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Remision": remision,
                "X-Movimientos": str(len(movimientos_creados))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comprobante-multiple")
async def generar_comprobante_multiple(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        body = await request.json()
        salidas = body.get('salidas', [])
        print(f"🔵 Comprobante múltiple - salidas: {len(salidas)}")
        for s in salidas:
            print(f"   - {s.get('nombre')}: RM={s.get('remision')}, CASO={s.get('caso')}, cajas={s.get('cajas')}")
        
        pdf_generator = PDFGenerator()
        pdf_bytes = pdf_generator.generar_comprobante_multiple(salidas)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=comprobante_multiple.pdf"}
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/reservas/confirmar-multiples")
async def confirmar_reservas_multiples(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Confirmar múltiples salidas pendientes en un solo comprobante"""
    try:
        body = await request.json()
        salidas = body.get('salidas', [])
        session_id = body.get('session_id')
        
        movimientos_creados = []
        salidas_confirmadas = []
        
        for salida in salidas:
            # Obtener la reserva para esta salida específica
            # (Necesitarás que cada salida tenga su propio identificador)
            # Por simplicidad, procesamos cada salida individualmente
            
            salidas_confirmadas.append({
                'nombre': salida.get('nombre', 'Salida'),
                'cliente': salida.get('cliente', 'No especificado'),
                'cajas': salida.get('cajas', 0),
                'remision': salida.get('remision', 'N/A'),
                'caso': salida.get('caso', 'N/A'),
                'productos': salida.get('productos', [])
            })
            
            # Aquí iría la lógica para actualizar el stock de cada producto
            # ...
        
        return {
            "success": True,
            "salidas": salidas_confirmadas,
            "message": f"{len(salidas)} salida(s) confirmada(s)"
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ==========================================
# ENDPOINTS PARA ENTRADAS PENDIENTES
# ==========================================
@router.post("/entradas-pendientes/guardar")
async def guardar_entrada_pendiente(
    entrada_data: dict,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_authenticated)
):
    """Guardar una entrada pendiente para confirmación posterior"""
    try:
        entradas_pendientes_col = db["entradas_pendientes"]
        
        print(f"🔵 Datos recibidos del frontend: {entrada_data}")
        
        # Limpiar los datos para eliminar cualquier ObjectId no serializable
        def limpiar_datos(obj):
            if isinstance(obj, dict):
                return {k: limpiar_datos(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [limpiar_datos(item) for item in obj]
            elif isinstance(obj, ObjectId):
                return str(obj)
            else:
                return obj
        
        datos_limpios = limpiar_datos(entrada_data)
        
        entrada = {
            "usuario_id": current_user["id"],
            "usuario_nombre": current_user.get("username", current_user.get("email")),
            "fecha_creacion": datetime.utcnow(),
            "estado": "pendiente",
            "datos": datos_limpios
        }
        
        result = await entradas_pendientes_col.insert_one(entrada)
        
        # Devolver solo datos serializables
        return {
            "success": True, 
            "entrada": {
                "id": str(result.inserted_id),
                "usuario_id": entrada["usuario_id"],
                "usuario_nombre": entrada["usuario_nombre"],
                "fecha_creacion": entrada["fecha_creacion"].isoformat(),
                "estado": entrada["estado"],
                "datos": datos_limpios
            }
        }
        
    except Exception as e:
        print(f"❌ Error guardando entrada pendiente: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entradas-pendientes")
async def obtener_entradas_pendientes(
    request: Request,  # ← Agregar Request para debugging
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_authenticated)
):
    """Obtener todas las entradas pendientes"""
    try:
        # Debug: Imprimir headers
        print(f"🔵 Headers recibidos: {dict(request.headers)}")
        print(f"🔵 Usuario en función: {current_user.get('id') if current_user else 'NO'}")
        print(f"🔵 Rol del usuario: {current_user.get('rol') if current_user else 'NO'}")
        
        entradas_pendientes_col = db["entradas_pendientes"]
        
        filtro = {}
        if current_user.get("rol") != "super_admin":
            filtro["usuario_id"] = current_user["id"]
        
        entradas = await entradas_pendientes_col.find(filtro).sort("fecha_creacion", -1).to_list(length=100)
        
        for e in entradas:
            e["id"] = str(e["_id"])
            del e["_id"]
        
        print(f"🔵 Entradas encontradas: {len(entradas)}")
        return entradas
        
    except Exception as e:
        print(f"❌ Error obteniendo entradas pendientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/entradas-pendientes/{entrada_id}")
async def eliminar_entrada_pendiente(
    entrada_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_authenticated)
):
    """Eliminar una entrada pendiente"""
    try:
        entradas_pendientes_col = db["entradas_pendientes"]
        
        # Verificar permiso
        entrada = await entradas_pendientes_col.find_one({"_id": ObjectId(entrada_id)})
        if not entrada:
            raise HTTPException(status_code=404, detail="Entrada no encontrada")
        
        if current_user.get("rol") != "super_admin" and entrada.get("usuario_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="No autorizado")
        
        await entradas_pendientes_col.delete_one({"_id": ObjectId(entrada_id)})
        
        return {"success": True, "message": "Entrada eliminada"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error eliminando entrada pendiente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/entradas-pendientes/eliminar-multiples")
async def eliminar_entradas_pendientes_multiples(
    data: dict,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_super_admin)
):
    """Eliminar múltiples entradas pendientes (solo super_admin)"""
    try:
        entradas_pendientes_col = db["entradas_pendientes"]
        entradas_ids = data.get("entradas_ids", [])
        
        if not entradas_ids:
            raise HTTPException(status_code=400, detail="No se proporcionaron IDs")
        
        eliminadas = 0
        for entrada_id in entradas_ids:
            try:
                result = await entradas_pendientes_col.delete_one({"_id": ObjectId(entrada_id)})
                if result.deleted_count > 0:
                    eliminadas += 1
            except:
                print(f"❌ Error eliminando {entrada_id}")
                continue
        
        return {
            "success": True, 
            "eliminadas": eliminadas,
            "total_solicitadas": len(entradas_ids)
        }
        
    except Exception as e:
        print(f"❌ Error en eliminar_entradas_pendientes_multiples: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/entradas-pendientes/confirmar")
async def confirmar_entradas_pendientes(
    entradas_ids: List[str],
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_super_admin)
):
    """Confirmar entradas pendientes (solo super_admin)"""
    try:
        entradas_pendientes_col = db["entradas_pendientes"]
        resultados = []
        
        for entrada_id in entradas_ids:
            entrada = await entradas_pendientes_col.find_one({"_id": ObjectId(entrada_id)})
            if entrada:
                # Aquí procesas la entrada (llamar a crear_entrada o entrada_multiple)
                datos = entrada["datos"]
                
                if datos["tipo"] == "multiple":
                    # Procesar entrada múltiple
                    data = {
                        "productos": datos["productos"],
                        "tipo_origen": datos["motivo"].lower(),
                        "origen_nombre": datos["origen_nombre"],
                        "observaciones": datos.get("notas", ""),
                        "usuario": current_user["username"]
                    }
                    # Llamar a tu función de entrada múltiple
                    # await crud.crear_entrada_multiple(db, ...)
                else:
                    # Procesar entrada individual
                    producto = datos["productos"][0]
                    data = {
                        "producto_id": producto["producto_id"],
                        "cantidad": producto["cantidad"],
                        "motivo": datos["motivo"],
                        "origen_nombre": datos["origen_nombre"],
                        "ubicacion": producto.get("ubicacion", "ALMACEN_GENERAL"),
                        "notas": datos.get("notas", ""),
                        "usuario": current_user["username"]
                    }
                    # Llamar a tu función de entrada
                    # await crud.crear_movimiento(db, ...)
                
                # Marcar como confirmada o eliminar
                await entradas_pendientes_col.update_one(
                    {"_id": ObjectId(entrada_id)},
                    {"$set": {"estado": "confirmada", "fecha_confirmacion": datetime.utcnow()}}
                )
                resultados.append({"id": entrada_id, "success": True})
        
        return {"success": True, "resultados": resultados}
        
    except Exception as e:
        print(f"❌ Error confirmando entradas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# ENDPOINTS PARA SALIDAS PENDIENTES
# ==========================================

@router.post("/salidas-pendientes/guardar")
async def guardar_salida_pendiente(
    salida_data: dict,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_authenticated)
):
    """Guardar una salida pendiente para confirmación posterior"""
    try:
        salidas_pendientes_col = db["salidas_pendientes"]
        
        print(f"🔵 Datos recibidos del frontend: {salida_data}")
        
        # Limpiar los datos para eliminar cualquier ObjectId no serializable
        def limpiar_datos(obj):
            if isinstance(obj, dict):
                return {k: limpiar_datos(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [limpiar_datos(item) for item in obj]
            elif isinstance(obj, ObjectId):
                return str(obj)
            else:
                return obj
        
        datos_limpios = limpiar_datos(salida_data)
        
        salida = {
            "usuario_id": current_user["id"],
            "usuario_nombre": current_user.get("username", current_user.get("email")),
            "fecha_creacion": datetime.utcnow(),
            "estado": "pendiente",
            "datos": datos_limpios
        }
        
        result = await salidas_pendientes_col.insert_one(salida)
        
        return {
            "success": True, 
            "salida": {
                "id": str(result.inserted_id),
                "usuario_id": salida["usuario_id"],
                "usuario_nombre": salida["usuario_nombre"],
                "fecha_creacion": salida["fecha_creacion"].isoformat(),
                "estado": salida["estado"],
                "datos": datos_limpios
            }
        }
        
    except Exception as e:
        print(f"❌ Error guardando salida pendiente: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/salidas-pendientes")
async def obtener_salidas_pendientes(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_authenticated)
):
    """Obtener todas las salidas pendientes (super_admin ve todas, otros ven las suyas)"""
    try:
        salidas_pendientes_col = db["salidas_pendientes"]
        
        filtro = {}
        if current_user.get("rol") != "super_admin":
            filtro["usuario_id"] = current_user["id"]
        
        salidas = await salidas_pendientes_col.find(filtro).sort("fecha_creacion", -1).to_list(length=100)
        
        for s in salidas:
            s["id"] = str(s["_id"])
            del s["_id"]
        
        print(f"🔵 Salidas pendientes encontradas: {len(salidas)}")
        return salidas
        
    except Exception as e:
        print(f"❌ Error obteniendo salidas pendientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/salidas-pendientes/{salida_id}")
async def eliminar_salida_pendiente(
    salida_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_authenticated)
):
    """Eliminar una salida pendiente"""
    try:
        salidas_pendientes_col = db["salidas_pendientes"]
        
        # Verificar permiso
        salida = await salidas_pendientes_col.find_one({"_id": ObjectId(salida_id)})
        if not salida:
            raise HTTPException(status_code=404, detail="Salida no encontrada")
        
        if current_user.get("rol") != "super_admin" and salida.get("usuario_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="No autorizado")
        
        await salidas_pendientes_col.delete_one({"_id": ObjectId(salida_id)})
        
        return {"success": True, "message": "Salida eliminada"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error eliminando salida pendiente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/salidas-pendientes/eliminar-multiples")
async def eliminar_salidas_pendientes_multiples(
    data: dict,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_super_admin)
):
    """Eliminar múltiples salidas pendientes (solo super_admin)"""
    try:
        salidas_pendientes_col = db["salidas_pendientes"]
        salidas_ids = data.get("salidas_ids", [])
        
        if not salidas_ids:
            raise HTTPException(status_code=400, detail="No se proporcionaron IDs")
        
        eliminadas = 0
        for salida_id in salidas_ids:
            try:
                result = await salidas_pendientes_col.delete_one({"_id": ObjectId(salida_id)})
                if result.deleted_count > 0:
                    eliminadas += 1
            except:
                print(f"❌ Error eliminando {salida_id}")
                continue
        
        return {
            "success": True, 
            "eliminadas": eliminadas,
            "total_solicitadas": len(salidas_ids)
        }
        
    except Exception as e:
        print(f"❌ Error en eliminar_salidas_pendientes_multiples: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/salidas-pendientes/confirmar")
async def confirmar_salidas_pendientes(
    data: dict,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_super_admin)
):
    """Confirmar salidas pendientes y procesarlas en inventario (solo super_admin)"""
    try:
        salidas_pendientes_col = db["salidas_pendientes"]
        salidas_ids = data.get("salidas_ids", [])
        resultados = []
        
        for salida_id in salidas_ids:
            salida = await salidas_pendientes_col.find_one({"_id": ObjectId(salida_id)})
            if salida:
                datos = salida["datos"]
                
                # Aquí procesas la salida (crear movimiento en inventario)
                # Por ahora marcamos como confirmada
                await salidas_pendientes_col.update_one(
                    {"_id": ObjectId(salida_id)},
                    {"$set": {"estado": "confirmada", "fecha_confirmacion": datetime.utcnow()}}
                )
                resultados.append({"id": salida_id, "success": True})
        
        return {"success": True, "resultados": resultados}
        
    except Exception as e:
        print(f"❌ Error confirmando salidas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
