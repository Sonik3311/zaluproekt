from dataclasses import dataclass


@dataclass
class Color:
    hex: int
    color_id: int
    def __str__(self):
        return "Color(#" + f"{format(self.hex, 'X').zfill(6)}, id:{self.color_id})"

@dataclass(frozen=True)
class ColorPalette:
    id: int
    colors: list[Color]
