"""
Módulo core para bind-pdf
Contiene todas las funciones esenciales de detección YOLO y OCR
"""
import os
import io
import uuid
import re
import cv2
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from PIL import Image

# Variables globales para caching de modelos
_ocr_pipeline = None
_easyocr_reader = None
_trocr_bundle = None
_donut_pipeline = None
_donut_error: Optional[str] = None

# Configuración del modelo
MODEL_ID = os.getenv("MODEL_ID", "foliacionpdf-u6br4/2")
# Path relativo al proyecto python-deploy
DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "models",
    "yolov8n.pt"
)
MODEL_PATH = os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH if os.path.exists(DEFAULT_MODEL_PATH) else None)
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "IkzCz5uodkvvJigVmhen")
MODEL_TYPE = None
model = None

def initialize_model():
    """Inicializa el modelo YOLO (Roboflow o Ultralytics)"""
    global model, MODEL_TYPE
    
    if MODEL_PATH:
        # Usar ultralytics local
        try:
            from ultralytics import YOLO
            model = YOLO(MODEL_PATH)
            MODEL_TYPE = "ultralytics"
            return True
        except Exception as e:
            raise RuntimeError(f"No se pudo cargar el modelo ultralytics: {MODEL_PATH}. {e}")
    else:
        # Usar Roboflow HTTP API
        try:
            from inference_sdk import InferenceHTTPClient
            model = InferenceHTTPClient(
                api_url="https://detect.roboflow.com",
                api_key=ROBOFLOW_API_KEY
            )
            MODEL_TYPE = "roboflow"
            return True
        except Exception as e:
            raise RuntimeError(f"No se pudo crear el cliente Roboflow HTTP: {e}")

def _get_ocr_pipeline():
    """Obtiene o crea la pipeline de keras-ocr"""
    global _ocr_pipeline
    if _ocr_pipeline is None:
        try:
            import keras_ocr
        except Exception as e:
            raise RuntimeError(
                "keras-ocr no está instalado. Instala con `pip install keras-ocr`"
            ) from e
        try:
            keras_ocr.config.configure()
        except Exception:
            pass
        _ocr_pipeline = keras_ocr.pipeline.Pipeline()
    return _ocr_pipeline

def _get_easyocr_reader():
    """Obtiene o crea el reader de EasyOCR"""
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
        except Exception as e:
            raise RuntimeError(
                "EasyOCR no está instalado. Instala con `pip install easyocr`"
            ) from e
        _easyocr_reader = easyocr.Reader(["en"], gpu=False)
    return _easyocr_reader

def pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> List[Tuple[int, np.ndarray]]:
    """Convierte PDF a lista de (page_num, np.ndarray RGB)"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PyMuPDF no instalado. Ejecuta: pip install pymupdf")
    
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zoom = dpi / 72.0
    pages = []
    
    for page_index in range(len(doc)):
        page = doc[page_index]
        m = fitz.Matrix(zoom, zoom)
        m = m.prerotate(page.rotation or 0) if hasattr(m, "prerotate") else m.preRotate(page.rotation or 0)
        pix = page.get_pixmap(matrix=m, alpha=False)
        pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append((page_index + 1, np.array(pil_img)))
    
    doc.close()
    return pages

def compare_foliation(ocr_digits: str, page_num: int) -> Dict[str, Any]:
    """Compara el dígito OCR con el número de página"""
    if not ocr_digits:
        return {"match": False, "diff": None, "confidence": 0.0, "match_percentage": 0}
    
    try:
        detected = int(ocr_digits)
    except ValueError:
        return {"match": False, "diff": None, "confidence": 0.0, "match_percentage": 0}
    
    diff = abs(detected - page_num)
    match = (diff == 0)
    
    if diff == 0:
        confidence = 1.0
        match_percentage = 100
    elif diff == 1:
        confidence = 0.8
        match_percentage = 80
    elif diff <= 3:
        confidence = 0.5
        match_percentage = 50
    else:
        confidence = max(0.0, 1.0 - (diff / 10.0))
        match_percentage = max(0, int(confidence * 100))
    
    return {
        "match": match,
        "diff": diff,
        "confidence": round(confidence, 2),
        "match_percentage": match_percentage
    }

def predict_array(img: np.ndarray, imgsz: int, conf: float) -> List[Dict[str, Any]]:
    """Ejecuta detección YOLO en una imagen"""
    if model is None:
        initialize_model()
    
    preds = []
    
    if MODEL_TYPE == "ultralytics":
        # Ultralytics YOLO local
        results = model.predict(source=[img], imgsz=imgsz, conf=conf, verbose=False)
        if not results:
            return []
        
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return preds
        
        xywh = r.boxes.xywh.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy().tolist()
        cls_ids = r.boxes.cls.cpu().numpy().astype(int).tolist()
        
        for i, (cx, cy, w, h) in enumerate(xywh):
            class_id = cls_ids[i]
            class_name = model.names.get(class_id, str(class_id)) if hasattr(model, "names") else str(class_id)
            preds.append({
                "x": float(cx),
                "y": float(cy),
                "width": float(w),
                "height": float(h),
                "confidence": round(float(confs[i]), 3),
                "class": class_name,
                "class_id": int(class_id),
                "detection_id": str(uuid.uuid4())
            })
    else:
        # Roboflow HTTP API
        pil_img = Image.fromarray(img)
        result = model.infer(pil_img, model_id=MODEL_ID)
        
        if not result or "predictions" not in result or not result["predictions"]:
            return []
        
        for pred in result["predictions"]:
            preds.append({
                "x": float(pred["x"]),
                "y": float(pred["y"]),
                "width": float(pred["width"]),
                "height": float(pred["height"]),
                "confidence": round(float(pred["confidence"]), 3),
                "class": str(pred.get("class", pred.get("class_id", "unknown"))),
                "class_id": int(pred.get("class_id", 0)),
                "detection_id": str(uuid.uuid4())
            })
    
    return preds

def _box_xywh_to_xyxy(box: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """Convierte de formato YOLO (centro x,y, ancho, alto) a (x1, y1, x2, y2)"""
    cx = box["x"]
    cy = box["y"]
    w = box["width"]
    h = box["height"]
    x1 = cx - w / 2.0
    y1 = cy - h / 2.0
    x2 = cx + w / 2.0
    y2 = cy + h / 2.0
    return x1, y1, x2, y2

def _word_center(word_box: np.ndarray) -> Tuple[float, float]:
    """Calcula el centro de una palabra detectada por OCR"""
    xs = word_box[:, 0]
    ys = word_box[:, 1]
    return float(xs.mean()), float(ys.mean())

def _clip(val: float, lo: float, hi: float) -> float:
    """Limita un valor entre min y max"""
    return max(lo, min(hi, val))

def _crop_with_pad(img: np.ndarray, box: Dict[str, Any], pad_ratio: float = 0.15) -> np.ndarray:
    """Recorta la imagen alrededor de una detección con padding"""
    h, w = img.shape[:2]
    cx, cy, bw, bh = box["x"], box["y"], box["width"], box["height"]
    px = bw * pad_ratio
    py = bh * pad_ratio
    x1 = _clip(cx - bw / 2 - px, 0, w - 1)
    y1 = _clip(cy - bh / 2 - py, 0, h - 1)
    x2 = _clip(cx + bw / 2 + px, 0, w - 1)
    y2 = _clip(cy + bh / 2 + py, 0, h - 1)
    x1i, y1i, x2i, y2i = map(lambda v: int(round(v)), (x1, y1, x2, y2))
    if x2i <= x1i or y2i <= y1i:
        return img[0:0, 0:0]
    return img[y1i:y2i, x1i:x2i]

def _preprocess_crop(crop: np.ndarray, mode: str = "strong") -> np.ndarray:
    """Preprocesa un recorte para mejorar OCR"""
    if crop.size == 0:
        return crop
    
    try:
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    except Exception:
        if len(crop.shape) == 2:
            gray = crop
        else:
            gray = crop[..., 0]
    
    scale = 2 if mode == "light" else 3
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    if mode == "light":
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    else:
        blur = cv2.bilateralFilter(gray, 5, 50, 50)
        th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, 15, 3)
    
    return cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)

def enrich_with_ocr(img: np.ndarray, predictions: List[Dict[str, Any]]) -> None:
    """Añade texto OCR a cada predicción usando keras-ocr"""
    pipeline = _get_ocr_pipeline()
    try:
        ocr_groups = pipeline.recognize([img])
        words = ocr_groups[0] if (ocr_groups and len(ocr_groups) > 0) else []
    except Exception:
        words = []
    
    for pred in predictions:
        x1, y1, x2, y2 = _box_xywh_to_xyxy(pred)
        inside_words = []
        for w_text, w_box in words:
            cx, cy = _word_center(np.array(w_box))
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                inside_words.append((w_text, w_box))
        
        inside_words.sort(key=lambda wb: (_word_center(np.array(wb[1]))[1], _word_center(np.array(wb[1]))[0]))
        pred["ocr_words"] = [w for w, _ in inside_words]
        pred["ocr_text"] = " ".join(pred["ocr_words"]) if pred["ocr_words"] else ""

def _normalize_to_digits(text: str) -> str:
    """Normaliza texto a solo dígitos"""
    if not text:
        return ""
    
    m = {
        "O": "0", "o": "0", "D": "0", "Q": "0",
        "I": "1", "l": "1", "|": "1", "!": "1",
        "Z": "2",
        "E": "3",
        "A": "4",
        "S": "5", "s": "5",
        "G": "6",
        "T": "7",
        "B": "8",
        "g": "9", "q": "9",
    }
    normalized = "".join(m.get(ch, ch) for ch in text)
    return re.sub(r"\D", "", normalized)

def ocr_digits_easyocr(img: np.ndarray, predictions: List[Dict[str, Any]], 
                       pad_ratio: float = 0.15, preprocess: str = "strong") -> None:
    """OCR para dígitos usando EasyOCR"""
    reader = _get_easyocr_reader()
    for pred in predictions:
        crop = _crop_with_pad(img, pred, pad_ratio=pad_ratio)
        crop = _preprocess_crop(crop, mode=preprocess)
        if crop.size == 0:
            pred["ocr_words"] = []
            pred["ocr_text"] = ""
            pred["ocr_digits"] = ""
            continue
        
        try:
            words = reader.readtext(crop, detail=0, allowlist="0123456789")
        except Exception:
            words = []
        
        text = " ".join(words) if words else ""
        digits = re.sub(r"\D", "", text)
        pred["ocr_words"] = words
        pred["ocr_text"] = text
        pred["ocr_digits"] = digits
        if digits:
            pred["ocr_digits_engine"] = "easyocr"

def ocr_digits_tesseract(img: np.ndarray, predictions: List[Dict[str, Any]], 
                         pad_ratio: float = 0.15, preprocess: str = "strong") -> None:
    """OCR para dígitos usando Tesseract"""
    try:
        import pytesseract
        tess_cmd = os.getenv("TESSERACT_EXE")
        if tess_cmd:
            pytesseract.pytesseract.tesseract_cmd = tess_cmd
    except Exception as e:
        raise RuntimeError("pytesseract no está instalado o Tesseract-OCR no está disponible.") from e
    
    for pred in predictions:
        crop = _crop_with_pad(img, pred, pad_ratio=pad_ratio)
        crop = _preprocess_crop(crop, mode=preprocess)
        if crop.size == 0:
            pred["ocr_words"] = []
            pred["ocr_text"] = ""
            pred["ocr_digits"] = ""
            continue
        
        try:
            cfg = "--psm 7 -c tessedit_char_whitelist=0123456789"
            text = pytesseract.image_to_string(crop, config=cfg)
        except Exception:
            text = ""
        
        digits = re.sub(r"\D", "", text or "")
        pred["ocr_words"] = [text.strip()] if text else []
        pred["ocr_text"] = (text or "").strip()
        pred["ocr_digits"] = digits
        if digits:
            pred["ocr_digits_engine"] = "tesseract"

_DIGITS_ENGINE_FUNCS = {
    "easyocr": ocr_digits_easyocr,
    "tesseract": ocr_digits_tesseract,
}

_DEFAULT_ENGINE_ORDER = ["easyocr", "tesseract"]

def _get_engine_order(preferred: str) -> List[str]:
    """Determina el orden de motores OCR a intentar"""
    pref = (preferred or "auto").lower()
    
    if pref == "auto":
        return list(_DEFAULT_ENGINE_ORDER)
    
    if pref not in _DIGITS_ENGINE_FUNCS:
        return list(_DEFAULT_ENGINE_ORDER)
    
    rest = [eng for eng in _DEFAULT_ENGINE_ORDER if eng != pref]
    return [pref] + rest

def _apply_digits_engines(
    img: np.ndarray,
    predictions: List[Dict[str, Any]],
    pad_ratio: float,
    preprocess: str,
    preferred_engine: str,
) -> List[str]:
    """Aplica motores OCR en orden hasta encontrar dígitos"""
    errors: List[str] = []
    
    for pred in predictions:
        if "ocr_digits" not in pred:
            pred["ocr_digits"] = ""
    
    engine_order = _get_engine_order(preferred_engine)
    
    for engine in engine_order:
        pending = [p for p in predictions if not p.get("ocr_digits")]
        if not pending:
            break
        
        func = _DIGITS_ENGINE_FUNCS.get(engine)
        if not func:
            continue
        
        try:
            func(img, pending, pad_ratio=pad_ratio, preprocess=preprocess)
        except Exception as exc:
            errors.append(f"{engine}: {exc}")
    
    return errors

def _ensure_empty_ocr_fields(predictions: List[Dict[str, Any]]) -> None:
    """Asegura que todos los campos OCR existan"""
    for p in predictions:
        if "ocr_words" not in p:
            p["ocr_words"] = []
        if "ocr_text" not in p:
            p["ocr_text"] = ""

def _strip_textual_ocr_fields(predictions: List[Dict[str, Any]]) -> None:
    """Elimina campos de texto cuando solo interesa el número"""
    for p in predictions:
        if "ocr_words" in p:
            del p["ocr_words"]
        if "ocr_text" in p:
            del p["ocr_text"]
        if "ocr_digits" not in p:
            p["ocr_digits"] = ""
