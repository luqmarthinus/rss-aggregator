from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional

class FeedCreate(BaseModel):
    url: HttpUrl = Field(..., example="https://hnrss.org/newest")

class FeedOut(BaseModel):
    id: int
    url: str
    title: Optional[str]
    added_at: datetime
    last_fetch_at: Optional[datetime]

class ArticleOut(BaseModel):
    id: int
    feed_id: int
    title: str
    link: str
    summary: Optional[str]
    published_at: Optional[datetime]
    is_read: bool

class ArticleReadUpdate(BaseModel):
    is_read: bool