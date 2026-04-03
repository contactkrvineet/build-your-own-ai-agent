"""OCR utilities — extract text from scanned PDFs and images."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.utils.logger import logger


def extract_text_with_ocr(file_path: Path, language: str = "eng") -> Optional[str]:
    """
    Run Tesseract OCR on a PDF or image file and return extracted text.

    Requirements (system-level):
        - Tesseract: brew install tesseract  (macOS) / apt install tesseract-ocr
        - Poppler:   brew install poppler    (macOS) / apt install poppler-utils

    Args:
        file_path: Path to PDF or image (PNG, JPG, TIFF).
        language:  Tesseract language code (default: "eng").

    Returns:
        Extracted text string, or None on failure.
    """
    try:
        import pytesseract
        from PIL import Image

        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            pages = _pdf_to_images(file_path)
            if not pages:
                return None
            texts = [pytesseract.image_to_string(img, lang=language) for img in pages]
            return "\n\n".join(t for t in texts if t.strip())

        elif suffix in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}:
            img = Image.open(file_path)
            return pytesseract.image_to_string(img, lang=language)

        else:
            logger.warning(f"OCR: unsupported file type {suffix} for {file_path.name}")
            return None

    except ImportError as e:
        logger.error(
            "OCR dependencies missing. Install with: "
            "pip install pytesseract Pillow pdf2image\n"
            f"Details: {e}"
        )
        return None
    except Exception as e:
        logger.error(f"OCR failed for {file_path.name}: {e}")
        return None


def _pdf_to_images(pdf_path: Path):
    """Convert PDF pages to PIL Image objects using pdf2image."""
    try:
        from pdf2image import convert_from_path

        return convert_from_path(str(pdf_path), dpi=300)
    except Exception as e:
        logger.error(f"pdf2image failed for {pdf_path.name}: {e}")
        return []


def is_scanned_pdf(file_path: Path, sample_pages: int = 3) -> bool:
    """
    Heuristic: return True if the PDF has minimal extractable text,
    suggesting it is a scanned image-based PDF needing OCR.
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        char_count = 0
        for page in reader.pages[:sample_pages]:
            char_count += len((page.extract_text() or "").strip())
        # If fewer than 100 characters per page on average → likely scanned
        avg = char_count / max(len(reader.pages[:sample_pages]), 1)
        return avg < 100
    except Exception:
        return False
