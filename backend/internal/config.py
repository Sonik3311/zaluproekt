from color_palettes import Color, ColorPalette
import configparser
import glob
import os
from colorama import Fore, Back, Style, init
init(autoreset=True)


class Config:
    def __init__(self, config_filepath: str):
        print(f"[Config] Starting to read '{config_filepath}'")
        config = configparser.ConfigParser()
        _ = config.read(config_filepath)
        if not config.has_section("PIXELBOARD"):
            print(f"[Config] {Back.RED + Style.BRIGHT}|!!| ERROR! No 'PIXELBOARD' section found in config file |!!|")
            print("Perhaps, you put in the wrong file path?")
            assert False, "No 'PIXELBOARD' section found"

        print("[Config] - Done!")
        self._board_width: int = int(config["PIXELBOARD"]["width"])
        self._board_height: int = int(config["PIXELBOARD"]["height"])
        print(f"[Config] Board width: {self._board_width}, {self._board_height}")

        print("[Config] Loading color palettes..")
        self._palettes: list[ColorPalette] = self.load_color_palettes()
        if len(self._palettes) == 0:
            print(f"[Config] {Back.RED + Style.BRIGHT}|!!| ERROR! No color palettes found! |!!|")
            assert False, "No color palettes found"


        self._color_palette_id: int = min(
            max(
                int(config["PIXELBOARD"]["color_palette_id"]),
                0
            ),
            len(self.palettes) - 1
        )

        if len(self._palettes) < int(config["PIXELBOARD"]["color_palette_id"]) + 1:
            print(f"[Config] {Fore.YELLOW}|::| Warning! selected palette ID in {config_filepath} is higher than amount of available palettes! ID clamped to the maximum allowed value")
            print(f"[Config] {Fore.YELLOW}|::| Uncorrected selected palette ID: {int(config["PIXELBOARD"]["color_palette_id"])}")
        print(f"[Config] Selected palette ID: {self._color_palette_id}")

        #Load [DATABASE] section
        if config.has_section("DATABASE"):
            try:
                self._db_host = config["DATABASE"]["host"]
                self._db_port = int(config["DATABASE"]["port"])
                self._db_name = config["DATABASE"]["name"]
                self._db_user = config["DATABASE"]["user"]
                self._db_password = config["DATABASE"]["password"]
                self._db_enabled = True
            except KeyError as e:
                print(f"[Config] {Fore.YELLOW}|::| Warning! DATABASE section is incomplete in {config_filepath}!")
                print(f"[Config] {Fore.YELLOW}|::| Working in VOLATILE mode")
                self._db_enabled = False
        else:
            print(f"[Config] {Fore.YELLOW}|::| Warning! DATABASE section not found in {config_filepath}!")
            print(f"[Config] {Fore.YELLOW}|::| Working in VOLATILE mode")
            self._db_enabled = False

        if config.has_section("SNAPSHOT") and self._db_enabled:
            self._snapshot_interval = int(config["SNAPSHOT"]["interval"]) or 300
            self._max_snapshots = int(config["SNAPSHOT"]["max_snapshots"]) or 100
            self._clear_current = config["SNAPSHOT"].getboolean("clear_current", False)
            self._clear_snapshots = config["SNAPSHOT"].getboolean("clear_snapshots", False)

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

    @property
    def is_volatile_mode(self) -> bool:
        return not self._db_enabled

    @property
    def is_db_configured(self) -> bool:
        return self._db_enabled

    @property
    def db_host(self) -> str:
        return self._db_host

    @property
    def db_port(self) -> int:
        return self._db_port

    @property
    def db_user(self) -> str:
        return self._db_user

    @property
    def db_password(self) -> str:
        return_password = self._db_password or ""
        self._db_password = None
        return return_password

    @property
    def db_name(self) -> str:
        return self._db_name

    @property
    def snapshot_interval(self) -> int:
        return self._snapshot_interval

    @property
    def max_snapshots(self) -> int:
        return self._max_snapshots

    @property
    def clear_db_current(self) -> bool:
        return self._clear_current

    @property
    def clear_db_snapshots(self) -> bool:
        return self._clear_snapshots

    def set_volatile_mode(self):
        self._db_enabled = False

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
                triggered_error = False
                if not config.has_section("PALETTE"):
                    print(f"[Config] {Fore.YELLOW} - |::| Palette under '{file_path}' is missing 'PALETTE' section. Skipping")
                    id -= 1
                    continue

                colors: list[Color] = []
                error_counter = 0
                for key in config["PALETTE"]:
                    try:
                        colors.append(Color(int(config["PALETTE"][key], base=16), len(colors)))
                    except ValueError as e:
                        triggered_error = True
                        error_counter += 1

                if len(colors) == 0:
                    print(f"[Config] {Fore.YELLOW} - |::| Palette {id} under '{file_path}' is empty. Appending black and white")
                    colors.append(Color(0x000000, 0))
                    colors.append(Color(0xFFFFFF, 1))
                    triggered_error = True
                palettes.append(ColorPalette(id, colors))

                if triggered_error:
                    print(f"[Config] {Fore.YELLOW}- |::| Palette {id} under '{file_path}' loaded with errors ({error_counter})!")
                else:
                    print(f"[Config] - Palette {id} under '{file_path}' successfully loaded!")
            except Exception as e:
                print(f"[Config] {Fore.YELLOW}- |!!| Couldn't read file '{file_path}': {e}")
                continue
            finally:
                config.clear()

        return palettes
