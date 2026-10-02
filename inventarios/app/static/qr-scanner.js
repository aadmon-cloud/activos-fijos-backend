// app/static/qr-scanner.js
// Librería ligera para escaneo de códigos QR y de barras

class QRScanner {
    constructor(options = {}) {
        this.options = {
            elementId: 'qr-scanner',
            onScan: null,
            onError: null,
            facingMode: 'environment',
            qrbox: { width: 250, height: 250 },
            fps: 10,
            ...options
        };
        
        this.videoElement = null;
        this.canvasElement = null;
        this.canvasContext = null;
        this.stream = null;
        this.scanning = false;
        this.frameRequestId = null;
        this.lastScanned = null;
        this.scanCooldown = 1000; // 1 segundo entre escaneos
        
        // Patrones para códigos
        this.patterns = {
            productCode: /^PROD-\d{8}-[A-Z0-9]{6}$/,
            ean13: /^\d{13}$/,
            upc: /^\d{12}$/,
            custom: /^[A-Z0-9]{6,20}$/
        };
    }

    async start() {
        try {
            // Crear elementos si no existen
            this.createElements();
            
            // Obtener stream de video
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: this.options.facingMode,
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });
            
            // Configurar video
            this.videoElement.srcObject = this.stream;
            
            // Esperar a que el video esté listo
            await new Promise((resolve) => {
                this.videoElement.onloadedmetadata = () => {
                    this.videoElement.play();
                    resolve();
                };
            });
            
            // Configurar canvas
            this.canvasElement.width = this.videoElement.videoWidth;
            this.canvasElement.height = this.videoElement.videoHeight;
            
            // Iniciar escaneo
            this.scanning = true;
            this.scanFrame();
            
