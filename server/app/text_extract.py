from pathlib import Path
from typing import Tuple
import io

def extract_text(content: bytes, filename: str, mime: str | None) -> Tuple[str, dict]:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        from pdfminer.high_level import extract_text as pdf_text
        buf = io.BytesIO(content)
        text = pdf_text(buf)
        return text, {"kind": "pdf"}
    if name.endswith(".docx"):
        import docx
        f = io.BytesIO(content)
        doc = docx.Document(f)
        text = "\n".join(p.text for p in doc.paragraphs)
        return text, {"kind": "docx"}
    # fallback: txt/markdown
    try:
        return content.decode("utf-8", errors="ignore"), {"kind": "plain"}
    except Exception:
        return "", {"kind": "unknown"}
