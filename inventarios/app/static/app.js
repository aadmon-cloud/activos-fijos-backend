// app/static/app.js
// Funciones principales de la aplicación

// API Client
class InventarioAPI {
    constructor() {
        this.baseURL = '/api';
    }

    async get(endpoint) {
        const response = await fetch(`${this.baseURL}${endpoint}`);
        return await response.json();
    }

    async post(endpoint, data) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await response.json();
    }

    async put(endpoint, data) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await response.json();
    }

    async delete(endpoint) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'DELETE'
        });
        return await response.json();
    }

    // Métodos específicos
    async buscarProducto(codigo) {
        return await this.get(`/productos/codigo/${codigo}`);
    }

    async crearProducto(producto) {
        return await this.post('/productos/', producto);
    }

    async registrarMovimiento(movimiento) {
        return await this.post('/movimientos/', movimiento);
    }

    async entradaRapida(productoId, cantidad, motivo = '') {
        return await this.post(`/movimientos/entrada-rapida?producto_id=${productoId}&cantidad=${cantidad}&motivo=${motivo}`);
    }

    async salidaRapida(productoId, cantidad, motivo = '') {
        return await this.post(`/movimientos/salida-rapida?producto_id=${productoId}&cantidad=${cantidad}&motivo=${motivo}`);
    }
}

// Sistema de Escaneo con HTML5 QR Code
class EscanerQR {
    constructor() {
        this.html5QrCode = null;
        this.onScanSuccess = null;
        this.active = false;
    }

    async iniciar(elementId, onSuccess) {
        try {
            // Verificar si ya existe una instancia
            if (this.html5QrCode) {
                await this.detener();
            }

            this.onScanSuccess = onSuccess;
            
            // Crear nueva instancia
            this.html5QrCode = new Html5Qrcode(elementId);
            
            // Configuración de la cámara
            const config = {
                fps: 10,
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0
            };

            // Iniciar escaneo
            await this.html5QrCode.start(
                { facingMode: "environment" },
                config,
                (decodedText) => {
                    if (this.onScanSuccess) {
                        this.onScanSuccess(decodedText);
                    }
                },
                (errorMessage) => {
                    // Los errores de no encontrar QR son normales
                    console.log(`Escaneando: ${errorMessage}`);
                }
            );

            this.active = true;
            console.log('Escáner iniciado');
            return true;

        } catch (error) {
            console.error('Error iniciando escáner:', error);
            this.mostrarErrorCamara();
            return false;
        }
    }

    async detener() {
        if (this.html5QrCode && this.active) {
            try {
                await this.html5QrCode.stop();
                this.html5QrCode.clear();
                this.active = false;
                console.log('Escáner detenido');
            } catch (error) {
                console.error('Error deteniendo escáner:', error);
            }
        }
    }

    mostrarErrorCamara() {
        // Mostrar interfaz manual como fallback
        const scannerContainer = document.getElementById('scanner-container');
        if (scannerContainer) {
            scannerContainer.innerHTML = `
                <div class="camera-error">
                    <div class="error-icon">
                        <i class="fas fa-video-slash fa-3x"></i>
                    </div>
                    <h3>No se pudo acceder a la cámara</h3>
                    <p>Posibles causas:</p>
                    <ul>
                        <li>No tienes una cámara disponible</li>
                        <li>No has dado permisos de cámara</li>
                        <li>La cámara está siendo usada por otra aplicación</li>
                    </ul>
                    <div class="error-actions">
                        <button onclick="mostrarInputManual()" class="btn btn-primary">
                            <i class="fas fa-keyboard"></i> Usar entrada manual
                        </button>
                        <button onclick="location.reload()" class="btn btn-secondary">
                            <i class="fas fa-redo"></i> Reintentar
                        </button>
                    </div>
                </div>
            `;
        }
    }

