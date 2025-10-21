from fastapi import FastAPI, HTTPException
from models import (
    ColorPixelRequestModel,
    PixelBoardResponse,
)
from config import Config
from board import Board


config = Config("config.ini")
board = Board(config.board_width, config.board_height, 0)
server = FastAPI()


@server.post("/ColorPixel")
def set_pixel(req: ColorPixelRequestModel):
    if (req.x - config.board_width >= 0) or (req.y - config.board_height >= 0):
        raise HTTPException(status_code=400, detail="Invalid pixel position")

    # TODO: Сверка с БД по времени последнего

    board.set_pixel(req.x, req.y, (req.color, req.color, req.color))


@server.get("/GetPixels/{x}/{y}/{x_end}/{y_end}", response_model=PixelBoardResponse)
def get_pixels(x: int, y: int, x_end: int, y_end: int):
    print(x, x_end, y, y_end)
    if (x_end - config.board_width >= 0) or (y_end - config.board_height >= 0):
        raise HTTPException(status_code=400, detail="Invalid pixel end range")

    if (x - config.board_width >= 0) or (y - config.board_height >= 0):
        raise HTTPException(status_code=400, detail="Invalid pixel start range")

    if (x >= x_end) or (y >= y_end):
        raise HTTPException(status_code=400, detail="Invalid pixel range")

    return {
        "response_code": 200,
        "pixels": board.get_pixel_range(x, y, x_end, y_end),
    }
