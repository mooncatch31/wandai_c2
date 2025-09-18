from pathlib import Path
from sqlalchemy.orm import Session
from typing import List
from app.settings import settings
from app.models import Document, Chunk
from app.utils import ensure_dir, sha256_bytes
from app.text_extract import extract_text
from app.chunker import chunk_text
from app.embedder import embed_texts
from app.pine import upsert_vectors
from uuid import uuid4

DATA_ROOT = Path("data/uploaded")
ensure_dir(DATA_ROOT)

def store_and_ingest_file(db: Session, *, workspace: str, filename: str, content: bytes, mime: str | None):
    # Deduplicate by content hash per workspace
    file_hash = sha256_bytes(content)
    ex = (
        db.query(Document)
        .filter(Document.workspace_id == workspace, Document.file_sha256 == file_hash)
        .order_by(Document.created_at.desc())
        .first()
    )
    if ex:
        return ex, "duplicate"

    ws_dir = DATA_ROOT / workspace
    ensure_dir(ws_dir)
    dest = ws_dir / filename
    dest.write_bytes(content)

    doc = Document(
        workspace_id=workspace,
        filename=filename,
        mime=mime or "application/octet-stream",
        bytes=len(content),
        storage_uri=str(dest),
        file_sha256=file_hash,
        status="uploaded",
        meta={},
    )
    db.add(doc); db.commit(); db.refresh(doc)

    text, meta = extract_text(content, filename, mime)
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

    # embeddings
    embeds = embed_texts([r.text for r in rows])
    vectors = []
    for r, v in zip(rows, embeds):
        vec_id = f"{workspace}:{doc.id}:{r.id}"
        vectors.append({"id": vec_id, "values": v, "metadata": {
            "workspace": workspace,
            "document_id": str(doc.id),
            "chunk_id": str(r.id),
            "idx": r.idx,
            "filename": doc.filename
        }})
    upsert_vectors(workspace, vectors)
    doc.status = "processed"
    db.add(doc); db.commit()
    return doc, "processed"
