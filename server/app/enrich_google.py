from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from urllib.parse import urlparse
import re, requests

from app.settings import settings
from app.models import Document, Chunk
from app.chunker import chunk_text
from app.embedder import embed_texts
from app.pine import upsert_vectors
from app.utils import sha256_bytes

def _normalize_topic(t: str) -> str:
    t = (t or "").strip().strip("\"'‘’“”")
    t = re.sub(r"^(what\s+is|who\s+is|define|definition\s+of|describe|description\s+of)\s+", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t)
    parts = t.split(" ")
    return " ".join(parts[:12])

def google_search(topic: str) -> List[Dict[str, str]]:
    if not settings.google_cse_api_key or not settings.google_cse_cx:
        return []
    q = _normalize_topic(topic)
    params = {"key": settings.google_cse_api_key, "cx": settings.google_cse_cx, "q": q, "num": 3}
    r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
    r.raise_for_status()
    items = r.json().get("items", []) or []
    out = []
    for it in items:
        link = it.get("link"); title = it.get("title")
        if not link: continue
        out.append({"title": title or urlparse(link).netloc, "url": link})
    return out

def _fetch_page_text(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers={"User-Agent": f"{settings.app_name}/1.0"}, timeout=10)
        r.raise_for_status()
        html = r.text
        # naive strip; for prod consider trafilatura
        text = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.S|re.I)
        text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.S|re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text if len(text) > 500 else None
    except Exception:
        return None

def ingest_web_pages(
    db: Session, *, workspace: str, topics: List[str], openai_key: str | None
) -> List[str]:
    """
    For each topic query Google CSE, fetch text, store as Document(meta.source='web'), chunk, embed, upsert.
    Returns list of added document ids (as strings).
    """
    added: List[str] = []
    budget = settings.auto_enrich_max_docs

    for topic in topics:
        if budget <= 0:
            break
        per_topic = 0
        for item in google_search(topic):
            if budget <= 0 or per_topic >= settings.auto_enrich_max_per_topic:
                break
            url = item["url"]
            title = item["title"]
            text = _fetch_page_text(url)
            if not text:
                continue
            h = sha256_bytes(text.encode("utf-8"))
            exists = (
                db.query(Document)
                .filter(Document.workspace_id == workspace, Document.file_sha256 == h)
                .first()
            )
            if exists:
                added.append(str(exists.id))
                budget -= 1; per_topic += 1
                continue

            doc = Document(
                workspace_id=workspace,
                filename=title,
                mime="text/plain",
                bytes=len(text.encode("utf-8")),
                storage_uri=url,
                file_sha256=h,
                status="uploaded",
                meta={"source": "web", "provider": "google", "url": url, "domain": urlparse(url).netloc},
            )
            db.add(doc); db.commit(); db.refresh(doc)

            parts = chunk_text(text, settings.chunk_size_tokens, settings.chunk_overlap_tokens)
            rows: List[Chunk] = []
            for p in parts:
                rows.append(
                    Chunk(
                        document_id=doc.id,
                        idx=p["idx"],
                        text=p["text"],
                        token_count=p["token_count"],
                        sha256=p["sha"],
                        page_start=None,
                        page_end=None,
                    )
                )
            db.add_all(rows); db.commit()

            embeds = embed_texts([r.text for r in rows])
            vectors = []
            for r, v in zip(rows, embeds):
                vec_id = f"{workspace}:{doc.id}:{r.id}"
                vectors.append({"id": vec_id, "values": v, "metadata": {
                    "workspace": workspace, "document_id": str(doc.id), "chunk_id": str(r.id), "idx": r.idx, "filename": doc.filename
                }})
            upsert_vectors(workspace, vectors)

            doc.status = "processed"
            db.add(doc); db.commit()

            added.append(str(doc.id))
            budget -= 1; per_topic += 1

    return added
