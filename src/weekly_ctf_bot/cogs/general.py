import time
from datetime import timedelta

from discord import Color, Embed, Interaction, app_commands
from discord.ext import commands

from .. import ChallengeBot


class General(commands.Cog):
    start_time: float | None = None

    def __init__(self, client: ChallengeBot):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        if self.start_time is None:
            self.start_time = time.time()

    @app_commands.command(
        name="uptime", description="Displays how long the bot has been running."
    )
    async def uptime(self, interaction: Interaction):
        if self.start_time is None:
            await interaction.response.send_message(
                "Uptime tracking has not started yet. Please wait a moment.",
                ephemeral=True,
            )
            return

        current_time = time.time()
        elapsed = int(round(current_time - self.start_time))
        uptime_text = str(timedelta(seconds=elapsed))

        embed = Embed(
            title=":clock: Uptime",
            description=f"The bot has been running for `{uptime_text}`.",
            color=Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(client: ChallengeBot):
    await client.add_cog(General(client))
