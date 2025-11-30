from pydantic import BaseModel
from functools import lru_cache
from color_palettes import ColorPalette, Color


class Pixel(BaseModel):
    x: int
    y: int
    color: Color


class PixelBoard:
    def __init__(self, width: int, height: int, color_palette: ColorPalette):
        print(f"[Board] Starting setup")
        self._width: int = width
        self._height: int = height
        self._color_palette: ColorPalette = color_palette

        print(f"[Board] - Generating board, x: {self._width}, y: {self._height}, {self._color_palette.colors[0]}")
        self._board: list[Pixel] = [
            Pixel(x=i % width, y=i // height, color=self._color_palette.colors[0]) for i in range(width * height)
        ]
        print(f"[Board] - Done!")
        self._board_changes: list[Pixel] = []
        print(f"[Board] Ready")

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def color_palette(self) -> ColorPalette:
        return self._color_palette

    @lru_cache(maxsize=128)
    def get_pixel_range(self, x: int, y: int, x_end: int, y_end: int) -> list[Pixel]:
        pixels: list[Pixel] = []
        for i in range(x, x_end):
            for j in range(y, y_end):
                pixels.append(self._board[(j) * self.width + (i)])

        return pixels

    @lru_cache(maxsize=20)
    def get_color(self, col_id: int) -> Color:
        try:
            return self._color_palette.colors[col_id]
        except IndexError:
            return self._color_palette.colors[0]

    def set_pixel(self, x: int, y: int, color_id: int):
        i = y * self.width + x
        color = self.get_color(color_id)
        self._board[i].color = color
        self._board_changes.append(Pixel(x=x, y=y, color=color))

    def get_changes(self) -> list[Pixel]:
        return self._board_changes

    def clear_changes(self):
        self._board_changes = []