    cambiarCamara() {
        if (this.html5QrCode) {
            // Obtener cámaras disponibles
            Html5Qrcode.getCameras().then(cameras => {
                if (cameras && cameras.length > 1) {
                    // Cambiar a la siguiente cámara
                    const currentCamera = this.html5QrCode.getRunningTrackSettings();
                    const nextCameraIndex = cameras.findIndex(cam => 
                        cam.id !== currentCamera.deviceId
                    );
                    
                    if (nextCameraIndex >= 0) {
                        this.html5QrCode.stop().then(() => {
                            this.iniciar('reader', this.onScanSuccess);
                        });
                    }
                }
            });
        }
    }
}

// Instancias globales
const api = new InventarioAPI();
const escaner = new EscanerQR();

// Funciones globales
async function procesarCodigoEscaneado(codigo, tipoOperacion = 'consulta') {
    console.log(`Código escaneado: ${codigo}, Operación: ${tipoOperacion}`);
    
    // Mostrar feedback
    mostrarFeedbackEscaneo(codigo);
    
    // Procesar código
    const resultado = await api.post('/escanear', {
        codigo: codigo,
        tipo_operacion: tipoOperacion
    });
    
    if (resultado.error) {
        mostrarError(resultado.mensaje);
        return;
    }
    
    if (resultado.encontrado) {
        // Producto encontrado
        mostrarProductoEncontrado(resultado.producto, tipoOperacion);
    } else {
        // Producto no encontrado
        mostrarOpcionCrearProducto(codigo, tipoOperacion);
    }
}
async function buscarProductoGlobal(codigoONombre) {
    try {
        console.log('Buscando producto:', codigoONombre); // Debug
        const response = await fetch(`/api/productos/buscar?q=${encodeURIComponent(codigoONombre)}`);
        console.log('Response status:', response.status); // Debug
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error buscando producto:', error);
        throw error;
    }
}
function mostrarFeedbackEscaneo(codigo) {
    // Crear o actualizar notificación
    let feedback = document.getElementById('scan-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.id = 'scan-feedback';
        feedback.className = 'scan-feedback';
        document.body.appendChild(feedback);
    }
    
    feedback.innerHTML = `
        <div class="feedback-content">
            <i class="fas fa-check-circle"></i>
            <span>Código detectado: ${codigo}</span>
        </div>
    `;
    
    feedback.classList.add('show');
    
    // Ocultar después de 2 segundos
    setTimeout(() => {
        feedback.classList.remove('show');
    }, 2000);
}

function mostrarProductoEncontrado(producto, tipoOperacion) {
    const modal = crearModal(`
        <h3><i class="fas fa-check-circle text-success"></i> Producto Encontrado</h3>
        <div class="producto-info">
            <p><strong>Nombre:</strong> ${producto.nombre}</p>
            <p><strong>Código:</strong> ${producto.codigo}</p>
            <p><strong>Stock Actual:</strong> ${producto.stock_actual}</p>
            <p><strong>Precio:</strong> $${producto.precio_unitario}</p>
        </div>
        
        ${tipoOperacion !== 'consulta' ? `
        <div class="movimiento-form">
            <h4>Registrar ${tipoOperacion === 'entrada' ? 'Entrada' : 'Salida'}</h4>
            <div class="form-group">
                <label for="cantidad-${producto.id}">Cantidad:</label>
                <input type="number" id="cantidad-${producto.id}" 
                       value="1" min="1" class="form-control">
            </div>
            <div class="form-group">
                <label for="motivo-${producto.id}">Motivo:</label>
                <input type="text" id="motivo-${producto.id}" 
                       placeholder="Ej: Compra, Venta, Ajuste..."
                       class="form-control">
            </div>
            <div class="modal-buttons">
                <button onclick="registrarMovimiento(${producto.id}, '${tipoOperacion}')" 
                        class="btn btn-success">
                    <i class="fas fa-save"></i> Registrar
                </button>
                <button onclick="cerrarModal()" class="btn btn-secondary">
                    <i class="fas fa-times"></i> Cancelar
                </button>
            </div>
        </div>
        ` : `
        <div class="modal-buttons">
            <button onclick="window.location.href='/productos/${producto.id}'" 
                    class="btn btn-primary">
                <i class="fas fa-eye"></i> Ver Detalles
            </button>
            <button onclick="cerrarModal()" class="btn btn-secondary">
                <i class="fas fa-times"></i> Cerrar
            </button>
        </div>
        `}
    `);
    
    mostrarModal(modal);
}

