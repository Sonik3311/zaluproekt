from fastapi import FastAPI, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
import asyncio
import uvicorn
import uuid
import json
from jsonenchanced import EnhancedJSONEncoder
from models import (
    ColorPixelRequestModel,
    PixelBoardResponse,
    SettingsResponse,
)
from config import Config
from board import Board

STREAM_DELAY = 1  # second
RETRY_TIMEOUT = 15000  # millisecond

config = Config("config.ini")
board = Board(config.board_width, config.board_height, config.palettes[config.color_palette_id])
server = FastAPI()

@server.get("/settings", response_model=SettingsResponse)
def get_board_size():
    return {
        "board_size" : {
            "x" : board.width,
            "y" : board.height
        },
        "palette": board.color_palette
    }


@server.post("/ColorPixel")
def set_pixel(req: ColorPixelRequestModel):
    if (req.x - config.board_width >= 0) or (req.y - config.board_height >= 0):
        raise HTTPException(status_code=400, detail="Invalid pixel position")

    if (req.color >= len(board.color_palette.colors)):
        raise HTTPException(status_code=400, detail="Invalid color ID")

    # TODO: Сверка с БД по времени последнего закрашивания

    board.set_pixel(req.x, req.y, req.color)


@server.get("/GetPixels/{x}/{y}/{x_end}/{y_end}", response_model=PixelBoardResponse)
def get_pixels(x: int, y: int, x_end: int, y_end: int):
    print(x, x_end, y, y_end)
    if (x_end - config.board_width >= 0) or (y_end - config.board_height >= 0):
        raise HTTPException(status_code=400, detail="Invalid pixel end range")

    if (x - config.board_width >= 0) or (y - config.board_height >= 0):
        raise HTTPException(status_code=400, detail="Invalid pixel start range")

    if (x >= x_end) or (y >= y_end):
        raise HTTPException(status_code=400, detail="Invalid pixel range")

    print("starting fetch")
    pixels = board.get_pixel_range(x, y, x_end, y_end)
    print("end fetch")
    return {
        "pixels": pixels,
    }


# SSE соединение.
# Отвечает за стриминг изменений клиентам в реальном времени
@server.get('/stream')
async def message_stream(request: Request):
    # Функция проверки новых сообщений
    def new_messages():
        changes = board.get_changes()
        if len(changes) > 0:
            board.clear_changes()
            return len(changes) > 0, json.dumps(changes, cls=EnhancedJSONEncoder)
        return False, ""

    async def event_generator():
        while True:
            # If client was closed the connection
            if await request.is_disconnected():
                break

            # Checks for new messages and return them to client if any
            has_changes, new_data = new_messages()
            if has_changes:
                yield {
                        "event": "update",
                        "id": str(uuid.uuid4()),
                        "retry": RETRY_TIMEOUT,
                        "data": new_data
                }

            await asyncio.sleep(STREAM_DELAY)

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    uvicorn.run("main:server", host="127.0.0.1", port=8000, reload=False)
