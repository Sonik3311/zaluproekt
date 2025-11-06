from color_palettes import (Color, ColorPalette)
import configparser
import glob
import os


class Config:
    def __init__(self, config_filepath: str):
        config = configparser.ConfigParser()
        _ = config.read(config_filepath)
        assert config.has_section("PIXELBOARD")


        self._palettes: list[ColorPalette] = self.load_color_palettes()

        self._board_width: int = int(config["PIXELBOARD"]["width"])
        self._board_height: int = int(config["PIXELBOARD"]["height"])
        self._color_palette_id: int = min(
            max(
                int(config["PIXELBOARD"]["color_palette_id"]),
                0
            ),
            len(self.palettes)
        )

    @property
    def palettes(self) -> list[ColorPalette]:
        return self._palettes

    @property
    def board_width(self) -> int:
        return self._board_width

    @property
    def board_height(self) -> int:
        return self._board_height

    @property
    def color_palette_id(self) -> int:
        return self._color_palette_id

    @staticmethod
    def load_color_palettes() -> list[ColorPalette]:

        config = configparser.ConfigParser()
        pattern = os.path.join("color_palettes", f"*.ini")

        palettes: list[ColorPalette] = []

        id = -1
        for file_path in glob.glob(pattern):
            try:
                _ = config.read(file_path)
                assert config.has_section("PALETTE")

                id += 1
                colors: list[Color] = [Color(int(config["PALETTE"][key], base=16)) for key in config["PALETTE"]]
                palettes.append(ColorPalette(id, colors))
            except IOError as e:
                print(e)
                continue

        return palettes


if __name__ == "__main__":
    conf = Config("config.ini")
    print(conf.palettes)
