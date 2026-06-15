"""Request models for the community API. Responses are plain dicts assembled in
the router (mirrors the rest of the codebase)."""
from typing import Optional

from pydantic import BaseModel, Field


class CreatePostRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    body: str = Field("", max_length=5000)
    image_key: Optional[str] = Field(None, max_length=200)
    image_type: Optional[str] = Field(None, max_length=100)


class CreateAnswerRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class VoteRequest(BaseModel):
    # 1 = upvote, -1 = downvote, 0 = remove vote
    value: int = Field(..., ge=-1, le=1)
