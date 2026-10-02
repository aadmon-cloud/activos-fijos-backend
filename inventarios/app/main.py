# app/main.py
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import os
import sys
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
# Añadir el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import connect_to_mongo, close_mongo_connection, get_database, init_db
from app import crud
from app.models import CodigoEscaneado
from app.routers import auth, productos, movimientos, inventario, admin


# ===== Lifespan context manager para conexiones =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando aplicación...")
    try:
        await connect_to_mongo()
        await init_db()
        print("✅ Sistema iniciado correctamente")
    except Exception as e:
        print(f"❌ Error crítico al iniciar: {e}")
        print("💡 La aplicación continuará ejecutándose pero las operaciones de BD fallarán")
        # No lanzamos la excepción para que la app siga corriendo
    yield
    # Shutdown
    await close_mongo_connection()
    print("👋 Aplicación cerrada")

# ===== Crear app =====
app = FastAPI(
    title="Sistema de Inventario FIMLM",
    description="Gestión de inventario con códigos QR y escaneo por cámara",
    version="1.0.0",
    lifespan=lifespan
)

# ===== CONFIGURAR CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.0.11:3000",
        "http://192.168.0.11",
        "http://192.168.0.100:3000",
        "http://192.168.1.100:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== SESSION MIDDLEWARE (para Google OAuth) =====
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("SECRET_KEY", "tu-secret-key-muy-segura-cambiala-en-produccion"),
    session_cookie="inventario_session",
    max_age=3600  # 1 hora
)

# Crear directorio de templates si no existe
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
    print(f"📁 Creado directorio de templates: {templates_dir}")

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=templates_dir)

# ===== Routers API =====
app.include_router(auth.router, prefix="/api")
app.include_router(productos.router, prefix="/api")
app.include_router(movimientos.router, prefix="/api")
app.include_router(inventario.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

# ===== Endpoint de prueba para verificar estado =====
@app.get("/api/health")
async def health_check():
    """Verificar estado del sistema"""
    status = {
        "status": "ok",
        "mongo_connected": False,
        "database": None
    }
    
    try:
        db = get_database()
        await db.command("ping")
        status["mongo_connected"] = True
        status["database"] = db.name
    except Exception as e:
        status["status"] = "degraded"
        status["error"] = str(e)
    
    return status

@app.get("/api/test")
async def test_endpoint():
    return {"message": "¡Sistema de Inventario funcionando!", "status": "ok", "version": "1.0.0"}

# ===== RUTAS FRONTEND (HTML) =====
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Inventario FIMLM"})

@app.get("/productos", response_class=HTMLResponse)
async def pagina_productos(request: Request):
    return templates.TemplateResponse("productos.html", {"request": request, "title": "Productos"})

@app.get("/productos/crear", response_class=HTMLResponse)
async def pagina_crear_producto(request: Request):
    return templates.TemplateResponse("crear_producto.html", {"request": request, "title": "Crear Producto"})

@app.get("/entrada", response_class=HTMLResponse)
async def pagina_entrada(request: Request):
    return templates.TemplateResponse("entrada.html", {"request": request, "title": "Entrada de Productos"})

@app.get("/salida", response_class=HTMLResponse)
async def pagina_salida(request: Request):
    return templates.TemplateResponse("salida.html", {"request": request, "title": "Salida de Productos"})

@app.get("/movimientos", response_class=HTMLResponse)
async def pagina_movimientos(request: Request):
    return templates.TemplateResponse("movimientos.html", {"request": request, "title": "Movimientos"})

@app.get("/escanear", response_class=HTMLResponse)
async def pagina_escanear(request: Request):
    return templates.TemplateResponse("escanear.html", {"request": request, "title": "Escanear Códigos"})

@app.get("/productos/{producto_id}/detalle", response_class=HTMLResponse)
async def pagina_detalle_producto(request: Request, producto_id: str, db=Depends(get_database)):
    """Página de detalle de producto"""
    try:
        producto = await crud.get_producto(db, producto_id)
        if not producto:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "title": "Error", "error": "Producto no encontrado"},
                status_code=404
            )
        historial = await crud.get_movimientos_por_producto(db, producto_id)
        return templates.TemplateResponse(
            "detalle_producto.html",
            {"request": request, "title": f"Producto: {producto['nombre']}", 
             "producto": producto, "historial": historial}
        )
    except Exception as e:
        print(f"Error en detalle producto: {e}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "title": "Error", "error": f"Error al cargar producto: {str(e)}"},
            status_code=500
        )

@app.get("/productos/{producto_id}/editar", response_class=HTMLResponse)
async def pagina_editar_producto(request: Request, producto_id: str, db=Depends(get_database)):
    """Página de edición de producto"""
    try:
        producto = await crud.get_producto(db, producto_id)
        if not producto:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "title": "Error", "error": "Producto no encontrado"},
                status_code=404
            )
        return templates.TemplateResponse(
            "editar_producto.html",
            {"request": request, "title": f"Editar: {producto['nombre']}", "producto": producto}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "title": "Error", "error": f"Error al cargar producto: {str(e)}"},
            status_code=500
        )

@app.get("/productos/cargar-excel", response_class=HTMLResponse)
async def pagina_cargar_excel(request: Request):
    return templates.TemplateResponse("cargar_excel.html", {"request": request, "title": "Cargar Productos desde Excel"})

# ===== API Endpoint para escaneo =====
@app.post("/api/escanear")
async def procesar_codigo_escaneado(codigo: CodigoEscaneado, db=Depends(get_database)):
    """Procesar código escaneado"""
    try:
        producto = await crud.get_producto_por_codigo(db, codigo.codigo)
        if producto:
            # Convertir ObjectId a string
            if '_id' in producto:
                producto['id'] = str(producto['_id'])
                del producto['_id']
            return {
                "encontrado": True,
                "producto": producto,
                "mensaje": f"Producto encontrado: {producto['nombre']}",
                "stock_actual": producto['stock_actual'],
                "accion_sugerida": codigo.tipo_operacion
            }
        return {
            "encontrado": False,
            "codigo": codigo.codigo,
            "mensaje": "Producto no encontrado.",
            "accion_sugerida": "crear_producto"
        }
    except Exception as e:
        print(f"Error en escaneo: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando código: {str(e)}")

# ===== REDIRECCIONES =====
@app.get("/volver-a-productos")
async def volver_a_productos():
    return RedirectResponse(url="/productos")

@app.get("/volver-a-inicio")
async def volver_a_inicio():
    return RedirectResponse(url="/")

# ===== Manejo de errores =====
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
    if request.url.path.startswith('/api'):
        return JSONResponse(status_code=404, content={"message": "Recurso no encontrado"})
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "title": "404 - No encontrado", "error": "La página que buscas no existe"},
        status_code=404
    )

@app.exception_handler(500)
async def internal_exception_handler(request: Request, exc):
    print(f"Error 500: {exc}")
    if request.url.path.startswith('/api'):
        return JSONResponse(status_code=500, content={"message": "Error interno del servidor"})
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "title": "500 - Error interno", "error": "Ha ocurrido un error interno en el servidor"},
        status_code=500
    )

# ===== EJECUTAR LOCAL =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)