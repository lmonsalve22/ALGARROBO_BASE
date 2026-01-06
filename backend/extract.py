from PyPDF2 import PdfReader
from docx import Document
from openpyxl import load_workbook
from PIL import Image
import pytesseract

def extract_text_from_file(file_path, extension):
    try:
        if extension == "pdf":
            reader = PdfReader(file_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)

        elif extension in ("doc", "docx"):
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)

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
