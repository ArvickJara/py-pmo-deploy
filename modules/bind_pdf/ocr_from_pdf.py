import argparse
import json
import os
from typing import List, Tuple, Optional

import numpy as np

try:
    import fitz  # PyMuPDF
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "PyMuPDF (pymupdf) is required for this script. Install with `pip install pymupdf`."
    ) from e

try:
    import keras_ocr
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "keras-ocr is required for this script. Install with `pip install keras-ocr`.\n"
        "Note: keras-ocr depends on TensorFlow 2.x."
    ) from e

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None  # optional, only needed for simple preprocessing

try:
    import matplotlib.pyplot as plt  # optional for annotation saving
except Exception:
    plt = None


def configure_tf_memory():
    """Configure TensorFlow memory growth if requested via env vars.

    If you set environment variable MEMORY_GROWTH to any value, keras_ocr.config.configure()
    will configure TF to allocate memory on demand. Optionally, MEMORY_ALLOCATED can limit
    VRAM usage ratio per process (float in 0..1).
    """
    try:
        # Only call if keras_ocr is available
        keras_ocr.config.configure()
    except Exception:
        # Non-fatal if TF is not present yet
        pass


def pdf_pages_to_images(pdf_path: str, dpi: int = 300,
                        first_page: Optional[int] = None,
                        last_page: Optional[int] = None) -> List[np.ndarray]:
    """Render PDF pages to images using PyMuPDF at the given DPI.

    Args:
        pdf_path: Path to the PDF file.
        dpi: Dots per inch for rendering (300-600 recommended for OCR).
        first_page: 1-based inclusive start page. If None, start from first.
        last_page: 1-based inclusive end page. If None, go to last.
    Returns:
        List of numpy arrays in RGB format (H, W, 3), dtype=uint8.
    """
    doc = fitz.open(pdf_path)
    images: List[np.ndarray] = []
    zoom = dpi / 72.0
    for page_index in range(len(doc)):
        pno = page_index + 1
        if first_page is not None and pno < first_page:
            continue
        if last_page is not None and pno > last_page:
            break
        page = doc[page_index]
        mat = fitz.Matrix(zoom, zoom).preRotate(page.rotation or 0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8)
        img = img.reshape(pix.height, pix.width, pix.n)
        if img.shape[2] == 4:  # RGBA -> RGB
            img = img[:, :, :3]
        # PyMuPDF returns RGB order
        images.append(img)
    return images


def simple_preprocess(img: np.ndarray) -> np.ndarray:
    """Optional light preprocessing to help OCR on scans.

    - Convert to RGB if needed.
    - Optionally apply CLAHE on L channel (if OpenCV available).
    """
    if cv2 is None:
        return img
    if img.ndim == 2:
        rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    elif img.shape[2] == 4:
        rgb = img[:, :, :3]
    else:
        rgb = img
    # Convert to LAB and apply CLAHE on L (optional mild contrast boost)
    try:
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        rgb = cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)
    except Exception:
        pass
    return rgb


def run_ocr_on_images(images: List[np.ndarray], scale: int = 2,
                      detection_kwargs: Optional[dict] = None,
                      recognition_kwargs: Optional[dict] = None) -> List[List[Tuple[str, np.ndarray]]]:
    """Run keras-ocr pipeline on a list of RGB images.

    Returns a list (per image) of (text, box) where box is 4x2 np.ndarray.
    """
    configure_tf_memory()
    pipeline = keras_ocr.pipeline.Pipeline(
        scale=scale,
        detector=keras_ocr.detection.Detector(**(detection_kwargs or {})),
        recognizer=keras_ocr.recognition.Recognizer(**(recognition_kwargs or {})),
    )
    preds = pipeline.recognize(images)
    return preds


def save_annotations(images: List[np.ndarray],
                     predictions: List[List[Tuple[str, np.ndarray]]],
                     out_dir: str, stem: str) -> None:
    """Save annotated images visualizing OCR results.

    Requires matplotlib. If not available, this function is a no-op.
    """
    if plt is None:
        print("[AVISO] matplotlib no está instalado; se omite guardado de anotaciones.")
        return
    os.makedirs(out_dir, exist_ok=True)
    import keras_ocr.tools as tools
    for i, (img, preds) in enumerate(zip(images, predictions), start=1):
        fig, ax = plt.subplots(figsize=(12, 12))
        tools.drawAnnotations(image=img, predictions=preds, ax=ax)
        ax.set_axis_off()
        fig.tight_layout(pad=0)
        out_path = os.path.join(out_dir, f"{stem}_page_{i:03d}.png")
        fig.savefig(out_path, dpi=200, bbox_inches='tight', pad_inches=0)
        plt.close(fig)


def serialize_predictions(predictions: List[List[Tuple[str, np.ndarray]]]) -> list:
    out = []
    for page_idx, preds in enumerate(predictions, start=1):
        page_items = []
        for text, box in preds:
            page_items.append({
                "text": text,
                "box": np.asarray(box, dtype=float).tolist()  # 4x2 list
            })
        out.append({"page": page_idx, "predictions": page_items})
    return out


def main():
    parser = argparse.ArgumentParser(description="OCR para PDFs escaneados usando PyMuPDF + keras-ocr")
    parser.add_argument("pdf", help="Ruta al PDF a procesar")
    parser.add_argument("--out", default="ocr_output", help="Carpeta de salida (JSON y anotaciones opcionales)")
    parser.add_argument("--json_name", default=None, help="Nombre del archivo JSON (por defecto, <pdf_stem>.json)")
    parser.add_argument("--dpi", type=int, default=300, help="DPI para renderizar páginas (300-600 recomendado)")
    parser.add_argument("--scale", type=int, default=2, help="Escala de la Pipeline (2 o 3 suelen ir bien para texto pequeño)")
    parser.add_argument("--first_page", type=int, default=None, help="Página inicial (1-based)")
    parser.add_argument("--last_page", type=int, default=None, help="Página final (1-based, inclusiva)")
    parser.add_argument("--annotate", action="store_true", help="Guardar PNGs con anotaciones de OCR")
    args = parser.parse_args()

    pdf_path = os.path.abspath(args.pdf)
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"No se encontró el archivo PDF: {pdf_path}")

    os.makedirs(args.out, exist_ok=True)
    stem = os.path.splitext(os.path.basename(pdf_path))[0]

    print(f"[1/4] Renderizando páginas de: {pdf_path} a {args.dpi} DPI...")
    images = pdf_pages_to_images(pdf_path, dpi=args.dpi,
                                 first_page=args.first_page, last_page=args.last_page)
    if not images:
        raise RuntimeError("No se generaron imágenes desde el PDF (¿rango de páginas vacío?).")

    print(f"[2/4] Preprocesando {len(images)} páginas...")
    images_prep = [simple_preprocess(img) for img in images]

    print(f"[3/4] Ejecutando OCR con keras-ocr (scale={args.scale})...")
    predictions = run_ocr_on_images(images_prep, scale=args.scale)

    print(f"[4/4] Serializando resultados a JSON...")
    data = serialize_predictions(predictions)
    json_name = args.json_name or f"{stem}.json"
    json_path = os.path.join(args.out, json_name)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"JSON guardado en: {json_path}")

    if args.annotate:
        print("Guardando imágenes anotadas...")
        ann_dir = os.path.join(args.out, f"{stem}_annotated")
        save_annotations(images, predictions, ann_dir, stem)
        print(f"Anotaciones guardadas en: {ann_dir}")

    print("Hecho.")


if __name__ == "__main__":
    main()