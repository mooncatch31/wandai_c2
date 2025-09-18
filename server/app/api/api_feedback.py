from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import cast, Float, literal

from app.deps import get_db, workspace_header
from app.models import Feedback, Query, Chunk, DocumentReputation

router = APIRouter(prefix="/api")

class FeedbackIn(BaseModel):
    query_id: str
    rating: int = Field(ge=-1, le=1)
    comment: Optional[str] = None

@router.post("/feedback")
def submit_feedback(payload: FeedbackIn, db: Session = Depends(get_db), ws: str = Depends(workspace_header)):
    q = db.get(Query, payload.query_id)
    if not q or q.workspace_id != ws:
        raise HTTPException(404, "Query not found")

    fb = Feedback(query_id=q.id, rating=payload.rating, comment=payload.comment or None)
    db.add(fb)

    # doc IDs used in this answer
    used_chunks = list(set(q.used_chunk_ids or []))
    if used_chunks:
        docs = db.query(Chunk.document_id).filter(Chunk.id.in_(used_chunks)).all()
        doc_ids = list({d.document_id for d in docs})

        up = 1 if payload.rating > 0 else 0
        down = 1 if payload.rating < 0 else 0

        table = DocumentReputation.__table__
        values = [{"workspace_id": ws, "document_id": did, "up_count": up, "down_count": down, "score": 0} for did in doc_ids]
        if up or down:
            stmt = pg_insert(table).values(values)
            new_up = table.c.up_count + stmt.excluded.up_count
            new_dn = table.c.down_count + stmt.excluded.down_count
            score_expr = cast(new_up - new_dn, Float) / cast(new_up + new_dn + literal(3), Float)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_docrep_ws_doc",
                set_={"up_count": new_up, "down_count": new_dn, "score": score_expr},
            )
            db.execute(stmt)

    db.commit()
    return {"ok": True}
