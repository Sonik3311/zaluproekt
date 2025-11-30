from multiprocessing import Event
from fastapi import APIRouter, Request, Response
from internal.jsonenchanced import EnhancedJSONEncoder
from dependencies import pixel_board
from sse_starlette.sse import EventSourceResponse
from collections import defaultdict
import asyncio
import uuid
import json


STREAM_DELAY = 0.5  # second
RETRY_TIMEOUT = 15000  # millisecond

router = APIRouter(
    prefix="/api",
    tags=["sse_broadcast"]
)


broadcast_task = None
async def create_broadcast_task():
    global broadcast_task
    broadcast_task = asyncio.create_task(periodic_broadcast())

event_queues = defaultdict(set)

async def broadcast_to_all(data):
    global event_queues
    for queue in event_queues["all"]:
        await queue.put(data)

# SSE соединение.
# Отвечает за стриминг изменений клиентам в реальном времени
@router.get('/stream')
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

                new_data = await queue.get()
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

async def periodic_broadcast():
    def new_messages():
        changes = pixel_board.get_changes()
        if len(changes) > 0:
            pixel_board.clear_changes()
            return len(changes) > 0, json.dumps(changes, cls=EnhancedJSONEncoder)
        return False, ""

    while True:
        try:
            await asyncio.sleep(STREAM_DELAY)
            has_changes, new_data = new_messages()
            if has_changes:
                await broadcast_to_all(new_data)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Broadcast error: {e}")
