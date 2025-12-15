import os
import sys
from pypdf import PdfMerger


def unir_pdfs_en_carpeta(carpeta_salida: str = ".", nombre_salida: str = "resultado_final.pdf") -> None:
    """Une todos los PDFs de una carpeta en un solo archivo.

    Parámetros:
      - carpeta_salida: Carpeta donde se buscan los PDFs y se guarda el resultado.
      - nombre_salida: Nombre del archivo final (se sobreescribe si existe).
    """

    carpeta_salida = os.path.abspath(carpeta_salida)
    if not os.path.isdir(carpeta_salida):
        print(f"La carpeta no existe: {carpeta_salida}")
        return

    salida_path = os.path.join(carpeta_salida, nombre_salida)

    # 1) Obtener PDFs de la carpeta (case-insensitive) y excluir el archivo de salida
    archivos_pdf = [
        f
        for f in os.listdir(carpeta_salida)
        if f.lower().endswith(".pdf") and f.lower() != nombre_salida.lower()
    ]

    # 2) Orden alfabético insensible a mayúsculas/minúsculas
    #    Si quieres control absoluto del orden, numera los archivos: 01_, 02_, 03_
    archivos_pdf.sort(key=str.casefold)

    if not archivos_pdf:
        print("No se encontraron archivos PDF para unir.")
        return

    print("Uniendo los siguientes archivos en orden:")
    merger = PdfMerger()

    for pdf in archivos_pdf:
        ruta_pdf = os.path.join(carpeta_salida, pdf)
        print(f"  -> {pdf}")
        try:
            merger.append(ruta_pdf)
        except Exception as exc:
            print(f"[AVISO] No se pudo agregar '{pdf}': {exc}")

    if not merger.pages:
        print("No se pudo crear el PDF final (no se añadieron páginas válidas).")
        try:
            merger.close()
        finally:
            return

    # 3) Escribir el PDF final (abrir el archivo en modo binario)
    try:
        with open(salida_path, "wb") as salida:
            merger.write(salida)
    finally:
        merger.close()

    print(f"\n¡Éxito! Archivo guardado como: {salida_path}")


# --- Ejecutar el script ---
if __name__ == "__main__":
    # Si se pasa una ruta por argumentos, usarla; si no, usar la carpeta del script
    carpeta = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    unir_pdfs_en_carpeta(carpeta)