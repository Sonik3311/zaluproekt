from fastapi import FastAPI, HTTPException
from .models import BaseResponse, ColorPixelRequestModel
from .config import Config


config = Config("config.ini")
server = FastAPI()


@server.get("/ColorPixel", response_model=BaseResponse)
def set_pixel(req: ColorPixelRequestModel):
    if (req.x - config.board_width < 0) or (req.y - config.board_height < 0):
        raise HTTPException(status_code=400, detail="Invalid pixel position")

    # TODO: Сверка с БД по времени последнего

    print("Set pixel at")


if __name__ == "__main__":
    ...
