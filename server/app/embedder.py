from __future__ import annotations
from typing import List
from app.settings import settings

# Lazy global singleton
_model = None
_dim = None

def embedding_dimension() -> int:
    global _dim
    if _dim is not None:
        return _dim
    # mini map of known dims (avoid loading just to know dim)
    known = {
        "intfloat/e5-small-v2": 384,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "intfloat/e5-base-v2": 768,
    }
    if settings.embedding_model in known:
        _dim = known[settings.embedding_model]
        return _dim
    # fallback: load model and check
    _load()
    return _dim  # type: ignore

def _load():
    global _model, _dim
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.embedding_model)
        _dim = _model.get_sentence_embedding_dimension()

def embed_texts(texts: List[str]) -> List[List[float]]:
    if settings.embedding_provider.lower() != "local":
        # You can add providers 'openai' or 'ollama' here if desired
        _load()
        return _model.encode(texts, normalize_embeddings=True).tolist()
    _load()
    return _model.encode(texts, normalize_embeddings=True).tolist()
