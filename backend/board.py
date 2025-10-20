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