async function registrarMovimiento(productoId, tipo) {
    const cantidadInput = document.getElementById(`cantidad-${productoId}`);
    const motivoInput = document.getElementById(`motivo-${productoId}`);
    
    if (!cantidadInput || parseInt(cantidadInput.value) <= 0) {
        alert('Por favor ingresa una cantidad válida');
        return;
    }
    
    const cantidad = parseInt(cantidadInput.value);
    const motivo = motivoInput ? motivoInput.value : '';
    
    try {
        let resultado;
        if (tipo === 'entrada') {
            resultado = await api.entradaRapida(productoId, cantidad, motivo);
        } else {
            resultado = await api.salidaRapida(productoId, cantidad, motivo);
        }
        
        if (resultado.error) {
            throw new Error(resultado.mensaje);
        }
        
        mostrarExito(`¡${tipo === 'entrada' ? 'Entrada' : 'Salida'} registrada! Stock actual: ${resultado.stock_actual}`);
        cerrarModal();
        
        // Continuar escaneando después de 1 segundo
        setTimeout(() => {
            if (escaner.active) {
                console.log('Continuando escaneo...');
            }
        }, 1000);
        
    } catch (error) {
        mostrarError(error.message);
    }
}

function mostrarOpcionCrearProducto(codigo, tipoOperacion) {
    const modal = crearModal(`
        <h3><i class="fas fa-exclamation-triangle text-warning"></i> Producto No Encontrado</h3>
        <p>El código <strong>${codigo}</strong> no existe en el sistema.</p>
        
        <div class="crear-producto-form">
            <h4>Crear Nuevo Producto</h4>
            <div class="form-group">
                <label>Código:</label>
                <input type="text" value="${codigo}" readonly class="form-control">
            </div>
            <div class="form-group">
                <label for="nombre-${codigo}">Nombre del Producto:</label>
                <input type="text" id="nombre-${codigo}" 
                       placeholder="Ej: Laptop HP EliteBook"
                       class="form-control" required>
            </div>
            <div class="form-group">
                <label for="precio-${codigo}">Precio Unitario:</label>
                <input type="number" id="precio-${codigo}" 
                       step="0.01" min="0" value="0"
                       class="form-control">
            </div>
            <div class="modal-buttons">
                <button onclick="crearProductoDesdeCodigo('${codigo}', '${tipoOperacion}')" 
                        class="btn btn-success">
                    <i class="fas fa-plus-circle"></i> Crear Producto
                </button>
                <button onclick="cerrarModal()" class="btn btn-secondary">
                    <i class="fas fa-times"></i> Cancelar
                </button>
            </div>
        </div>
    `);
    
    mostrarModal(modal);
}

async function crearProductoDesdeCodigo(codigo, tipoOperacion) {
    const nombreInput = document.getElementById(`nombre-${codigo}`);
    const precioInput = document.getElementById(`precio-${codigo}`);
    
    if (!nombreInput || !nombreInput.value.trim()) {
        alert('Por favor ingresa un nombre para el producto');
        return;
    }
    
    const productoData = {
        codigo: codigo,
        nombre: nombreInput.value.trim(),
        precio_unitario: parseFloat(precioInput?.value || 0),
        descripcion: `Producto creado por escaneo`,
        categoria: 'General',
        stock_minimo: 5,
        ubicacion: 'Almacén'
    };
    
    try {
        const resultado = await api.crearProducto(productoData);
        
        if (resultado.error) {
            throw new Error(resultado.mensaje);
        }
        
        mostrarExito(`¡Producto creado exitosamente! ID: ${resultado.id}`);
        cerrarModal();
        
        // Si era para entrada/salida, mostrar formulario de movimiento
        if (tipoOperacion !== 'consulta') {
            setTimeout(() => {
                mostrarProductoEncontrado(resultado, tipoOperacion);
            }, 1000);
        }
        
    } catch (error) {
        mostrarError(error.message);
    }
}

