"""
PMO Python API - Servicio unificado
Combina módulos de bind-pdf y admisibilidad
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
from pathlib import Path

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Crear aplicación Flask
app = Flask(__name__)
CORS(app)

# Configuración
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', './temp')
app.config['MODEL_PATH'] = os.getenv('MODEL_PATH', './models/yolov8n.pt')

# Crear carpetas necesarias
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
Path('logs').mkdir(exist_ok=True)

# ============================================================================
# IMPORTAR MÓDULOS
# ============================================================================

try:
    # Módulo bind-pdf
    from modules.bind_pdf import api as bind_pdf_api
    logger.info("Módulo bind-pdf cargado correctamente")
except ImportError as e:
    logger.error(f"Error cargando módulo bind-pdf: {e}")
    bind_pdf_api = None

try:
    # Módulo admisibilidad
    from modules.admisibilidad import api as admisibilidad_api
    logger.info("Módulo admisibilidad cargado correctamente")
except ImportError as e:
    logger.error(f"Error cargando módulo admisibilidad: {e}")
    admisibilidad_api = None

# ============================================================================
# RUTAS PRINCIPALES
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'pmo-python-api',
        'modules': {
            'bind_pdf': bind_pdf_api is not None,
            'admisibilidad': admisibilidad_api is not None
        }
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Endpoint raíz con información del servicio"""
    return jsonify({
        'service': 'PMO Python API',
        'version': '1.0.0',
        'endpoints': {
            'bind-pdf': {
                'ocr': '/api/bind-pdf/ocr',
                'merge': '/api/bind-pdf/merge',
                'process': '/api/bind-pdf/process'
            },
            'admisibilidad': {
                'verificar': '/api/admisibilidad/verificar',
                'extraer-datos': '/api/admisibilidad/extraer-datos'
            }
        }
    }), 200

# ============================================================================
# REGISTRAR BLUEPRINTS
# ============================================================================

if bind_pdf_api:
    # Registrar rutas de bind-pdf
    app.register_blueprint(bind_pdf_api.bp, url_prefix='/api/bind-pdf')
    logger.info("Rutas de bind-pdf registradas en /api/bind-pdf")

if admisibilidad_api:
    # Registrar rutas de admisibilidad
    app.register_blueprint(admisibilidad_api.bp, url_prefix='/api/admisibilidad')
    logger.info("Rutas de admisibilidad registradas en /api/admisibilidad")

# ============================================================================
# MANEJO DE ERRORES
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint no encontrado',
        'message': str(error)
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Error interno del servidor: {error}")
    return jsonify({
        'error': 'Error interno del servidor',
        'message': str(error)
    }), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        'error': 'Archivo demasiado grande',
        'message': 'El tamaño máximo permitido es 50 MB'
    }), 413

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Iniciando servidor en puerto {port} (debug={debug})")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
