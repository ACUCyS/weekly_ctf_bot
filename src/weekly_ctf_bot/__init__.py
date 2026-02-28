import importlib.metadata
import traceback
from asyncio import Task, get_running_loop, sleep
from datetime import datetime, timezone
from platform import python_version
from typing import Any, Awaitable

from discord import (
    ClientException,
    Color,
    Embed,
    Intents,
    Interaction,
    InteractionResponded,
    TextChannel,
    app_commands,
)
from discord import __version__ as discord_version
from discord.ext import commands
from loguru import logger

from .config import BotMode, Config
from .database import Challenge, Database


def run_at[R](task: Awaitable[R], time: datetime) -> Task[R]:
    async def wait_until(task: Awaitable[R], time: datetime) -> R:
        now = datetime.now(timezone.utc)
        await sleep((time - now).total_seconds())
        return await task

    loop = get_running_loop()
    return loop.create_task(wait_until(task, time))


class ChallengeBot(commands.Bot):
    config: Config
    database: Database
    start_events: dict[int, Task[None]] = {}
    finish_events: dict[int, Task[None]] = {}

    def __init__(self, config: Config, database: Database):
        self.config = config
        self.database = database

        logger.info(f"Bot version: {importlib.metadata.version(__name__)}")
        logger.info(f"Discord.py API version: {discord_version}")
        logger.info(f"Python version: {python_version()}")

        intents = Intents.default()
        super().__init__(command_prefix=".", intents=intents, help_command=None)

    async def setup_hook(self):
        self.tree.on_error = self.on_app_command_error

        COGS = ["general", "challenges"]

        for cog in COGS:
            await self.load_extension(f"{__name__}.cogs.{cog}")
            logger.debug(f"Loaded: bot.cogs.{cog}")

        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} Slash Commands globally.")
        logger.debug(f"Synced: {[cmd.name for cmd in synced]}")

        for challenge in await self.database.get_upcoming_challenges():
            self.add_start_event(challenge)

        for challenge in await self.database.get_active_challenges(server_id=None):
            self.add_finish_event(challenge)

    async def on_ready(self):
        if self.user is None:
            raise ClientException("Unable to get client's name!")
        else:
            logger.success(f"Logged in as {self.user.name}")

    def add_start_event(self, challenge: Challenge):
        self.start_events[challenge.id] = run_at(
            self.start_event(challenge.id), challenge.start
        )

    def add_finish_event(self, challenge: Challenge):
        self.finish_events[challenge.id] = run_at(
            self.finish_event(challenge.id), challenge.finish
        )

    async def start_event(self, challenge_id: int):
        del self.start_events[challenge_id]

        challenge = await self.database.get_challenge(challenge_id)
        if challenge is None:
            return

        self.add_finish_event(challenge)

        server = await self.database.get_server(challenge.server_id)
        if server.announcement_channel == 0:
            return

        channel = await self.fetch_channel(server.announcement_channel)
        assert isinstance(channel, TextChannel)

        embed = Embed(
            title=f"{challenge.name} has opened!",
            description=f"""
{challenge.description}

*Closes at:* <t:{int(challenge.finish.timestamp())}:s>
Use `/challenge` to view more info and submit the flag.
""",
            color=Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        await channel.send(
            "@everyone" if server.ping_role == 0 else f"<@&{server.ping_role}>",
            embed=embed,
        )

    async def finish_event(self, challenge_id: int):
        del self.finish_events[challenge_id]

        challenge = await self.database.get_challenge(challenge_id)
        if challenge is None:
            return

        solves = sorted(
            filter(
                lambda submission: submission.is_correct,
                list(await self.database.get_submissions(challenge.id)),
            ),
            key=lambda submission: submission.timestamp,
        )

        server = await self.database.get_server(challenge.server_id)
        if server.announcement_channel == 0:
            return

        channel = await self.fetch_channel(server.announcement_channel)
        assert isinstance(channel, TextChannel)

        description = challenge.description
        if len(solves) == 0:
            description += "\n\nNo one managed to solve the challenge!"
        else:
            description += f"""

The following players solved the challenge: {", ".join([f"<@{solve.user_id}>" for solve in solves])}!
-# In order from first to solve, to last to solve.
"""

        embed = Embed(
            title=f"{challenge.name} has closed!",
            description=description,
            color=Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        await channel.send(
            "@everyone" if server.ping_role == 0 else f"<@&{server.ping_role}>",
            embed=embed,
        )

    async def on_app_command_error(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ):
        await handle_error(interaction, error, self.config)


async def handle_error(interaction: Interaction, error: Exception, config: Config):
    async def response_func(*args: Any, **kwargs: Any):
        # for some reason, just checking interaction.response.is_done does not work
        # and interaction.followup is in invalid state until a response is sent
        try:
            await interaction.response.send_message(*args, **kwargs)
        except InteractionResponded:
            await interaction.followup.send(*args, **kwargs)

    if isinstance(error, app_commands.CommandInvokeError):
        original = error.original
        err_traceback = error.original.__traceback__
        error_loc = error.command.name

        if err_traceback is not None:
            while err_traceback.tb_next is not None:
                err_traceback = err_traceback.tb_next

            frame = err_traceback.tb_frame
            while f"src/{__name__}" not in frame.f_code.co_filename.replace("\\", "/"):
                frame = frame.f_back
                if frame is None:
                    break

            if frame is not None:
                error_loc += f" - {frame.f_code.co_qualname}:{frame.f_lineno}"

        logger.error(f"[{error_loc}] {type(original).__name__}: {original}")

        extra = ""
        if config.bot_mode == BotMode.DEVELOPMENT:
            extra = f"\n```{''.join(traceback.format_exception(error.original))}```"

        await response_func(
            "An unexpected internal error occurred while executing the command" + extra,
            ephemeral=True,
        )

    elif isinstance(error, app_commands.CommandOnCooldown):
        await response_func(
            "This command is on cooldown, please try again later.", ephemeral=True
        )

    elif isinstance(error, app_commands.CheckFailure):
        await response_func(
            "You don't have permission to use this command.", ephemeral=True
        )

    else:
        logger.error(f"[Bot Error] {type(error).__name__}: {error}")

        extra = ""
        if config.bot_mode == BotMode.DEVELOPMENT:
            extra = f"\n```{''.join(traceback.format_exception(error))}```"

        await response_func(
            "An unknown error occurred." + extra,
            ephemeral=True,
        )
