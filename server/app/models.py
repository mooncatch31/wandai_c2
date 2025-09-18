from sqlalchemy import Column, String, Integer, JSON, ForeignKey, Index, UniqueConstraint, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from app.db import Base


class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(String(64), index=True, default="default")
    filename = Column(String(512))
    mime = Column(String(128))
    bytes = Column(Integer)
    storage_uri = Column(String(1024))  # file path or URL
    file_sha256 = Column(String(64), index=True)
    status = Column(String(32), default="uploaded")
    meta = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (Index("ix_docs_ws_sha", "workspace_id", "file_sha256"),)


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    idx = Column(Integer)
    text = Column(String)  # long text OK on PG
    token_count = Column(Integer)
    sha256 = Column(String(64))
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)


class Query(Base):
    __tablename__ = "queries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(String(64), index=True, default="default")
    question = Column(String)
    answer = Column(String, default="")
    confidence = Column(Integer, default=50)  # 0..100
    missing_info = Column(ARRAY(String), default=[])
    suggested_enrichment = Column(ARRAY(String), default=[])
    used_chunk_ids = Column(ARRAY(UUID(as_uuid=True)), default=[])
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.id", ondelete="CASCADE"), index=True)
    rating = Column(Integer)  # -1,0,1
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class DocumentReputation(Base):
    __tablename__ = "document_reputation"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(String(64), index=True, default="default")
    document_id = Column(UUID(as_uuid=True), index=True)
    up_count = Column(Integer, default=0)
    down_count = Column(Integer, default=0)
    score = Column(Integer, default=0)  # we’ll compute smoothed score as float-like int*100 if needed
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (
        UniqueConstraint("workspace_id", "document_id", name="uq_docrep_ws_doc"),
        Index("ix_docrep_ws_doc", "workspace_id", "document_id"),
    )
