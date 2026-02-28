import os
from dataclasses import MISSING, dataclass, field
from enum import StrEnum
from typing import Any, Self


class BotMode(StrEnum):
    DEVELOPMENT = "dev"
    PRODUCTION = "prod"

    @classmethod
    def parse(cls: type[Self], value: str) -> Self:
        try:
            return cls(value.lower())
        except ValueError:
            raise RuntimeError("Expected bot mode in config, got " + value)


@dataclass(frozen=True)
class Config:
    bot_token: str
    database_url: str = field(default="sqlite+aiosqlite:///challenges.db")
    bot_mode: BotMode = field(
        default=BotMode.DEVELOPMENT, metadata={"parser": BotMode.parse}
    )

    def __init__(self):
        for cur_field in self.__dataclass_fields__.values():
            name = cur_field.name.upper()
            value = os.getenv(name)

            if cur_field.default is MISSING and value is None:
                raise RuntimeError(f"Missing required environment variable: {name}")

            if value is not None:

                def parser(val: str) -> Any:
                    return cur_field.type(val)

                if "parser" in cur_field.metadata:
                    parser = cur_field.metadata["parser"]

                object.__setattr__(self, cur_field.name, parser(value.strip()))
