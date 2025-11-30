from sys import path as syspath
import argparse

syspath.append("../new_back/internal")
syspath.append("../new_back/routers")

import routers.router_board as router_board
import routers.router_broadcast as router_broadcast
import routers.router_site as router_site
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await router_broadcast.create_broadcast_task()
    yield

server = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost",
    "http://localhost:8080",
]

server.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


server.include_router(router_board.router)
server.include_router(router_broadcast.router)
server.include_router(router_site.router)

server.mount("/site", StaticFiles(directory="../frontend", html=True), name="front")

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str)
    parser.add_argument("--port", type=int)
    parser.add_argument("--hotreload", action="store_true")
    args = parser.parse_args()

    default_host = "127.0.0.1"
    default_port = 8080

    uvicorn.run("main:server", host=args.host or default_host, port=args.port or default_port, reload=args.hotreload)
