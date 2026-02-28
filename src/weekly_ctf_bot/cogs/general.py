import time
from datetime import timedelta

from discord import Color, Embed, Interaction, app_commands
from discord.ext import commands

from .. import ChallengeBot
from ..ui import ServerSettingsModal, resolve_server


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

    @app_commands.command(
        name="server-settings", description="Set the server settings."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def server_settings(self, interaction: Interaction):
        assert interaction.guild_id is not None
        await interaction.response.send_modal(
            ServerSettingsModal(
                self.client, await resolve_server(self.client, interaction.guild_id)
            )
        )


async def setup(client: ChallengeBot):
    await client.add_cog(General(client))
