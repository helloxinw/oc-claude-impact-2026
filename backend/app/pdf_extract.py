"""Turn an uploaded referral-packet PDF into per-page OCR text.

Hospital referral packets are usually scanned faxes with no text layer. We pull each page's
embedded image directly (no poppler/pdftoppm dependency) and run local OCR (Tesseract, via
pytesseract) on it ourselves, then hand Claude clean text instead of page images \u2014 far cheaper,
and the per-page text/confidence can be reviewed independently of any LLM call.
"""
import os
import shutil
from dataclasses import dataclass
from io import BytesIO

import pytesseract
from PIL import Image
from pypdf import PdfReader

if shutil.which('tesseract') is None:
    # pytesseract otherwise assumes `tesseract` is on PATH, which winget/choco installs on Windows
    # don't always add. Fall back to the common UB-Mannheim install location.
    _default_windows_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(_default_windows_path):
        pytesseract.pytesseract.tesseract_cmd = _default_windows_path


@dataclass
class OcrLine:
    text: str
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1), each 0-1 as a fraction of the page image


@dataclass
class PageContent:
    page_number: int  # 1-indexed
    text: str
    mean_confidence: float | None  # Tesseract's average per-word confidence (0-100); None if no words found
    lines: list[OcrLine]  # Empty for pages OCR didn't run on (e.g. the pypdf text-layer fallback)


class PdfExtractionError(ValueError):
    pass


def _largest_image(page) -> Image.Image | None:
    try:
        images = list(page.images)
    except Exception:
        return None
    if not images:
        return None
    best = max(images, key=lambda im: im.image.size[0] * im.image.size[1])
    return best.image


def _ocr_page(image: Image.Image) -> tuple[str, float | None, list[OcrLine]]:
    """Runs Tesseract once and reconstructs line-grouped text, a mean word confidence, and each
    line's bounding box (normalized to the image size), instead of calling image_to_string and
    image_to_data separately. The bounding boxes let the frontend highlight exactly where an
    extracted fact came from, rather than just the page it's on."""
    if image.mode not in ('RGB', 'L'):
        image = image.convert('L')
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    width, height = image.size

    words_by_line: dict[tuple[int, int, int], list[str]] = {}
    boxes_by_line: dict[tuple[int, int, int], list[tuple[int, int, int, int]]] = {}
    confidences: list[int] = []
    for i, word in enumerate(data['text']):
        if not word.strip():
            continue
        conf = int(float(data['conf'][i]))
        if conf >= 0:
            confidences.append(conf)
        key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        words_by_line.setdefault(key, []).append(word)
        left, top, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        boxes_by_line.setdefault(key, []).append((left, top, left + w, top + h))

    text = '\n'.join(' '.join(words) for words in words_by_line.values())
    mean_confidence = sum(confidences) / len(confidences) if confidences else None

    lines: list[OcrLine] = []
    if width and height:
        for key, words in words_by_line.items():
            word_boxes = boxes_by_line[key]
            x0 = min(b[0] for b in word_boxes) / width
            y0 = min(b[1] for b in word_boxes) / height
            x1 = max(b[2] for b in word_boxes) / width
            y1 = max(b[3] for b in word_boxes) / height
            lines.append(OcrLine(text=' '.join(words), bbox=(x0, y0, x1, y1)))

    return text, mean_confidence, lines


def extract_pages(file_bytes: bytes, *, max_pages: int = 60) -> list[PageContent]:
    """Raises PdfExtractionError if the file cannot be read as a PDF at all."""
    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:
        raise PdfExtractionError(f'Could not open file as a PDF: {exc}') from exc

    if reader.is_encrypted:
        raise PdfExtractionError('This PDF is password-protected. Remove the password and re-upload.')

    num_pages = len(reader.pages)
    if num_pages == 0:
        raise PdfExtractionError('This PDF has no pages.')
    if num_pages > max_pages:
        raise PdfExtractionError(f'This PDF has {num_pages} pages; the limit for one referral packet is {max_pages}.')

    pages: list[PageContent] = []
    for index in range(num_pages):
        page_number = index + 1
        text = ''
        confidence: float | None = None
        lines: list[OcrLine] = []
        try:
            page = reader.pages[index]
            image = _largest_image(page)
            if image is not None:
                text, confidence, lines = _ocr_page(image)
            if not text:
                # No embedded image (or OCR found nothing) \u2014 fall back to any text layer the PDF has.
                text = (page.extract_text() or '').strip()
        except Exception as exc:
            text = f'[Page {page_number} could not be read: {exc}]'
        pages.append(PageContent(page_number=page_number, text=text, mean_confidence=confidence, lines=lines))
    return pages
