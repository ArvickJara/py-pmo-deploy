"""
Blueprint para el módulo bind-pdf
Endpoints para procesamiento OCR y unión de PDFs
"""
from flask import Blueprint, request, jsonify, send_file
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Crear Blueprint
bp = Blueprint('bind_pdf', __name__)

# Importar funciones del módulo original
try:
    from . import ocr_from_pdf
    from . import pdf_to_images
    from . import draw_boxes
    from . import unir_pdfs
    logger.info("Funciones de bind-pdf importadas correctamente")
except ImportError as e:
    logger.error(f"Error importando funciones de bind-pdf: {e}")

# ============================================================================
# ENDPOINTS
# ============================================================================

@bp.route('/health', methods=['GET'])
def health():
    """Health check del módulo bind-pdf"""
    return jsonify({
        'module': 'bind-pdf',
        'status': 'healthy'
    }), 200

@bp.route('/ocr', methods=['POST'])
def process_ocr():
    """
    Procesa un PDF con OCR para extraer tablas
    
    Parámetros:
    - file: archivo PDF (multipart/form-data)
    
    Retorna:
    - JSON con datos extraídos de las tablas
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'El archivo debe ser PDF'}), 400
        
        # Guardar archivo temporal
        temp_path = Path('temp') / file.filename
        temp_path.parent.mkdir(exist_ok=True)
        file.save(str(temp_path))
        
        logger.info(f"Procesando OCR para: {file.filename}")
        
        # Procesar OCR (implementar según tu lógica original)
        # resultado = ocr_from_pdf.procesar_pdf(str(temp_path))
        
        # Por ahora retornamos estructura de ejemplo
        resultado = {
            'success': True,
            'filename': file.filename,
            'message': 'OCR procesado (implementar lógica específica)'
        }
        
        # Limpiar archivo temporal
        if temp_path.exists():
            temp_path.unlink()
        
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error en OCR: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/merge', methods=['POST'])
def merge_pdfs():
    """
    Une múltiples PDFs en uno solo
    
    Parámetros:
    - files: lista de archivos PDF (multipart/form-data)
    
    Retorna:
    - Archivo PDF unificado
    """
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No se proporcionaron archivos'}), 400
        
        files = request.files.getlist('files')
        
        if len(files) < 2:
            return jsonify({'error': 'Se requieren al menos 2 archivos'}), 400
        
        # Guardar archivos temporales
        temp_paths = []
        for file in files:
            if file.filename and file.filename.lower().endswith('.pdf'):
                temp_path = Path('temp') / file.filename
                file.save(str(temp_path))
                temp_paths.append(str(temp_path))
        
        if len(temp_paths) < 2:
            return jsonify({'error': 'Al menos 2 archivos válidos requeridos'}), 400
        
        logger.info(f"Uniendo {len(temp_paths)} PDFs")
        
        # Unir PDFs (implementar según tu lógica original)
        # output_path = unir_pdfs.unir(temp_paths)
        
        # Por ahora retornamos estructura de ejemplo
        resultado = {
            'success': True,
            'files_merged': len(temp_paths),
            'message': 'PDFs unidos (implementar lógica específica)'
        }
        
        # Limpiar archivos temporales
        for path in temp_paths:
            Path(path).unlink(missing_ok=True)
        
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error uniendo PDFs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/process', methods=['POST'])
def process_full():
    """
    Proceso completo: OCR + unión de PDFs
    
    Parámetros:
    - file: archivo PDF
    - operations: lista de operaciones a realizar
    
    Retorna:
    - Archivo procesado y datos extraídos
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        operations = request.form.get('operations', 'ocr').split(',')
        
        logger.info(f"Procesando {file.filename} con operaciones: {operations}")
        
        resultado = {
            'success': True,
            'filename': file.filename,
            'operations': operations,
            'message': 'Proceso completo (implementar lógica específica)'
        }
        
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error en proceso completo: {str(e)}")
        return jsonify({'error': str(e)}), 500
