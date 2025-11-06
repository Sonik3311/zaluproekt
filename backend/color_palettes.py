from dataclasses import dataclass


@dataclass
class Color:
    hex: int

@dataclass(frozen=True)
class ColorPalette:
    id: int
    colors: list[Color]