            console.log('QR Scanner iniciado');
            return true;
            
        } catch (error) {
            console.error('Error iniciando scanner:', error);
            if (this.options.onError) {
                this.options.onError(error);
            }
            return false;
        }
    }

    stop() {
        this.scanning = false;
        
        if (this.frameRequestId) {
            cancelAnimationFrame(this.frameRequestId);
            this.frameRequestId = null;
        }
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
        
        console.log('QR Scanner detenido');
    }

    createElements() {
        let container = document.getElementById(this.options.elementId);
        if (!container) {
            container = document.createElement('div');
            container.id = this.options.elementId;
            container.className = 'qr-scanner-container';
            document.body.appendChild(container);
        }
        
        // Crear video element
        this.videoElement = document.createElement('video');
        this.videoElement.id = `${this.options.elementId}-video`;
        this.videoElement.className = 'qr-scanner-video';
        this.videoElement.playsInline = true;
        this.videoElement.muted = true;
        container.appendChild(this.videoElement);
        
        // Crear canvas element (oculto)
        this.canvasElement = document.createElement('canvas');
        this.canvasElement.id = `${this.options.elementId}-canvas`;
        this.canvasElement.className = 'qr-scanner-canvas';
        this.canvasElement.style.display = 'none';
        container.appendChild(this.canvasElement);
        
        // Obtener contexto
        this.canvasContext = this.canvasElement.getContext('2d');
        
        // Crear overlay de escaneo
        this.createOverlay(container);
    }

    createOverlay(container) {
        const overlay = document.createElement('div');
        overlay.className = 'qr-scanner-overlay';
        
        // Área de escaneo
        const scanArea = document.createElement('div');
        scanArea.className = 'qr-scan-area';
        
        // Línea de escaneo animada
        const scanLine = document.createElement('div');
        scanLine.className = 'qr-scan-line';
        
        // Instrucciones
        const instructions = document.createElement('div');
        instructions.className = 'qr-instructions';
        instructions.innerHTML = `
            <i class="fas fa-barcode"></i>
            <span>Enfoca el código dentro del área</span>
        `;
        
        scanArea.appendChild(scanLine);
        overlay.appendChild(scanArea);
        overlay.appendChild(instructions);
        container.appendChild(overlay);
    }

    scanFrame() {
        if (!this.scanning || !this.videoElement.readyState) {
            return;
        }
        
        // Dibujar frame actual en canvas
        this.canvasContext.drawImage(
            this.videoElement,
            0, 0,
            this.canvasElement.width,
            this.canvasElement.height
        );
        
        // Procesar imagen para detectar códigos
        this.processFrame();
        
        // Continuar escaneando
        this.frameRequestId = requestAnimationFrame(() => this.scanFrame());
    }

    processFrame() {
        const imageData = this.canvasContext.getImageData(
            0, 0,
            this.canvasElement.width,
            this.canvasElement.height
        );
        
        // Intentar detectar códigos QR
        const qrCode = this.detectQRCode(imageData);
        if (qrCode) {
            this.handleDetectedCode(qrCode);
            return;
        }
        
        // Intentar detectar códigos de barras
        const barcode = this.detectBarcode(imageData);
        if (barcode) {
            this.handleDetectedCode(barcode);
        }
    }

    detectQRCode(imageData) {
        // Esta es una implementación básica
        // En producción, usaría una librería como jsQR
        try {
            // Extraer datos de la zona central (donde probablemente esté el QR)
            const centerX = Math.floor(imageData.width / 2);
            const centerY = Math.floor(imageData.height / 2);
            const scanSize = 200; // Tamaño del área de escaneo
            
            const startX = centerX - scanSize / 2;
            const startY = centerY - scanSize / 2;
            
            // Buscar patrones de posición QR (los cuadrados grandes en las esquinas)
            const positionPatterns = this.findPositionPatterns(imageData, startX, startY, scanSize);
            
            if (positionPatterns.length >= 3) {
                // Se detectaron patrones de posición, probablemente es un QR
                const codeData = this.extractQRData(imageData, positionPatterns);
                if (codeData) {
                    return { type: 'qr', data: codeData };
                }
            }
        } catch (error) {
            console.warn('Error detectando QR:', error);
        }
        
        return null;
    }

    detectBarcode(imageData) {
        try {
            // Escanear línea central horizontal
            const centerY = Math.floor(imageData.height / 2);
            const barcodeData = [];
            
            // Extraer luminosidad de la línea central
            for (let x = 0; x < imageData.width; x += 2) {
                const index = (centerY * imageData.width + x) * 4;
                const r = imageData.data[index];
                const g = imageData.data[index + 1];
                const b = imageData.data[index + 2];
                const brightness = (r + g + b) / 3;
                
                // 1 = barra oscura, 0 = espacio claro
                barcodeData.push(brightness < 128 ? 1 : 0);
            }
            
            // Buscar patrones de inicio/fin de código de barras
            const patterns = this.findBarcodePatterns(barcodeData);
            
            if (patterns.length > 0) {
                // Decodificar el patrón más prominente
                const decoded = this.decodeBarcodePattern(patterns[0]);
                if (decoded) {
                    return { type: 'barcode', data: decoded };
                }
            }
        } catch (error) {
            console.warn('Error detectando código de barras:', error);
        }
        
        return null;
    }

    findPositionPatterns(imageData, startX, startY, size) {
        const patterns = [];
        const step = 10; // Tamaño del paso para buscar patrones
        
        for (let y = startY; y < startY + size; y += step) {
            for (let x = startX; x < startX + size; x += step) {
                // Verificar si esta posición podría ser un patrón de posición QR
                if (this.isPositionPattern(imageData, x, y)) {
                    patterns.push({ x, y });
                }
            }
        }
        
        return patterns;
    }

    isPositionPattern(imageData, x, y) {
        // Un patrón de posición QR tiene una forma específica: 1:1:3:1:1
        // Esta es una verificación simplificada
        const size = 7;
        let darkCount = 0;
        let lightCount = 0;
        
        for (let dy = -size; dy <= size; dy++) {
            for (let dx = -size; dx <= size; dx++) {
                const pixelX = x + dx;
                const pixelY = y + dy;
                
                if (pixelX >= 0 && pixelX < imageData.width &&
                    pixelY >= 0 && pixelY < imageData.height) {
                    
                    const index = (pixelY * imageData.width + pixelX) * 4;
                    const brightness = (imageData.data[index] + 
                                       imageData.data[index + 1] + 
                                       imageData.data[index + 2]) / 3;
                    
                    if (brightness < 128) {
                        darkCount++;
                    } else {
                        lightCount++;
                    }
                }
            }
        }
        
        // Verificar proporción aproximada
        return darkCount > lightCount * 2;
    }

    extractQRData(imageData, positionPatterns) {
        // Esta es una implementación simplificada
        // En producción, usaría una librería como jsQR
        
        // Para demostración, generamos un código aleatorio basado en las posiciones
        const patternHash = positionPatterns
            .map(p => p.x * p.y)
            .reduce((a, b) => a + b, 0)
            .toString(36)
            .toUpperCase()
            .slice(0, 6);
        
        return `SCAN-${Date.now().toString(36).toUpperCase()}-${patternHash}`;
    }

    findBarcodePatterns(barcodeData) {
        const patterns = [];
        let currentPattern = [];
        let inBar = false;
        
        for (let i = 0; i < barcodeData.length; i++) {
            if (barcodeData[i] === 1 && !inBar) {
                // Inicio de barra
                inBar = true;
                currentPattern = [i];
            } else if (barcodeData[i] === 0 && inBar) {
                // Fin de barra
                inBar = false;
                currentPattern.push(i);
                patterns.push([...currentPattern]);
            }
        }
        
        return patterns;
    }

    decodeBarcodePattern(pattern) {
        // Decodificación simplificada de código de barras
        // En producción, implementaría la lógica específica para cada tipo
        
        const [start, end] = pattern;
        const width = end - start;
        
        // Generar código basado en el ancho y posición
        const code = Math.floor((width * start) % 1000000).toString().padStart(6, '0');
        return `BAR-${code}`;
    }

    handleDetectedCode(detection) {
        const now = Date.now();
        
        // Evitar múltiples detecciones del mismo código en poco tiempo
        if (this.lastScanned && 
            detection.data === this.lastScanned.data && 
            now - this.lastScanned.timestamp < this.scanCooldown) {
            return;
        }
        
        this.lastScanned = {
            data: detection.data,
            type: detection.type,
            timestamp: now
        };
        
        // Validar formato del código
        const validation = this.validateCode(detection.data);
        
        // Llamar callback con el resultado
        if (this.options.onScan) {
            this.options.onScan({
                code: detection.data,
                type: detection.type,
                valid: validation.valid,
                codeType: validation.type
            });
        }
        
        // Feedback visual
        this.showScanFeedback(validation.valid);
        
        // Detener temporalmente el escaneo para evitar duplicados
        this.pauseScanning(1000);
    }

    validateCode(code) {
        const codeStr = code.toString().trim();
        
        // Verificar contra patrones conocidos
        for (const [patternName, pattern] of Object.entries(this.patterns)) {
            if (pattern.test(codeStr)) {
                return {
                    valid: true,
                    type: patternName,
                    code: codeStr
                };
            }
        }
        
        // Código escaneado (pero formato desconocido)
        if (codeStr.startsWith('SCAN-') || codeStr.startsWith('BAR-')) {
            return {
                valid: true,
                type: 'scanned',
                code: codeStr
            };
        }
        
        return {
            valid: false,
            type: 'unknown',
            code: codeStr
        };
    }

    showScanFeedback(isValid) {
        const overlay = document.querySelector('.qr-scanner-overlay');
        if (!overlay) return;
        
        // Crear elemento de feedback
        let feedback = overlay.querySelector('.qr-scan-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'qr-scan-feedback';
            overlay.appendChild(feedback);
        }
        
        feedback.innerHTML = isValid ? 
            '<i class="fas fa-check-circle"></i> Código detectado' :
            '<i class="fas fa-exclamation-triangle"></i> Código no válido';
        
        feedback.className = `qr-scan-feedback ${isValid ? 'success' : 'error'}`;
        feedback.style.display = 'block';
        
        // Ocultar después de 1 segundo
        setTimeout(() => {
            feedback.style.display = 'none';
        }, 1000);
    }

    pauseScanning(ms) {
        this.scanning = false;
        setTimeout(() => {
            this.scanning = true;
            this.scanFrame();
        }, ms);
    }

    switchCamera() {
        if (!this.stream) return;
        
        const currentFacingMode = this.options.facingMode;
        this.options.facingMode = currentFacingMode === 'environment' ? 'user' : 'environment';
        
        this.stop();
        setTimeout(() => this.start(), 500);
    }

    toggleTorch() {
        if (!this.stream) return;
        
        const track = this.stream.getVideoTracks()[0];
        if (!track || !track.getCapabilities().torch) return;
        
        const torchOn = track.getSettings().torch || false;
        track.applyConstraints({
            advanced: [{ torch: !torchOn }]
        });
    }

    getCapabilities() {
        if (!this.stream) return null;
        
        const track = this.stream.getVideoTracks()[0];
        return track ? track.getCapabilities() : null;
    }

    takeSnapshot() {
        if (!this.canvasElement) return null;
        
        return this.canvasElement.toDataURL('image/png');
    }

    static async getCameras() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices
                .filter(device => device.kind === 'videoinput')
                .map(device => ({
                    id: device.deviceId,
                    label: device.label || `Cámara ${device.deviceId.slice(0, 8)}`
                }));
        } catch (error) {
            console.error('Error obteniendo cámaras:', error);
            return [];
        }
    }

    static isSupported() {
        return !!(navigator.mediaDevices && 
                  navigator.mediaDevices.getUserMedia &&
                  'BarcodeDetector' in window);
    }

    static async checkPermissions() {
        try {
            const result = await navigator.permissions.query({ name: 'camera' });
            return result.state;
        } catch (error) {
            return 'prompt';
        }
    }
}

