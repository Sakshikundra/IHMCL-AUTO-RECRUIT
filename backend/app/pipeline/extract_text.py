import pdfplumber
from pypdf import PdfReader


def extract_pdf_pages(path: str) -> list[dict]:
    """Returns [{page: 1, text: '...'}, ...]. Falls back to pypdf if pdfplumber fails."""
    pages = []
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append({"page": i, "text": text})
        if any(p["text"].strip() for p in pages):
            return pages
    except Exception:
        pass

    # Fallback
    try:
        reader = PdfReader(path)
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            pages.append({"page": i, "text": page.extract_text() or ""})
    except Exception:
        pages = [{"page": 1, "text": ""}]
    return pages


def pdf_text_with_page_markers(path: str) -> str:
    """Flattens a PDF into text with explicit [PAGE n] markers so the model can cite pages."""
    pages = extract_pdf_pages(path)
    return "\n\n".join(f"[PAGE {p['page']}]\n{p['text']}" for p in pages)
