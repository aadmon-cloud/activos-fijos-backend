# reset.ps1
Write-Host "🔄 REINICIANDO BASE DE DATOS..." -ForegroundColor Yellow
Write-Host "=" * 50 -ForegroundColor Yellow

# Eliminar BD
if (Test-Path "app/inventario.db") {
    Remove-Item -Path "app/inventario.db" -Force
    Write-Host "✅ Base de datos eliminada" -ForegroundColor Green
}

# Crear nuevas tablas
python -c "
from app.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)
print('✅ Tablas creadas: movimientos, productos')
" 2>$null

Write-Host "`n🚀 INICIANDO SERVIDOR..." -ForegroundColor Cyan
Write-Host "Presiona Ctrl+C para detener`n" -ForegroundColor Gray

# Iniciar servidor
uvicorn app.main:app --reload