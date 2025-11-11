from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import asyncio
import uvicorn
import uuid
import json
from jsonenchanced import EnhancedJSONEncoder
from collections import defaultdict
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
async def set_pixel(req: ColorPixelRequestModel):
    if (req.x - config.board_width >= 0) or (req.y - config.board_height >= 0):
        raise HTTPException(status_code=400, detail="Invalid pixel position")

    if (req.color >= len(board.color_palette.colors)):
        raise HTTPException(status_code=400, detail="Invalid color ID")

    # TODO: Сверка с БД по времени последнего закрашивания

    board.set_pixel(req.x, req.y, req.color)


    def new_messages():
        changes = board.get_changes()
        if len(changes) > 0:
            board.clear_changes()
            return len(changes) > 0, json.dumps(changes, cls=EnhancedJSONEncoder)
        return False, ""

    _, data = new_messages()

    await broadcast_to_all(data)


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

event_queues = defaultdict(set)

async def broadcast_to_all(message: str):
    for queue in event_queues["all"]:
        await queue.put(message)


# SSE соединение.
# Отвечает за стриминг изменений клиентам в реальном времени
@server.get('/stream')
async def message_stream(request: Request, response: Response):
    # Функция проверки новых сообщений
    queue = asyncio.Queue()

    async def event_generator():
        event_queues["all"].add(queue)
        try:

            while True:
                # If client was closed the connection
                if await request.is_disconnected():
                    print('disconnected')
                    break

                # Checks for new messages and return them to client if any
                new_data = await queue.get()

                #has_changes, new_data = new_messages()
                if new_data:
                    yield {
                            "event": "update",
                            "id": str(uuid.uuid4()),
                            "retry": RETRY_TIMEOUT,
                            "data": new_data
                    }
                response.headers['Content-type'] = "text/event-stream"
                response.headers['Cache-Control'] = "no-cache"
                response.headers['Connection'] = 'keep-alive'

                await asyncio.sleep(STREAM_DELAY)
        except asyncio.CancelledError:
            event_queues["all"].discard(queue)
        finally:
            event_queues["all"].discard(queue)


    return EventSourceResponse(event_generator())

server.mount("/site", StaticFiles(directory="../frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("main:server", host="127.0.0.1", port=8080, reload=True)
