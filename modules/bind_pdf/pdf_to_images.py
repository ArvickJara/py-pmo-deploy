import argparse
import os
import io
from typing import Optional
from PIL import Image
import fitz  # PyMuPDF

def _resize_image(img: Image.Image, scale: float) -> Image.Image:
    new_w = max(1, int(img.width * scale))
    new_h = max(1, int(img.height * scale))
    return img.resize((new_w, new_h), Image.LANCZOS)

def _save_with_size_cap(img: Image.Image, out_path: str, fmt: str, max_mb: Optional[float]) -> None:
    """
    Guarda 'img' como fmt (png|jpg), intentando que pese <= max_mb.
    Estrategia:
      - JPG: bajar calidad primero; si no alcanza, reducir resolución y volver a probar.
      - PNG: intentar optimize+compresión; si no alcanza, reducir resolución.
    """
    fmt = fmt.lower()
    if max_mb is None:
        # Guardado directo con buenas opciones por defecto.
        if fmt == "jpg":
            img.save(out_path, format="JPEG", quality=95, subsampling="4:2:0", optimize=True, progressive=True)
        else:
            img.save(out_path, format="PNG", optimize=True, compress_level=9)
        return

    max_bytes = int(max_mb * 1024 * 1024)
    best_bytes = None
    best_buf = None

    def try_save(cur_img: Image.Image, quality: Optional[int] = None) -> bytes:
        buf = io.BytesIO()
        if fmt == "jpg":
            q = 95 if quality is None else quality
            cur_img.save(buf, format="JPEG", quality=q, subsampling="4:2:0", optimize=True, progressive=True)
        else:
            cur_img.save(buf, format="PNG", optimize=True, compress_level=9)
        return buf.getvalue()

    cur_img = img
    if fmt == "jpg":
        quality = 95
        scale = 1.0
        while True:
            data = try_save(cur_img, quality)
            size = len(data)
            # Mantener el mejor intento (más pequeño)
            if best_bytes is None or size < best_bytes:
                best_bytes = size
                best_buf = data
            if size <= max_bytes:
                # Guardar y salir
                with open(out_path, "wb") as f:
                    f.write(data)
                return
            # Intentar bajar calidad hasta 40, luego reducir escala
            if quality > 40:
                quality -= 5
                continue
            # Si ya no podemos bajar más la calidad, reducimos escala
            # Limitar reducción para no destruir la legibilidad: hasta ~30% del tamaño original
            if min(cur_img.width, cur_img.height) > 800:
                scale *= 0.85
                cur_img = _resize_image(cur_img, 0.85)
                # Al reducir tamaño, podemos subir un poco calidad para mantener legibilidad
                quality = min(85, quality + 10)
                continue
            # No se pudo cumplir el límite, guardamos el mejor intento
            break
    else:
        # PNG: sin pérdidas, tamaño depende mucho de resolución; aplicamos optimize y reducimos escala si es necesario
        scale = 1.0
        while True:
            data = try_save(cur_img)
            size = len(data)
            if best_bytes is None or size < best_bytes:
                best_bytes = size
                best_buf = data
            if size <= max_bytes:
                with open(out_path, "wb") as f:
                    f.write(data)
                return
            if min(cur_img.width, cur_img.height) > 800:
                scale *= 0.85
                cur_img = _resize_image(cur_img, 0.85)
                continue
            break

    # Fallback: guardar el mejor que logramos (puede exceder el límite si era imposible sin perder demasiado)
    if best_buf is not None:
        with open(out_path, "wb") as f:
            f.write(best_buf)
    else:
        # Caso extremo: guardar algo para no fallar
        if fmt == "jpg":
            img.save(out_path, format="JPEG", quality=85, subsampling="4:2:0", optimize=True, progressive=True)
        else:
            img.save(out_path, format="PNG", optimize=True, compress_level=9)

def pdf_to_images(pdf_path: str, out_dir: str, dpi: int = 300, prefix: str = None,
                  start: int = None, end: int = None, fmt: str = "png",
                  max_mb: Optional[float] = None) -> None:
    """
    Convierte páginas de un PDF a imágenes.
    - max_mb: tamaño máximo por imagen (MB). Si se excede, se intenta comprimir y/o reescalar.
    """
    doc = fitz.open(pdf_path)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    prefix = prefix or base
    os.makedirs(out_dir, exist_ok=True)

    zoom = dpi / 72.0

    total_pages = len(doc)
    first_idx = 0 if start is None else max(start - 1, 0)
    last_idx = total_pages - 1 if end is None else min(end - 1, total_pages - 1)

    for page_index in range(first_idx, last_idx + 1):
        page = doc[page_index]
        # Manejar prerotate/preRotate
        m = fitz.Matrix(zoom, zoom)
        m = m.prerotate(page.rotation or 0) if hasattr(m, "prerotate") else m.preRotate(page.rotation or 0)
        pix = page.get_pixmap(matrix=m, alpha=False)

        # Convertir a PIL para controlar compresión y reescalado
        pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        out_name = f"{prefix}_p{page_index+1:04d}.{fmt.lower()}"
        out_path = os.path.join(out_dir, out_name)

        _save_with_size_cap(pil_img, out_path, fmt, max_mb)
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"Guardado: {out_path} ({size_mb:.2f} MB)")

    print("Listo.")

def main():
    ap = argparse.ArgumentParser(description="Convertir PDF escaneado a imágenes (PyMuPDF).")
    ap.add_argument("pdf", help="Ruta al PDF")
    ap.add_argument("--out", default="pages_images", help="Carpeta de salida")
    ap.add_argument("--dpi", type=int, default=300, help="Resolución (300–600)")
    ap.add_argument("--prefix", help="Prefijo de archivos (opcional)")
    ap.add_argument("--start", type=int, help="Página inicial (1-based)")
    ap.add_argument("--end", type=int, help="Página final (1-based)")
    ap.add_argument("--fmt", choices=["png", "jpg"], default="png", help="Formato de imagen")
    ap.add_argument("--max-mb", type=float, help="Tamaño máximo por imagen (MB), ej. 20")
    args = ap.parse_args()

    pdf_to_images(
        pdf_path=args.pdf,
        out_dir=args.out,
        dpi=args.dpi,
        prefix=args.prefix,
        start=args.start,
        end=args.end,
        fmt=args.fmt,
        max_mb=args.max_mb,
    )

if __name__ == "__main__":
    main()