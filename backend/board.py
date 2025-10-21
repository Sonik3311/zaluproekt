from dataclasses import dataclass


@dataclass
class Pixel:
    x: int
    y: int
    color: tuple[int, int, int]


class Board:
    def __init__(self, width: int, height: int, color_palette: int):
        self.width: int = width
        self.height: int = height

        self._board: list[Pixel] = [
            Pixel(i % width, i // height, (0, 0, 0)) for i in range(width * height)
        ]

    def get_pixel_range(self, x: int, y: int, x_end: int, y_end: int) -> list[Pixel]:
        pixels: list[Pixel] = []
        for i in range(x, x_end):
            for j in range(y, y_end):
                pixels.append(self._board[(j + y) * self.width + (i + x)])

        return pixels

    def set_pixel(self, x: int, y: int, color: tuple[int, int, int]):
        i = y * self.width + x
        self._board[i].color = color

        print(f"colored pixel {x},{y} with {color}")
