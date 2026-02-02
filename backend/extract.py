from PyPDF2 import PdfReader
from docx import Document
from openpyxl import load_workbook
from PIL import Image
import pytesseract
import subprocess
import pathlib



soffice = r"C:\Program Files\LibreOffice\program\soffice.exe"
outdir = r"C:\Users\Administrador\algarrobo\docs"


def estract_doc(archivo):
    subprocess.run([
        soffice,
        "--headless",
        "--convert-to", "txt:Text",
        archivo,
        "--outdir", outdir
    ], check=True)

    # Leer el txt generado
    txt_path = pathlib.Path(archivo).with_suffix(".txt")
    text = txt_path.read_text(encoding="utf-8", errors="ignore")
    return text


def extract_text_from_file(file_path, extension):
    try:
        if extension == "pdf":
            reader = PdfReader(file_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)

        elif extension in ( "docx"):
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        
        elif extension in ("doc"):
            doc = estract_doc(file_path)
            return doc

        elif extension in ("xls", "xlsx"):
            wb = load_workbook(file_path, data_only=True)
            text = []
            for sheet in wb:
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value:
                            text.append(str(cell.value))
            return "\n".join(text)

        elif extension in ("png", "jpg", "jpeg"):
            img = Image.open(file_path)
            return pytesseract.image_to_string(img)

        else:
            return ""

    except Exception as e:
        return ""
