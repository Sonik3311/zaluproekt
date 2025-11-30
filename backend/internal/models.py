from pydantic import BaseModel
from board import Pixel
from color_palettes import ColorPalette


class PixelBoardResponse(BaseModel):
    pixels: list[Pixel]

class ColorPaletteResponse(BaseModel):
    palette: ColorPalette

class BasePixelPos(BaseModel):
    x: int
    y: int


class BasePixelPosRange(BasePixelPos):
    x_end: int
    y_end: int


class ColorPixelRequestModel(BasePixelPos):
    color: int

class SettingsResponse(BaseModel):
    board_size: BasePixelPos
    palette: ColorPalette
