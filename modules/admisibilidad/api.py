"""
Blueprint para el módulo admisibilidad
Endpoints para verificación de documentos
"""
from flask import Blueprint, request, jsonify
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Crear Blueprint
bp = Blueprint('admisibilidad', __name__)

# Importar funciones del módulo original
try:
    from . import verificador_admisibilidad
    logger.info("Funciones de admisibilidad importadas correctamente")
except ImportError as e:
    logger.error(f"Error importando funciones de admisibilidad: {e}")

# ============================================================================
# ENDPOINTS
# ============================================================================

@bp.route('/health', methods=['GET'])
def health():
    """Health check del módulo admisibilidad"""
    return jsonify({
        'module': 'admisibilidad',
        'status': 'healthy'
    }), 200

@bp.route('/verificar', methods=['POST'])
def verificar_documento():
    """
    Verifica la admisibilidad de un documento
    
    Parámetros:
    - file: archivo PDF (multipart/form-data)
    - tipo_documento: tipo de documento a verificar
    
    Retorna:
    - JSON con resultado de verificación
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        tipo_documento = request.form.get('tipo_documento', 'general')
        
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'El archivo debe ser PDF'}), 400
        
        # Guardar archivo temporal
        temp_path = Path('temp') / file.filename
        temp_path.parent.mkdir(exist_ok=True)
        file.save(str(temp_path))
        
        logger.info(f"Verificando admisibilidad de: {file.filename}")
        
        # Verificar (implementar según tu lógica original)
        # resultado = verificador_admisibilidad.verificar(str(temp_path), tipo_documento)
        
        # Por ahora retornamos estructura de ejemplo
        resultado = {
            'success': True,
            'filename': file.filename,
            'tipo_documento': tipo_documento,
            'admisible': True,
            'observaciones': [],
            'message': 'Verificación completa (implementar lógica específica)'
        }
        
        # Limpiar archivo temporal
        if temp_path.exists():
            temp_path.unlink()
        
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error verificando documento: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/extraer-datos', methods=['POST'])
def extraer_datos():
    """
    Extrae datos estructurados de un documento
    
    Parámetros:
    - file: archivo PDF (multipart/form-data)
    - campos: campos a extraer (JSON)
    
    Retorna:
    - JSON con datos extraídos
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        campos = request.form.get('campos', '[]')
        
        logger.info(f"Extrayendo datos de: {file.filename}")
        
        # Guardar archivo temporal
        temp_path = Path('temp') / file.filename
        temp_path.parent.mkdir(exist_ok=True)
        file.save(str(temp_path))
        
        # Extraer datos (implementar según tu lógica original)
        resultado = {
            'success': True,
            'filename': file.filename,
            'datos': {},
            'message': 'Extracción completa (implementar lógica específica)'
        }
        
        # Limpiar archivo temporal
        if temp_path.exists():
            temp_path.unlink()
        
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error extrayendo datos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/validar-campos', methods=['POST'])
def validar_campos():
    """
    Valida campos extraídos según reglas
    
    Parámetros:
    - datos: JSON con campos a validar
    - reglas: JSON con reglas de validación
    
    Retorna:
    - JSON con resultado de validación
    """
    try:
        datos = request.get_json()
        
        if not datos:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
        
        logger.info("Validando campos")
        
        # Validar (implementar según tu lógica original)
        resultado = {
            'success': True,
            'valido': True,
            'errores': [],
            'message': 'Validación completa (implementar lógica específica)'
        }
        
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Error validando campos: {str(e)}")
        return jsonify({'error': str(e)}), 500
