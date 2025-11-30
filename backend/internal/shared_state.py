from internal import board, config


class SharedState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
          cls._instance = super(SharedState, cls).__new__(cls)
          cls._instance.__init__(True)
        return cls._instance

    def __init__(self, should_actually_do_stuff: bool = False):
        if not should_actually_do_stuff:
            return
        print(f"[SharedState] Init")
        self.config = config.Config("config.ini")
        self.board = board.PixelBoard(self.config.board_width, self.config.board_height, self.config.palettes[self.config.color_palette_id])
        print(f"[SharedState] Ready")
