from typing import Literal

from pydantic import BaseModel, Field


SummaryMode = Literal["short", "detailed", "bullet"]


class SummarizeRequest(BaseModel):
    url: str = Field(default="")
    title: str = Field(default="")
    content: str = Field(min_length=200)
    mode: SummaryMode = Field(default="short")


class StreamEvent(BaseModel):
    event: Literal["progress", "partial", "done", "error"]
    message: str
    data: dict = Field(default_factory=dict)
