from internal.shared_state import SharedState

_sst = SharedState()
config = _sst.config
pixel_board = _sst.board
db_manager = _sst.db_manager
is_volatile_mode = config.is_volatile_mode
