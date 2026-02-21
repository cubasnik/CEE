from fastapi import APIRouter

router = APIRouter(prefix="/networks", tags=["networks"])


@router.get("/")
async def list_networks():
    return []
