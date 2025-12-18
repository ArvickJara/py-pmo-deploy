"""
Blueprint para el módulo bind-pdf
Endpoints para procesamiento OCR y unión de PDFs
"""
from flask import Blueprint, request, jsonify, send_file
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Crear Blueprint
bp = Blueprint('bind_pdf', __name__)

# Importar funciones del módulo core
try:
    from . import core
    logger.info("Módulo core de bind-pdf importado correctamente")
    
    # Inicializar el modelo al cargar el módulo
    try:
        core.initialize_model()
        logger.info(f"Modelo {core.MODEL_TYPE} inicializado correctamente")
    except Exception as e:
        logger.error(f"Error inicializando modelo: {e}")
except ImportError as e:
    logger.error(f"Error importando módulo core: {e}")
    core = None

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

@bp.route('/process-pdf', methods=['POST'])
def process_pdf():
    """
    Procesa un PDF completo: convierte páginas, ejecuta YOLO+OCR, compara foliación
    
    Parámetros (query):
    - dpi: DPI para conversión de páginas (default: 300)
    - imgsz: Tamaño de imagen para YOLO (default: 512)
    - conf: Confianza mínima de detección (default: 0.25)
    - min_confidence: Confianza mínima para procesar OCR (default: 0.5)
    - ocr: Si true, ejecuta OCR en cada detección (default: true)
    - digits_only: Modo numérico para foliación (default: true)
    - digits_engine: Motor OCR (default: "auto")
    - digits_preprocess: Preprocesamiento (default: "strong")
    - pad_ratio: Ratio de padding (default: 0.15)
    
    Retorna:
    - JSON con resultados por página y resumen
    """
    if not core:
        return jsonify({'error': 'Módulo core no disponible'}), 500
    
    try:
        # Validar archivo
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo PDF'}), 400
        
        file = request.files['file']
        
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Debe ser un archivo PDF válido'}), 400
        
        # Leer parámetros de query
        dpi = int(request.args.get('dpi', 300))
        imgsz = int(request.args.get('imgsz', 512))
        conf = float(request.args.get('conf', 0.25))
        min_confidence = float(request.args.get('min_confidence', 0.5))
        ocr = request.args.get('ocr', 'true').lower() == 'true'
        digits_only = request.args.get('digits_only', 'true').lower() == 'true'
        digits_engine = request.args.get('digits_engine', 'auto')
        digits_preprocess = request.args.get('digits_preprocess', 'strong')
        pad_ratio = float(request.args.get('pad_ratio', 0.15))
        
        logger.info(f"Procesando PDF: {file.filename} (dpi={dpi}, ocr={ocr}, digits_only={digits_only})")
        
        # Leer contenido del PDF
        pdf_data = file.read()
        if not pdf_data:
            return jsonify({'error': 'Archivo vacío'}), 400
        
        # Convertir PDF a imágenes
        try:
            pages = core.pdf_to_images(pdf_data, dpi=dpi)
        except Exception as e:
            logger.error(f"Error convirtiendo PDF: {str(e)}")
            return jsonify({'error': f'Error al convertir PDF: {str(e)}'}), 500
        
        results = []
        
        # Procesar cada página
        for page_num, img in pages:
            try:
                # Ejecutar detección YOLO
                predictions = core.predict_array(img, imgsz=imgsz, conf=conf)
                
                # Filtrar detecciones de baja confianza
                for pred in predictions:
                    if pred.get("confidence", 0) < min_confidence:
                        pred["low_confidence"] = True
                        pred["ocr_skipped"] = "Confianza por debajo del umbral mínimo"
                
                # Solo aplicar OCR a detecciones con confianza suficiente
                high_conf_predictions = [p for p in predictions if not p.get("low_confidence", False)]
                
                extra_payload: Dict[str, Any] = {}
                
                if ocr and high_conf_predictions:
                    if digits_only:
                        try:
                            engine = (digits_engine or "auto").lower()
                            pre = (digits_preprocess or "strong").lower()
                            if pre == "none":
                                pre = "light"
                            
                            engine_errors = core._apply_digits_engines(
                                img,
                                high_conf_predictions,
                                pad_ratio=pad_ratio,
                                preprocess=pre,
                                preferred_engine=engine,
                            )
                            
                            if engine_errors:
                                extra_payload["digits_engine_errors"] = engine_errors
                            
                            # Fallback a OCR general si no hay dígitos
                            if any(not p.get("ocr_digits") for p in high_conf_predictions):
                                try:
                                    core.enrich_with_ocr(img, high_conf_predictions)
                                    for p in high_conf_predictions:
                                        if not p.get("ocr_digits"):
                                            p["ocr_digits"] = core._normalize_to_digits(p.get("ocr_text", ""))
                                except Exception:
                                    pass
                        except Exception as e_ocr:
                            logger.warning(f"Error en OCR de dígitos: {str(e_ocr)}")
                            try:
                                core.enrich_with_ocr(img, high_conf_predictions)
                                for p in high_conf_predictions:
                                    p["ocr_digits"] = core._normalize_to_digits(p.get("ocr_text", ""))
                            except Exception:
                                core._ensure_empty_ocr_fields(high_conf_predictions)
                                for p in high_conf_predictions:
                                    p["ocr_digits"] = ""
                        
                        core._strip_textual_ocr_fields(high_conf_predictions)
                    else:
                        # OCR general (no solo dígitos)
                        try:
                            core.enrich_with_ocr(img, high_conf_predictions)
                        except Exception as ocr_err:
                            core._ensure_empty_ocr_fields(high_conf_predictions)
                            extra_payload["ocr_error"] = str(ocr_err)
                
                # Comparar foliación
                for pred in predictions:
                    if digits_only and "ocr_digits" in pred:
                        pred["foliation_check"] = core.compare_foliation(pred["ocr_digits"], page_num)
                
                page_result = {
                    "page_number": page_num,
                    "predictions": predictions,
                }
                
                if extra_payload:
                    page_result.update(extra_payload)
                
                results.append(page_result)
                
            except Exception as page_err:
                logger.error(f"Error procesando página {page_num}: {str(page_err)}")
                results.append({
                    "page_number": page_num,
                    "error": str(page_err),
                    "predictions": []
                })
        
        # Calcular resumen
        total_detections = sum(len(r.get("predictions", [])) for r in results)
        pages_with_detections = sum(1 for r in results if len(r.get("predictions", [])) > 0)
        exact_matches = sum(
            1 for r in results 
            for p in r.get("predictions", [])
            if p.get("foliation_check", {}).get("match", False)
        )
        pages_without_match = len(pages) - exact_matches
        
        # Calcular confianza promedio
        all_confidences = [
            p.get("confidence", 0) 
            for r in results 
            for p in r.get("predictions", [])
        ]
        average_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        
        # Agregar dimensiones de imagen al resultado
        if results and len(pages) > 0:
            _, first_img = pages[0]
            h, w = first_img.shape[:2]
            for result in results:
                result["image_dimensions"] = {"width": w, "height": h}
        
        return jsonify({
            "pages": results,
            "summary": {
                "total_pages": len(pages),
                "total_detections": total_detections,
                "pages_with_detections": pages_with_detections,
                "exact_matches": exact_matches,
                "pages_without_match": pages_without_match,
                "average_confidence": round(average_confidence, 3)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error en process-pdf: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