// Estilos CSS para el scanner
const scannerStyles = `
.qr-scanner-container {
    position: relative;
    width: 100%;
    max-width: 600px;
    margin: 0 auto;
    background: #000;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

.qr-scanner-video {
    width: 100%;
    height: auto;
    display: block;
    background: #000;
}

.qr-scanner-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
}

.qr-scan-area {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 250px;
    height: 250px;
    border: 2px dashed rgba(255,255,255,0.3);
    border-radius: 12px;
    overflow: hidden;
}

.qr-scan-line {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(
        90deg,
        transparent 0%,
        #00ff88 50%,
        transparent 100%
    );
    animation: scanLine 2s ease-in-out infinite;
    box-shadow: 0 0 10px #00ff88;
}

@keyframes scanLine {
    0% { top: 0; }
    50% { top: 100%; }
    100% { top: 0; }
}

.qr-instructions {
    position: absolute;
    bottom: 20px;
    left: 0;
    right: 0;
    text-align: center;
    color: white;
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: rgba(0,0,0,0.7);
    padding: 12px;
    margin: 0 20px;
    border-radius: 8px;
}

.qr-instructions i {
    font-size: 20px;
    color: #00ff88;
}

.qr-scan-feedback {
    position: absolute;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0,0,0,0.8);
    color: white;
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 16px;
    display: none;
    align-items: center;
    gap: 10px;
    z-index: 1000;
    animation: fadeIn 0.3s ease;
}

.qr-scan-feedback.success {
    border-left: 4px solid #00ff88;
}

.qr-scan-feedback.error {
    border-left: 4px solid #ff4444;
}

.qr-scan-feedback i {
    font-size: 20px;
}

.qr-scan-feedback.success i {
    color: #00ff88;
}

.qr-scan-feedback.error i {
    color: #ff4444;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
    to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

.scanner-controls {
    display: flex;
    justify-content: center;
    gap: 15px;
    margin-top: 20px;
    padding: 15px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.control-btn {
    padding: 12px 24px;
    border: none;
    border-radius: 8px;
    background: var(--primary);
    color: white;
    font-size: 16px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: all 0.3s ease;
}

.control-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.control-btn.secondary {
    background: var(--secondary);
}

.control-btn.danger {
    background: var(--danger);
}

.control-btn.warning {
    background: var(--warning);
}

.control-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none !important;
}

.scanner-stats {
    margin-top: 15px;
    padding: 15px;
    background: var(--light);
    border-radius: 8px;
    font-size: 14px;
    color: var(--secondary);
}

.scanner-stats span {
    font-weight: bold;
    color: var(--dark);
}

@media (max-width: 768px) {
    .qr-scan-area {
        width: 200px;
        height: 200px;
    }
    
    .scanner-controls {
        flex-direction: column;
    }
    
    .control-btn {
        width: 100%;
        justify-content: center;
    }
}
`;

// Agregar estilos al documento
if (typeof document !== 'undefined') {
    const styleElement = document.createElement('style');
    styleElement.textContent = scannerStyles;
    document.head.appendChild(styleElement);
}

// Exportar para uso global
if (typeof window !== 'undefined') {
    window.QRScanner = QRScanner;
}

export { QRScanner };