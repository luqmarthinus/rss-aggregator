from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    # SQLite stores timestamps as naive UTC strings; mark them as UTC so the
    # JSON output carries an offset and browsers render the right local time.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class FeedCreate(BaseModel):
    url: HttpUrl = Field(..., examples=["https://hnrss.org/newest"])


class FeedOut(BaseModel):
    id: int
    url: str
    title: Optional[str]
    added_at: datetime
    last_fetch_at: Optional[datetime]
    unread_count: int = 0

    utc_dates = field_validator("added_at", "last_fetch_at")(_as_utc)


class ArticleOut(BaseModel):
    id: int
    feed_id: int
    title: str
    link: str
    summary: Optional[str]
    published_at: Optional[datetime]
    is_read: bool

    utc_dates = field_validator("published_at")(_as_utc)


class ArticleReadUpdate(BaseModel):
    is_read: bool