// Funciones de UI
function crearModal(content) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-overlay" onclick="cerrarModal()"></div>
        <div class="modal-content">
            <button class="modal-close" onclick="cerrarModal()">
                <i class="fas fa-times"></i>
            </button>
            ${content}
        </div>
    `;
    return modal;
}

function mostrarModal(modal) {
    document.body.appendChild(modal);
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

function cerrarModal() {
    const modal = document.querySelector('.modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.remove();
        }, 300);
    }
}

function mostrarExito(mensaje) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-success';
    alert.innerHTML = `<i class="fas fa-check-circle"></i> ${mensaje}`;
    mostrarNotificacion(alert);
}

function mostrarError(mensaje) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger';
    alert.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${mensaje}`;
    mostrarNotificacion(alert);
}

function mostrarNotificacion(element) {
    const container = document.getElementById('notifications') || crearContenedorNotificaciones();
    container.appendChild(element);
    
    setTimeout(() => {
        element.remove();
    }, 5000);
}

function crearContenedorNotificaciones() {
    const container = document.createElement('div');
    container.id = 'notifications';
    container.className = 'notifications';
    document.body.appendChild(container);
    return container;
}

// Funciones para páginas específicas
async function iniciarEscaneoPagina(tipoOperacion = 'consulta') {
    try {
        const iniciado = await escaner.iniciar('reader', (codigo) => {
            procesarCodigoEscaneado(codigo, tipoOperacion);
        });
        
        if (iniciado) {
            // Mostrar controles
            document.getElementById('scanner-controls').style.display = 'flex';
        }
        
    } catch (error) {
        console.error('Error:', error);
    }
}

function detenerEscaneoPagina() {
    escaner.detener();
    document.getElementById('scanner-controls').style.display = 'none';
}

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    // Verificar si estamos en la página de escaneo
    if (window.location.pathname.includes('/escanear')) {
        // Configurar botones de operación
        const botonesOperacion = document.querySelectorAll('.btn-operacion');
        botonesOperacion.forEach(boton => {
            boton.addEventListener('click', function() {
                const tipo = this.dataset.operacion;
                document.getElementById('operacion-actual').textContent = 
                    tipo === 'entrada' ? 'Entrada' : 
                    tipo === 'salida' ? 'Salida' : 'Consulta';
                
                // Reiniciar escáner con nuevo tipo
                detenerEscaneoPagina();
                setTimeout(() => iniciarEscaneoPagina(tipo), 500);
            });
        });
        
        // Iniciar escaneo por defecto (consulta)
        setTimeout(() => iniciarEscaneoPagina('consulta'), 1000);
    }
    
    // Cargar datos de productos si estamos en esa página
    if (window.location.pathname.includes('/productos') && 
        !window.location.pathname.includes('/crear')) {
        cargarProductos();
    }
});

