from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.settings import settings
from app.embedder import embed_texts
from app.pine import query_vectors
from app.models import Chunk, Document
from urllib.parse import urlparse

def retrieve(db: Session, *, workspace: str, query_text: str) -> Tuple[List[Any], List[Chunk], float]:
    qv = embed_texts([query_text])[0]
    res = query_vectors(workspace, qv, top_k=settings.topk, include_metadata=True)
    matches = getattr(res, "matches", None) or res.get("matches", []) or []
    ids = []
    for m in matches:
        meta = m.get("metadata") if isinstance(m, dict) else m.metadata
        cid = meta.get("chunk_id") if meta else None
        if cid:
            ids.append(cid)
    if not ids:
        return [], [], 0.0
    rows = db.query(Chunk).filter(Chunk.id.in_(ids)).all()
    avg = sum((m.get("score") if isinstance(m, dict) else m.score) or 0.0 for m in matches[:5]) / max(1, min(5, len(matches)))
    return matches, rows, float(avg)

def make_context_and_citations(db: Session, rows: List[Chunk]) -> Tuple[str, List[Dict[str, Any]]]:
    if not rows:
        return "", []

    # map document info
    doc_ids = list({r.document_id for r in rows})
    docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
    dmap = {str(d.id): d for d in docs}

    blocks, cites = [], []
    for i, r in enumerate(rows[:settings.max_context_chunks], start=1):
        d = dmap.get(str(r.document_id))
        fname = d.filename if d else "source"
        meta = (d.meta or {}) if d else {}
        src = (meta.get("source") or "local").lower()
        url = meta.get("url")
        domain = urlparse(url).netloc if (url and src == "web") else None

        header = f"[{i}] ({fname}{f', p.{r.page_start}-{r.page_end}' if r.page_start is not None and r.page_end is not None else ''})"
        blocks.append(f"{header}\n{(r.text or '').strip()}")
        cites.append({
            "n": i,
            "filename": fname,
            "document_id": str(r.document_id),
            "chunk_id": str(r.id),
            "page_start": r.page_start,
            "page_end": r.page_end,
            "origin": "web" if src == "web" else "local",
            "domain": domain,
            "url": url if src == "web" else None,
        })
    return "\n\n".join(blocks), cites

def origin_summary(citations: List[Dict[str, Any]]) -> Dict[str, Any]:
    local = sum(1 for c in citations if c.get("origin") == "local")
    web = sum(1 for c in citations if c.get("origin") == "web")
    domains = sorted({c.get("domain") for c in citations if c.get("domain")})
    return {"mode": "enriched" if web > 0 else "local", "local": local, "web": web, "web_domains": domains}
