import time
from datetime import timedelta
from platform import python_version

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from weekly_ctf_bot import ChallengeBot


class General(commands.Cog):
    start_time: float | None = None

    def __init__(self, client: ChallengeBot):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        if self.client.user is None:
            raise discord.errors.ClientException("Unable to get client's name!")
        else:
            logger.info(f"Logged in as {self.client.user.name}")

        logger.info(f"Discord.py API version: {discord.__version__}")
        logger.info(f"Python version: {python_version()}")

        self.start_time = time.time()

        logger.success("Bot is ready!")

    @app_commands.command(
        name="uptime", description="Displays how long the bot has been running."
    )
    async def uptime(self, interaction: discord.Interaction):
        if self.start_time is None:
            await interaction.response.send_message(
                "Uptime tracking has not started yet. Please wait a moment.",
                ephemeral=True,
            )
            return

        current_time = time.time()
        elapsed = int(round(current_time - self.start_time))
        uptime_text = str(timedelta(seconds=elapsed))

        embed = discord.Embed(
            title=":clock: Uptime",
            description=f"The bot has been running for `{uptime_text}`.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(client: ChallengeBot):
    await client.add_cog(General(client))
