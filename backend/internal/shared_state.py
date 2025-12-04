from internal import board, config, db_manager


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
        if self.config.is_db_configured:
            self.db_manager = db_manager.DBManager(
                self.config.db_host,
                self.config.db_port,
                self.config.db_user,
                self.config.db_password,
                self.config.db_name,
                self.config.max_snapshots,
                self.config.clear_db_current,
                self.config.clear_db_snapshots
            )
        else:
            self.db_manager = None
        self.board = board.PixelBoard(self.config.board_width, self.config.board_height, self.config.palettes[self.config.color_palette_id], self.db_manager, self.config)
        print(f"[SharedState] Ready")
