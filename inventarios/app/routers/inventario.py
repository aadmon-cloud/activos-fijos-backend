# app/routers/inventario.py
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Dict, Any
from .. import crud
from ..database import get_database

router = APIRouter(prefix="/inventario", tags=["inventario"])

@router.get("/dashboard")
async def get_dashboard_stats(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Obtener estadísticas para el dashboard principal"""
    stats = await crud.get_estadisticas_dashboard(db)
    
    # Convertir ObjectId a string en los movimientos
    for mov in stats.get('ultimos_movimientos', []):
        if '_id' in mov:
            mov['id'] = str(mov['_id'])
            del mov['_id']
    
    return stats

@router.get("/reporte")
async def obtener_reporte_inventario(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Obtener reporte completo del inventario"""
    productos = await crud.get_productos(db)
    productos_bajo_stock = await crud.get_productos_bajo_stock(db)
    valor_total = await crud.get_valor_total_inventario(db)
    ultimos_movimientos = await crud.get_movimientos(db, limit=10)
    
    # Convertir ObjectId a string
    for p in productos:
        if '_id' in p:
            p['id'] = str(p['_id'])
            del p['_id']
    
    for p in productos_bajo_stock:
        if '_id' in p:
            p['id'] = str(p['_id'])
            del p['_id']
    
    for m in ultimos_movimientos:
        if '_id' in m:
            m['id'] = str(m['_id'])
            del m['_id']
    
    return {
        "total_productos": len(productos),
        "productos_bajo_stock": productos_bajo_stock,
        "valor_total_inventario": valor_total,
        "ultimos_movimientos": ultimos_movimientos
    }

@router.get("/bajo-stock")
async def obtener_productos_bajo_stock(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Obtener productos con stock por debajo del mínimo"""
    productos = await crud.get_productos_bajo_stock(db)
    
    for p in productos:
        if '_id' in p:
            p['id'] = str(p['_id'])
            del p['_id']
    
    return productos

@router.get("/valor-total")
async def obtener_valor_total_inventario(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Obtener valor total del inventario"""
    valor = await crud.get_valor_total_inventario(db)
    return {"valor_total_inventario": valor}

@router.get("/producto/{producto_id}/historial")
async def obtener_historial_producto(
    producto_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Obtener historial completo de un producto"""
    resultado = await crud.get_historial_completo_producto(db, producto_id)
    
    if "error" in resultado:
        raise HTTPException(status_code=404, detail=resultado["error"])
    
    # Convertir ObjectId a string
    if '_id' in resultado['producto']:
        resultado['producto']['id'] = str(resultado['producto']['_id'])
        del resultado['producto']['_id']
    
    for mov in resultado['historial']:
        if '_id' in mov:
            mov['id'] = str(mov['_id'])
            del mov['_id']
    
    return resultado