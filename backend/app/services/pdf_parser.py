from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PDFParseError(ValueError):
    pass


def extract_pdf_text(data: bytes, *, max_pages: int = 25) -> str:
    try:
        reader = PdfReader(BytesIO(data))
    except (PdfReadError, ValueError, OSError) as exc:
        raise PDFParseError("PDF okunamadi") from exc

    parts: list[str] = []
    for index, page in enumerate(reader.pages):
        if index >= max_pages:
            break
        try:
            text = page.extract_text() or ""
        except (PdfReadError, ValueError, KeyError):
            text = ""
        clean = text.strip()
        if clean:
            parts.append(clean)

    extracted = "\n\n".join(parts).strip()
    if not extracted:
        raise PDFParseError("PDF metin icermiyor")
    return extracted
