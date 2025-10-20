from pydantic import BaseModel


class BaseResponse(BaseModel):
    response: int


class BasePixel(BaseModel):
    x: int
    y: int


class BasePixelRange(BasePixel):
    x_end: int
    y_end: int


class ColorPixelRequestModel(BasePixel):
    color: int
