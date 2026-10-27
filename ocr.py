from pathlib import Path

import pytesseract
from PIL import Image
from pypdf import PdfReader


def extract_pdf_text(file_path: str) -> str:
    """Extract embedded text from a PDF."""
    reader = PdfReader(file_path)
    pages = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return "\n".join(pages).strip()


def extract_image_text(file_path: str) -> str:
    """Extract text from an image using Tesseract OCR."""
    with Image.open(file_path) as image:
        return pytesseract.image_to_string(image).strip()


def extract_text(file_path: str) -> dict:
    """Choose the extraction method based on file extension."""
    path = Path(file_path)
    extension = path.suffix.lower()

    if not path.is_file():
        raise FileNotFoundError("Document not found.")

    if extension == ".pdf":
        text = extract_pdf_text(str(path))
        method = "pdf_text_extraction"
    elif extension in {".jpg", ".jpeg", ".png"}:
        text = extract_image_text(str(path))
        method = "tesseract_ocr"
    else:
        raise ValueError("Unsupported file type.")

    return {
        "text": text,
        "method": method,
        "characters_extracted": len(text),
        "needs_review": True
    }