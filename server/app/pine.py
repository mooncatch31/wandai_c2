from typing import List, Dict, Any
from app.settings import settings
from app.embedder import embedding_dimension
from pinecone import Pinecone, ServerlessSpec

_pc = None
_index = None

def _client() -> Pinecone:
    global _pc
    if _pc:
        return _pc
    _pc = Pinecone(api_key=settings.pinecone_api_key)
    return _pc

def ensure_index():
    pc = _client()
    name = settings.pinecone_index
    dim = embedding_dimension()
    existing = [x["name"] for x in pc.list_indexes()]
    if name not in existing:
        pc.create_index(
            name=name,
            dimension=dim,
            metric="cosine",
            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
        )

def get_index():
    global _index
    if _index:
        return _index
    ensure_index()
    _index = _client().Index(settings.pinecone_index)
    return _index

def upsert_vectors(namespace: str, items: List[Dict[str, Any]]):
    """
    items: [{"id": "...", "values": [...], "metadata": {...}}, ...]
    """
    idx = get_index()
    idx.upsert(vectors=items, namespace=namespace)

def query_vectors(namespace: str, vector: List[float], top_k: int, include_metadata=True):
    idx = get_index()
    return idx.query(vector=vector, top_k=top_k, namespace=namespace, include_metadata=include_metadata)

def fetch_vectors(namespace: str, ids: List[str]):
    idx = get_index()
    return idx.fetch(ids=ids, namespace=namespace)
