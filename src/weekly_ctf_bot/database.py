from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence
from urllib.parse import quote, unquote

from sqlalchemy import (
    BIGINT,
    TEXT,
    VARCHAR,
    Dialect,
    ForeignKey,
    TypeDecorator,
    delete,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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

        if value == "":
            return []

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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR(32), unique=True)
    description: Mapped[str] = mapped_column(TEXT)
    visible: Mapped[bool]
    flag: Mapped[str] = mapped_column(VARCHAR(MAX_FLAG_LENGTH))
    files: Mapped[list[File]] = mapped_column(FileList)
    url: Mapped[str] = mapped_column(VARCHAR(64))
    start: Mapped[datetime] = mapped_column(Timestamp)
    finish: Mapped[datetime] = mapped_column(Timestamp)
    # submissions: Mapped[list[Submission]] = relationship(back_populates="challenge")


class Submission(Base):
    __tablename__ = "submission"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT)
    timestamp: Mapped[datetime] = mapped_column(Timestamp)
    flag: Mapped[str] = mapped_column(VARCHAR(MAX_FLAG_LENGTH))
    is_correct: Mapped[bool]
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenge.id"))
    # challenge: Mapped[Challenge] = relationship(back_populates="submissions")


class Database:
    engine: AsyncEngine
    session_maker: async_sessionmaker[AsyncSession]

    def __init__(self, url: str):
        self.engine = create_async_engine(url)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    @staticmethod
    async def create(url: str) -> Database:
        db = Database(url)

        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        return db

    async def get_active_challenges(self) -> Sequence[Challenge]:
        async with self.session_maker() as session:
            now = datetime.now().replace(tzinfo=timezone.utc)
            stmt = (
                select(Challenge)
                .where(Challenge.visible)
                .where(Challenge.start <= now)
                .where(Challenge.finish > now)
                .order_by(Challenge.start)
            )

            return (await session.scalars(stmt)).all()

    async def get_challenge(self, name: str) -> Challenge | None:
        async with self.session_maker() as session:
            stmt = select(Challenge).where(
                func.lower(Challenge.name) == func.lower(name)
            )

            return (await session.scalars(stmt)).first()

    async def get_challenge_by_id(self, id: int) -> Challenge | None:
        async with self.session_maker() as session:
            stmt = select(Challenge).where(Challenge.id == id)
            return (await session.scalars(stmt)).first()

    async def add_challenge(self, chal: Challenge):
        async with self.session_maker.begin() as session:
            session.add(chal)

    async def update_challenge(self, id: int, **kwargs: dict[str, Any]):
        async with self.session_maker.begin() as session:
            stmt = update(Challenge).where(Challenge.id == id).values(**kwargs)
            await session.execute(stmt)

    async def delete_challenge(self, id: int):
        async with self.session_maker.begin() as session:
            stmt = delete(Challenge).where(Challenge.id == id)
            await session.execute(stmt)

    async def get_submissions(
        self, challenge_id: int, user_id: int | None = None
    ) -> Sequence[Submission]:
        async with self.session_maker() as session:
            stmt = select(Submission).where(Submission.challenge_id == challenge_id)
            if user_id is not None:
                stmt = stmt.where(Submission.user_id == user_id)

            return (await session.scalars(stmt)).all()

    async def get_solve(self, challenge_id: int, user_id: int) -> Submission | None:
        async with self.session_maker() as session:
            stmt = (
                select(Submission)
                .where(Submission.is_correct)
                .where(Submission.challenge_id == challenge_id)
                .where(Submission.user_id == user_id)
            )

            return (await session.scalars(stmt)).first()

    async def add_submission(
        self, challenge: Challenge, user_id: int, flag: str
    ) -> bool:
        is_correct = flag.lower() == challenge.flag.lower()

        async with self.session_maker.begin() as session:
            session.add(
                Submission(
                    user_id=user_id,
                    timestamp=datetime.now(),
                    flag=flag,
                    is_correct=is_correct,
                    challenge_id=challenge.id,
                )
            )

        return is_correct

    async def delete_submission(self, id: int):
        async with self.session_maker.begin() as session:
            stmt = delete(Submission).where(Submission.id == id)
            await session.execute(stmt)

    async def close(self):
        await self.engine.dispose()
