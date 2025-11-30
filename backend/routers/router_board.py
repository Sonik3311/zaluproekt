from fastapi import APIRouter, HTTPException
from dependencies import pixel_board, config
from internal.models import SettingsResponse, ColorPixelRequestModel, PixelBoardResponse
from internal.jsonenchanced import EnhancedJSONEncoder

from internal.board import Pixel

router = APIRouter(
    prefix="/api",
    tags=["board"]
)

@router.get("/settings", response_model=SettingsResponse)
def get_board_size():
    return {
        "board_size" : {
            "x" : pixel_board.width,
            "y" : pixel_board.height
        },
        "palette": pixel_board.color_palette
    }

@router.post("/ColorPixel")
async def set_pixel(req: ColorPixelRequestModel):
    if (req.x - config.board_width >= 0) or (req.y - config.board_height >= 0):
        raise HTTPException(status_code=400, detail="Invalid pixel position")

    if (req.color >= len(pixel_board.color_palette.colors)):
        raise HTTPException(status_code=400, detail="Invalid color ID")

    # TODO: Сверка с БД по времени последнего закрашивания

    pixel_board.set_pixel(req.x, req.y, req.color)

@router.get("/GetPixels/{x}/{y}/{x_end}/{y_end}", response_model=PixelBoardResponse)
def get_pixels(x: int, y: int, x_end: int, y_end: int):
    print(x, x_end, y, y_end)
    if (x_end - config.board_width >= 0) or (y_end - config.board_height >= 0):
        raise HTTPException(status_code=400, detail="Invalid pixel end range")

    if (x - config.board_width >= 0) or (y - config.board_height >= 0):
        raise HTTPException(status_code=400, detail="Invalid pixel start range")

    if (x >= x_end) or (y >= y_end):
        raise HTTPException(status_code=400, detail="Invalid pixel range")

    pixels = pixel_board.get_pixel_range(x, y, x_end, y_end)

    return {
        "pixels": pixels
    }
