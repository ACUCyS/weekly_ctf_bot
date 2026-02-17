import asyncio
import os
import sys
from datetime import datetime

import dotenv
from loguru import logger

from weekly_ctf_bot import ChallengeBot
from weekly_ctf_bot.config import BotMode, Config


async def async_main(config: Config):
    async with ChallengeBot(config) as client:
        await client.start(config.bot_token, reconnect=True)


def main():
    dotenv.load_dotenv()
    config = Config()

    log_dir = "./logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_filename = datetime.now().strftime("%Y-%m-%d-%H-%M-%S.log")
    level = "DEBUG" if config.bot_mode == BotMode.DEVELOPMENT else "INFO"

    logger.remove()  # remove default handler

    logger.add(sys.stderr, level="ERROR")
    logger.add(
        sys.stdout,
        level=level,
        # avoid duplication of errors in console, since stderr often is piped to stdout
        filter=lambda record: record["level"].no <= logger.level("WARNING").no,
    )

    logger.add(
        os.path.join(log_dir, log_filename),
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="2 MB",
        diagnose=config.bot_mode == BotMode.DEVELOPMENT,
    )

    asyncio.run(async_main(config))


if __name__ == "__main__":
    main()
