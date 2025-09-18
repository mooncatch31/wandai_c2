from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from typing import List
from sqlalchemy.orm import Session
from app.deps import get_db, workspace_header
from app.settings import settings
from app.ingest import store_and_ingest_file

router = APIRouter(prefix="/api")

@router.post("/upload")
async def upload(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    ws: str = Depends(workspace_header),
):
    if not files:
        raise HTTPException(400, "No files")
    if len(files) > settings.max_files:
        raise HTTPException(413, f"Too many files (max {settings.max_files})")

    results = []
    for f in files:
        content = await f.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > settings.max_upload_mb:
            results.append({"filename": f.filename, "status": "failed", "error": f"File > {settings.max_upload_mb}MB"})
            continue
        doc, status = store_and_ingest_file(db, workspace=ws, filename=f.filename, content=content, mime=f.content_type)
        results.append({"id": str(doc.id), "filename": doc.filename, "status": status})
    return {"workspace": ws, "documents": results}
