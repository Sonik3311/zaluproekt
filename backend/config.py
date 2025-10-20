import configparser


class Config:
    def __init__(self, config_filepath: str):
        config = configparser.ConfigParser()
        _ = config.read(config_filepath)

        assert config.has_section("PIXELBOARD")

        # Access values from sections
        self.board_width: int = int(config["PIXELBOARD"]["width"])
        self.board_height: int = int(config["PIXELBOARD"]["height"])
        self.color_palette_id: int = int(config["PIXELBOARD"]["color_palette_id"])
