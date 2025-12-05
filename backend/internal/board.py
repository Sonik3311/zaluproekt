from functools import lru_cache
from color_palettes import ColorPalette, Color
from tqdm import tqdm
from config import Config
from db_manager import DBManager
from dataclasses import dataclass, asdict


@dataclass()
class Pixel:
    x: int
    y: int
    color: Color


class PixelBoard:
    def __init__(self, width: int, height: int, color_palette: ColorPalette, db_manager: DBManager, config: Config):
        print(f"[Board] Starting setup")
        self._width: int = width
        self._height: int = height
        self._color_palette: ColorPalette = color_palette

        print(f"[Board] - Generating board, x: {self._width}, y: {self._height}, {self._color_palette.colors[0]}")
        self._board: list[Pixel] = self.create_board_batched(self._width, self._height, self._color_palette.colors[0])

        if not config.is_volatile_mode:
            pixels = db_manager.get_pixels()
            print(f"[Board] Syncing Board with DB")
            for x, y, hex in tqdm(pixels, total=len(pixels)):
                color = int.from_bytes(hex, byteorder='big')
                color_id = self.get_color_id(color)
                self._board[y * self._width + x].color = self._color_palette.colors[color_id]

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
    def get_pixel_range(self, x: int, y: int, x_end: int, y_end: int, asdictionary: bool = False) -> list[Pixel]:
        pixels: list[Pixel] = []
        for i in range(x, x_end):
            for j in range(y, y_end):
                if asdictionary:
                    pixels.append(asdict(self._board[(j) * self.width + (i)]))
                else:
                    pixels.append(self._board[(j) * self.width + (i)])

        return pixels

    @lru_cache(maxsize=20)
    def get_color(self, col_id: int) -> Color:
        try:
            return self._color_palette.colors[col_id]
        except IndexError:
            return self._color_palette.colors[0]

    @lru_cache(maxsize=20)
    def get_color_id(self, color_hex: int) -> int:
        for i, c in enumerate(self._color_palette.colors):
            if c.hex == color_hex:
                return i
        return 0

    def set_pixel(self, x: int, y: int, color_id: int):
        i = y * self.width + x
        color = self.get_color(color_id)
        self._board[i].color = color
        self._board_changes.append(Pixel(x=x, y=y, color=color))

    def get_changes(self) -> list[Pixel]:
        return self._board_changes

    def clear_changes(self):
        self._board_changes = []

    @staticmethod
    def create_board_batched(width, height, color, batch_size=125000):
        total_pixels = width * height
        board = []

        with tqdm(total=total_pixels) as pbar:
            for start in range(0, total_pixels, batch_size):
                end = min(start + batch_size, total_pixels)
                batch = [
                    Pixel(x=i % width, y=i // width, color=color)  # Fixed
                    for i in range(start, end)
                ]
                board.extend(batch)
                pbar.update(end - start)

        return board
