from color_palettes import Color, ColorPalette
import configparser
import glob
import os


class Config:
    def __init__(self, config_filepath: str):
        print(f"[Config] Starting to read '{config_filepath}'")
        config = configparser.ConfigParser()
        _ = config.read(config_filepath)
        assert config.has_section("PIXELBOARD")

        print("[Config] - Done!")
        self._board_width: int = int(config["PIXELBOARD"]["width"])
        self._board_height: int = int(config["PIXELBOARD"]["height"])
        print(f"[Config] Board width: {self._board_width}, {self._board_height}")

        print("[Config] Loading color palettes..")
        self._palettes: list[ColorPalette] = self.load_color_palettes()

        self._color_palette_id: int = min(
            max(
                int(config["PIXELBOARD"]["color_palette_id"]),
                0
            ),
            len(self.palettes) - 1
        )

        if len(self._palettes) < int(config["PIXELBOARD"]["color_palette_id"]) + 1:
            print(f"[Config] |::| Warning! selected palette ID in {config_filepath} is higher than amount of available palettes! ID clamped to the maximum allowed value")
            print(f"[Config] |::| Uncorrected selected palette ID: {int(config["PIXELBOARD"]["color_palette_id"])}")
        print(f"[Config] Selected palette ID: {self._color_palette_id}")


        print(f"[Config] Ready")

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
                id += 1
                _ = config.read(file_path)
                if not config.has_section("PALETTE"):
                    print(f"[Config] - |::| Palette under '{file_path}' is missing 'PALETTE' section. Skipping")
                    id -= 1
                    continue


                colors: list[Color] = [Color(int(config["PALETTE"][key], base=16), index) for index, key in enumerate(config["PALETTE"])]
                if len(colors) == 0:
                    print(f"[Config] |::| Palette {id} under '{file_path}' is empty. Appending black and white")
                    colors.append(Color(0x000000, 0))
                    colors.append(Color(0xFFFFFF, 1))
                palettes.append(ColorPalette(id, colors))
                print(f"[Config] - New palette {id} under '{file_path}', colors: {len(colors)}")
            except IOError as e:
                print(f"[Config] - |!!| Couldn't read file '{file_path}': {e}")
                continue

        return palettes
