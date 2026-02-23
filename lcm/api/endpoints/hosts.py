from fastapi import APIRouter

router = APIRouter(prefix="/hosts", tags=["hosts"])


@router.get("/")
async def list_hosts():
    return []
