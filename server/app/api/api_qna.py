from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Tuple
from sqlalchemy.orm import Session

from app.deps import get_db, workspace_header, openai_key_header
from app.settings import settings
from app.models import Query
from app.retriever import retrieve, make_context_and_citations, origin_summary
from app.openai_chat import answer_with_openai
from app.enrich_google import ingest_web_pages

router = APIRouter(prefix="/api")

class AskIn(BaseModel):
    query: str
    history: List[Dict[str, str]] = []
    auto_enrich: bool = False

def _conf_map(s: str) -> int:
    return {"low": 20, "medium": 60, "high": 90}.get(s, 60)

@router.post("/ask")
def ask(
    payload: AskIn,
    db: Session = Depends(get_db),
    ws: str = Depends(workspace_header),
    oai_key: str | None = Depends(openai_key_header),
):
    qraw = (payload.query or "").strip()
    if not qraw:
        raise HTTPException(400, "Query is required")

    qrow = Query(workspace_id=ws, question=qraw)
    db.add(qrow); db.commit(); db.refresh(qrow)

    matches, rows, avg = retrieve(db, workspace=ws, query_text=qraw)

    if not rows:
        context, cites = "", []
        data = {
            "answer": "I couldn’t find relevant information in your uploaded documents.",
            "confidence": "low",
            "missing_info": [qraw],
            "suggested_enrichment": ["Upload more domain-relevant files"],
        }
    else:
        ctx, cites = make_context_and_citations(db, rows)
        data = answer_with_openai(qraw, ctx, oai_key)
        if not data:
            data = {
                "answer": "Here’s what the context indicates:\n\n" + rows[0].text[:400],
                "confidence": "medium",
                "missing_info": [],
                "suggested_enrichment": [],
            }

    # decide enrichment
    should_enrich = (
        payload.auto_enrich
        and settings.auto_enrich_enabled
        and (
            (data.get("confidence") == "low")
            or (avg is not None and avg < settings.auto_enrich_min_conf)
            or bool(data.get("missing_info"))
        )
    )

    enrich_meta = None
    if should_enrich:
        topics = data.get("missing_info") or [qraw]
        added = ingest_web_pages(db, workspace=ws, topics=topics, openai_key=oai_key)
        if added:
            matches, rows, avg = retrieve(db, workspace=ws, query_text=qraw)
            ctx, cites = make_context_and_citations(db, rows)
            data2 = answer_with_openai(qraw, ctx, oai_key) or data
            data = data2
            enrich_meta = {
                "added_docs": len(added),
                "sources": [
                    {"id": d} for d in added
                ],
            }

    # persist query answer
    qrow.answer = data.get("answer", "")
    qrow.confidence = _conf_map(data.get("confidence", "medium"))
    qrow.missing_info = data.get("missing_info") or []
    qrow.suggested_enrichment = data.get("suggested_enrichment") or []
    qrow.used_chunk_ids = [c["chunk_id"] for c in (cites or []) if "chunk_id" in c]
    db.add(qrow); db.commit()

    out = {
        "query_id": str(qrow.id),
        "answer": qrow.answer,
        "confidence": data.get("confidence", "medium"),
        "missing_info": qrow.missing_info,
        "suggested_enrichment": qrow.suggested_enrichment,
        "citations": cites,
        "origin": origin_summary(cites),
    }
    if enrich_meta:
        out["enrichment"] = enrich_meta
    return JSONResponse(out)
