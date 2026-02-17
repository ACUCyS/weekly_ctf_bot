from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, unquote

from sqlalchemy import BIGINT, TEXT, VARCHAR, Dialect, TypeDecorator, select
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

MAX_FLAG_LENGTH = 32


class Base(AsyncAttrs, DeclarativeBase):
    pass


@dataclass(slots=True)
class File:
    filename: str
    url: str


def uri_encode(uri: str) -> str:
    return quote(uri, safe="-_.!~*'();/?:@&=+$,#")


class FileList(TypeDecorator[list[File]]):
    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value: list[File] | None, dialect: Dialect) -> Any:
        if value is None:
            return ""

        return "^".join(
            [f"{uri_encode(file.filename)} {uri_encode(file.url)}" for file in value]
        )

    def process_result_value(
        self, value: Any | None, dialect: Dialect
    ) -> list[File] | None:
        if value is None:
            return None

        return [
            File(
                filename=unquote((file_pieces := file.split(" "))[0]),
                url=unquote(file_pieces[1]),
            )
            for file in value.split("^")
        ]


class Timestamp(TypeDecorator[datetime]):
    impl = BIGINT
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> Any:
        if value is None:
            return 0

        return int(value.replace(tzinfo=timezone.utc).timestamp() * 1000)

    def process_result_value(
        self, value: Any | None, dialect: Dialect
    ) -> datetime | None:
        if value is None or value == 0:
            return None

        return datetime.fromtimestamp(value / 1000, timezone.utc)


class Challenge(Base):
    __tablename__ = "challenge"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(VARCHAR(32))
    description: Mapped[str] = mapped_column(TEXT)
    flag: Mapped[str] = mapped_column(VARCHAR(MAX_FLAG_LENGTH))
    files: Mapped[list[File]] = mapped_column(FileList)
    url: Mapped[str] = mapped_column(VARCHAR(64))
    start: Mapped[datetime] = mapped_column(Timestamp)
    finish: Mapped[datetime | None] = mapped_column(Timestamp)
    submissions: Mapped[list[Submission]] = relationship(back_populates="challenge")


class Submission(Base):
    __tablename__ = "submission"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BIGINT)
    timestamp: Mapped[datetime] = mapped_column(Timestamp)
    flag: Mapped[str] = mapped_column(VARCHAR(MAX_FLAG_LENGTH))
    challenge: Mapped[Challenge] = relationship(back_populates="submissions")


class Database:
    engine: AsyncEngine
    session_maker: async_sessionmaker[AsyncSession]

    def __init__(self, url: str):
        self.engine = create_async_engine(url)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def close(self):
        await self.engine.dispose()
