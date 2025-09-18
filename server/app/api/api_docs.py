from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.deps import get_db, workspace_header
from app.models import Document, Chunk
from typing import Optional

router = APIRouter(prefix="/api")

@router.get("/documents")
def list_docs(
    q: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    ws: str = Depends(workspace_header),
):
    base = db.query(Document).filter(Document.workspace_id == ws)
    if q:
        base = base.filter(Document.filename.ilike(f"%{q}%"))
    if status:
        base = base.filter(Document.status == status)
    total = base.count()
    rows = (
        base.order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    # fetch chunk counts
    counts = dict(
        db.query(Chunk.document_id, func.count(Chunk.id)).filter(Chunk.document_id.in_([r.id for r in rows])).group_by(Chunk.document_id).all()
    )
    return {
        "total": total,
        "documents": [
            {
                "id": str(r.id),
                "filename": r.filename,
                "status": r.status,
                "bytes": r.bytes,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "chunks": int(counts.get(r.id, 0)),
                "meta": r.meta or {},
            }
            for r in rows
        ],
    }

@router.get("/documents/{doc_id}")
def get_doc(doc_id: str, db: Session = Depends(get_db), ws: str = Depends(workspace_header)):
    row = db.get(Document, doc_id)
    if not row or row.workspace_id != ws:
        raise HTTPException(404, "Not found")
    return {
        "id": str(row.id),
        "filename": row.filename,
        "status": row.status,
        "bytes": row.bytes,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "meta": row.meta or {},
    }

@router.get("/documents/{doc_id}/chunks")
def get_doc_chunks(
    doc_id: str,
    include_text: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    ws: str = Depends(workspace_header),
):
    parent = db.get(Document, doc_id)
    if not parent or parent.workspace_id != ws:
        raise HTTPException(404, "Not found")
    base = db.query(Chunk).filter(Chunk.document_id == parent.id).order_by(Chunk.idx)
    total = base.count()
    rows = base.offset(offset).limit(limit).all()
    return {
        "total": total,
        "chunks": [
            {
                "chunk_id": str(r.id),
                "idx": r.idx,
                "token_count": r.token_count,
                "page_start": r.page_start,
                "page_end": r.page_end,
                "preview": r.text[:240] + ("…" if len(r.text) > 240 else ""),
                **({"text": r.text} if include_text else {}),
            }
            for r in rows
        ],
    }
