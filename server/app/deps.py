from fastapi import Header, Depends
from sqlalchemy.orm import Session
from app.db import SessionLocal

def workspace_header(x_workspace: str | None = Header(default="default", alias="X-Workspace")) -> str:
    return x_workspace or "default"

def openai_key_header(x_openai_key: str | None = Header(default=None, alias="X-OpenAI-Key")) -> str | None:
    return x_openai_key

def get_db():
    db: Session | None = None
    try:
        db = SessionLocal()
        yield db
    finally:
        if db:
            db.close()
