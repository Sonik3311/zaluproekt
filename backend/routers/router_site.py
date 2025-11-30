from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags = ["site"])

@router.get("/")
async def redirect_example():
    return RedirectResponse(url="/site")
