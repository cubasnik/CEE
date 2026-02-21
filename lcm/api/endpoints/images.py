from fastapi import APIRouter

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/")
async def list_images():
    return []