async function cargarProductos() {
    try {
        const productos = await api.get('/productos/');
        const container = document.getElementById('productos-container');
        
        if (!container) return;
        
        if (productos.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-box-open fa-3x"></i>
                    <h3>No hay productos registrados</h3>
                    <p>Comienza agregando tu primer producto</p>
                    <a href="/productos/crear" class="btn btn-primary">
                        <i class="fas fa-plus"></i> Crear Producto
                    </a>
                </div>
            `;
            return;
        }
        
        let html = '<div class="productos-grid">';
        productos.forEach(producto => {
            const bajoStock = producto.stock_actual < producto.stock_minimo;
            const stockClass = bajoStock ? 'warning' : 'success';
            const stockIcon = bajoStock ? 'exclamation-triangle' : 'check-circle';
            
            html += `
                <div class="producto-card">
                    <div class="producto-header">
                        <h4>${producto.nombre}</h4>
                        <span class="badge ${stockClass}">
                            <i class="fas fa-${stockIcon}"></i>
                            Stock: ${producto.stock_actual}
                        </span>
                    </div>
                    
                    <div class="producto-body">
                        <p><strong>Código:</strong> ${producto.codigo}</p>
                        <p><strong>Categoría:</strong> ${producto.categoria || 'Sin categoría'}</p>
                        <p><strong>Precio:</strong> $${producto.precio_unitario.toFixed(2)}</p>
                        <p><strong>Ubicación:</strong> ${producto.ubicacion || 'Sin ubicación'}</p>
                    </div>
                    
                    <div class="producto-actions">
                        <a href="/productos/${producto.id}" class="btn btn-sm btn-primary">
                            <i class="fas fa-eye"></i> Ver
                        </a>
                        <button onclick="generarQR(${producto.id})" class="btn btn-sm btn-secondary">
                            <i class="fas fa-qrcode"></i> QR
                        </button>
                        <button onclick="generarBarcode(${producto.id})" class="btn btn-sm btn-secondary">
                            <i class="fas fa-barcode"></i> Barras
                        </button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error cargando productos:', error);
    }
}

async function generarQR(productoId) {
    try {
        const resultado = await api.get(`/productos/${productoId}/qr-code`);
        
        const modal = crearModal(`
            <h3><i class="fas fa-qrcode"></i> Código QR del Producto</h3>
            <div class="qr-container">
                <img src="${resultado.qr_code}" alt="Código QR" class="qr-image">
                <p class="text-center">Escanea este código con tu celular</p>
            </div>
            <div class="modal-buttons">
                <button onclick="descargarImagen('${resultado.qr_code}', 'qr-producto.png')" 
                        class="btn btn-primary">
                    <i class="fas fa-download"></i> Descargar
                </button>
                <button onclick="cerrarModal()" class="btn btn-secondary">
                    <i class="fas fa-times"></i> Cerrar
                </button>
            </div>
        `);
        
        mostrarModal(modal);
        
    } catch (error) {
        mostrarError('Error generando código QR');
    }
}

async function generarBarcode(productoId) {
    try {
        const resultado = await api.get(`/productos/${productoId}/codigo-barras`);
        
        const modal = crearModal(`
            <h3><i class="fas fa-barcode"></i> Código de Barras</h3>
            <div class="barcode-container">
                <img src="${resultado.codigo_barras}" alt="Código de Barras" class="barcode-image">
                <p class="text-center">Código para escanear</p>
            </div>
            <div class="modal-buttons">
                <button onclick="descargarImagen('${resultado.codigo_barras}', 'barcode-producto.png')" 
                        class="btn btn-primary">
                    <i class="fas fa-download"></i> Descargar
                </button>
                <button onclick="cerrarModal()" class="btn btn-secondary">
                    <i class="fas fa-times"></i> Cerrar
                </button>
            </div>
        `);
        
        mostrarModal(modal);
        
    } catch (error) {
        mostrarError('Error generando código de barras');
    }
}

function descargarImagen(dataUrl, filename) {
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Exportar funciones globales
window.iniciarEscaneoPagina = iniciarEscaneoPagina;
window.detenerEscaneoPagina = detenerEscaneoPagina;
window.procesarCodigoEscaneado = procesarCodigoEscaneado;
window.registrarMovimiento = registrarMovimiento;
window.crearProductoDesdeCodigo = crearProductoDesdeCodigo;
window.cerrarModal = cerrarModal;
window.generarQR = generarQR;
window.generarBarcode = generarBarcode;
window.buscarProductoGlobal = buscarProductoGlobal;