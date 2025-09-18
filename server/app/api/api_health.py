from fastapi import APIRouter

router = APIRouter(prefix="/api")

@router.get("/")
def root():
    return {"ok": True, "name": "wandai-kb"}
