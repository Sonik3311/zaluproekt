from dataclasses import dataclass
from color_palettes import ColorPalette, Color


@dataclass
class Pixel:
    x: int
    y: int
    color: Color

@dataclass
class PixelChange:
    x: int
    y: int
    color_id: int

class Board:
    def __init__(self, width: int, height: int, color_palette: ColorPalette):
        self._width: int = width
        self._height: int = height
        self._color_palette: ColorPalette = color_palette

        self._board: list[Pixel] = [
            Pixel(i % width, i // height, Color(0x000000)) for i in range(width * height)
        ]

        self._board_changes: list[PixelChange] = []

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def color_palette(self):
        return self._color_palette


    def get_pixel_range(self, x: int, y: int, x_end: int, y_end: int) -> list[Pixel]:
        pixels: list[Pixel] = []
        for i in range(x, x_end):
            for j in range(y, y_end):
                pixels.append(self._board[(j) * self.width + (i)])

        return pixels

    def get_color(self, col_id: int) -> Color:
        try:
            return self._color_palette.colors[col_id]
        except IndexError:
            return Color(0x000000)

    def set_pixel(self, x: int, y: int, color: int):
        i = y * self.width + x
        self._board[i].color = self.get_color(color)

        self._board_changes.append(PixelChange(x,y, color))

        print(f"colored pixel {x},{y} with {color}")

    def get_changes(self) -> list[PixelChange]:
        return self._board_changes

    def clear_changes(self):
        self._board_changes = []

if __name__ == "__main__":
    ...
