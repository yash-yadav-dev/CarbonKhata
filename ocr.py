from pathlib import Path

import pytesseract
from PIL import Image, ImageOps
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
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        return pytesseract.image_to_string(image).strip()


def extract_text(file_path: str) -> dict:
    """Extract text and report whether manual review is needed."""
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError("Document not found.")

    extension = path.suffix.lower()

    if extension == ".pdf":
        text = extract_pdf_text(str(path))
        method = "pdf_text_extraction"

        if not text:
            return {
                "text": "",
                "method": method,
                "characters_extracted": 0,
                "needs_review": True,
                "warning": (
                    "No embedded text was found. This may be a scanned PDF. "
                    "Use an OCR-readable image or a PDF with selectable text."
                ),
            }

    elif extension in {".jpg", ".jpeg", ".png"}:
        try:
            text = extract_image_text(str(path))
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError(
                "Image OCR requires the Tesseract OCR engine. "
                "Install Tesseract and ensure it is available on PATH."
            ) from exc
        except pytesseract.TesseractError as exc:
            raise RuntimeError(
                "Tesseract could not process this image. "
                "Try a clearer JPG or PNG image."
            ) from exc

        method = "tesseract_ocr"

        if not text:
            return {
                "text": "",
                "method": method,
                "characters_extracted": 0,
                "needs_review": True,
                "warning": (
                    "No text was detected. Try a clearer image with "
                    "better lighting and readable text."
                ),
            }

    else:
        raise ValueError("Unsupported file type.")

    return {
        "text": text,
        "method": method,
        "characters_extracted": len(text),
        "needs_review": True,
    }
