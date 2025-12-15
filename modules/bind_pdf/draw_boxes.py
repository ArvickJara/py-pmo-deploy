import argparse
import json
import os
from typing import Any, Dict, List, Optional

import cv2
import numpy as np


def _clean_inline_json(s: str) -> str:
    """Best-effort cleanup for inline JSON passed via shells.

    - Strip BOM if present
    - Trim whitespace
    """
    # Remove UTF-8 BOM if present
    s = s.lstrip("\ufeff").lstrip("\uFEFF")
    # Trim whitespace/newlines from both ends
    s = s.strip()
    return s


def load_predictions(pred_source: str, inline: bool) -> Dict[str, Any]:
    """Load predictions from a JSON file or inline JSON string.

    Expected format:
    {
      "predictions": [
        {"x": float, "y": float, "width": float, "height": float,
         "confidence": float, "class": str, "class_id": int, "detection_id": str}
      ]
    }
    """
    if inline:
        # Tolerate BOM/newlines in inline JSON
        cleaned = _clean_inline_json(pred_source)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                "No se pudo parsear --json-inline. Asegúrate de pasar JSON válido. "
                "En PowerShell, usa un here-string o guarda a archivo y usa --json.\n"
                f"Detalle: {e}"
            )
    else:
        # Use utf-8-sig to gracefully handle files with BOM written by some editors/tools
        with open(pred_source, "r", encoding="utf-8-sig") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(
                    "No se pudo parsear el archivo JSON. Verifica que el contenido sea JSON válido.\n"
                    f"Archivo: {pred_source}\nDetalle: {e}"
                )
    if isinstance(data, list):
        data = {"predictions": data}
    if "predictions" not in data or not isinstance(data["predictions"], list):
        raise ValueError("JSON inválido: se esperaba una clave 'predictions' con una lista.")
    return data


def xywh_to_xyxy(cx: float, cy: float, w: float, h: float) -> List[int]:
    x1 = int(round(cx - w / 2.0))
    y1 = int(round(cy - h / 2.0))
    x2 = int(round(cx + w / 2.0))
    y2 = int(round(cy + h / 2.0))
    return [x1, y1, x2, y2]


def clamp_box(x1: int, y1: int, x2: int, y2: int, width: int, height: int) -> List[int]:
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(0, min(x2, width - 1))
    y2 = max(0, min(y2, height - 1))
    return [x1, y1, x2, y2]


def draw_boxes(
    image_path: str,
    predictions: List[Dict[str, Any]],
    out_path: str,
    color: tuple = (0, 255, 0),
    thickness: int = 3,
    font_scale: float = 0.8,
    draw_center: bool = False,
) -> None:
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"No se pudo leer la imagen: {image_path}")

    h, w = img.shape[:2]

    for p in predictions:
        cx = float(p.get("x"))
        cy = float(p.get("y"))
        bw = float(p.get("width"))
        bh = float(p.get("height"))
        cls = str(p.get("class", ""))
        conf = p.get("confidence")
        label = cls
        if conf is not None:
            try:
                label = f"{cls} {float(conf):.3f}"
            except Exception:
                pass

        x1, y1, x2, y2 = xywh_to_xyxy(cx, cy, bw, bh)
        x1, y1, x2, y2 = clamp_box(x1, y1, x2, y2, w, h)

        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

        # Draw label background for readability
        ((text_w, text_h), baseline) = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
        text_x, text_y = x1, max(0, y1 - 5)
        cv2.rectangle(img, (text_x, text_y - text_h - baseline), (text_x + text_w, text_y), color, -1)
        cv2.putText(
            img,
            label,
            (text_x, text_y - 2),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=font_scale,
            color=(0, 0, 0),
            thickness=2,
            lineType=cv2.LINE_AA,
        )

        if draw_center:
            cv2.circle(img, (int(round(cx)), int(round(cy))), radius=4, color=color, thickness=-1)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if not cv2.imwrite(out_path, img):
        raise RuntimeError(f"No se pudo guardar la imagen de salida en: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Dibujar recuadros a partir de un JSON de predicciones (xywh en píxeles)")
    parser.add_argument("image", help="Ruta de la imagen de entrada")
    parser.add_argument("--json", dest="json_path", help="Ruta a archivo JSON con {predictions: [...]} ")
    parser.add_argument("--json-inline", dest="json_inline", help="Cadena JSON inline con {predictions: [...]} ")
    parser.add_argument("--out", default=None, help="Ruta de salida (por defecto: <imagen>_boxed.png)")
    parser.add_argument("--color", default="0,255,0", help="Color BGR de caja, ej: 0,255,0")
    parser.add_argument("--thickness", type=int, default=3, help="Grosor de línea de la caja")
    parser.add_argument("--font-scale", type=float, default=0.8, help="Escala de fuente para la etiqueta")
    parser.add_argument("--draw-center", action="store_true", help="Dibujar punto en el centro (x,y)")

    args = parser.parse_args()

    if not args.json_path and not args.json_inline:
        raise SystemExit("Debes especificar --json <archivo> o --json-inline <cadena>")

    inline = args.json_inline is not None
    pred_source = args.json_inline if inline else args.json_path
    data = load_predictions(pred_source, inline=inline)

    image_path = args.image
    base, ext = os.path.splitext(os.path.basename(image_path))
    out_path = args.out or f"{base}_boxed.png"

    try:
        bgr = tuple(int(x) for x in args.color.split(","))
        if len(bgr) != 3:
            raise ValueError
    except Exception:
        raise SystemExit("--color debe ser 'B,G,R', por ejemplo 0,255,0")

    draw_boxes(
        image_path=image_path,
        predictions=data["predictions"],
        out_path=out_path,
        color=bgr,  # OpenCV usa BGR
        thickness=args.thickness,
        font_scale=args.font_scale,
        draw_center=args.draw_center,
    )

    print(f"Guardado: {out_path}")


if __name__ == "__main__":
    main()
