from pydantic import BaseModel
from board import Pixel


class PixelBoardResponse(BaseModel):
    pixels: list[Pixel]


class BasePixelPos(BaseModel):
    x: int
    y: int


class BasePixelPosRange(BasePixelPos):
    x_end: int
    y_end: int


class ColorPixelRequestModel(BasePixelPos):
    color: int
