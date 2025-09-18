from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.settings import settings
from app.db import Base, engine
from app.api.api_health import router as health
from app.api.api_upload import router as upload
from app.api.api_docs import router as docs
from app.api.api_qna import router as qna
from app.api.api_feedback import router as feedback

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(health, tags=["health"])
app.include_router(upload, tags=["upload"])
app.include_router(docs, tags=["documents"])
app.include_router(qna, tags=["ask"])
app.include_router(feedback, tags=["feedback"])
