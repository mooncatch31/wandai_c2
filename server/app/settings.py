from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    app_name: str = Field(default="wandai-kb", alias="APP_NAME")
    app_contact: str | None = Field(default=None, alias="APP_CONTACT")

    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"], alias="CORS_ORIGINS")

    database_url: str = Field(alias="DATABASE_URL")

    pinecone_api_key: str = Field(alias="PINECONE_API_KEY")
    pinecone_index: str = Field(alias="PINECONE_INDEX")
    pinecone_cloud: str = Field(default="aws", alias="PINECONE_CLOUD")
    pinecone_region: str = Field(default="us-west-2", alias="PINECONE_REGION")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="intfloat/e5-small-v2", alias="EMBEDDING_MODEL")

    chunk_size_tokens: int = Field(default=350, alias="CHUNK_SIZE_TOKENS")
    chunk_overlap_tokens: int = Field(default=60, alias="CHUNK_OVERLAP_TOKENS")
    topk: int = Field(default=30, alias="TOPK")
    max_context_chunks: int = Field(default=8, alias="MAX_CONTEXT_CHUNKS")

    # enrichment
    auto_enrich_enabled: bool = Field(default=False, alias="AUTO_ENRICH_ENABLED")
    auto_enrich_min_conf: float = Field(default=0.35, alias="AUTO_ENRICH_MIN_CONF")
    auto_enrich_max_docs: int = Field(default=2, alias="AUTO_ENRICH_MAX_DOCS")
    auto_enrich_max_per_topic: int = Field(default=1, alias="AUTO_ENRICH_MAX_PER_TOPIC")
    google_cse_api_key: str | None = Field(default=None, alias="GOOGLE_CSE_API_KEY")
    google_cse_cx: str | None = Field(default=None, alias="GOOGLE_CSE_CX")

    max_upload_mb: int = Field(default=30, alias="MAX_UPLOAD_MB")
    max_files: int = Field(default=10, alias="MAX_FILES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
