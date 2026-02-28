from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Self

from discord import ChannelType, Color, Embed, Interaction, Role, TextChannel, ui

from .. import ChallengeBot, handle_error


@dataclass
class ResolvedServer:
    id: int
    author_role: Role | None
    ping_role: Role | None
    announcement_channel: TextChannel | None
    solve_channel: TextChannel | None


async def resolve_server(client: ChallengeBot, server_id: int) -> ResolvedServer:
    server = await client.database.get_server(server_id)
    guild = await client.fetch_guild(server_id)

    author_role = (
        None if server.author_role == 0 else await guild.fetch_role(server.author_role)
    )

    ping_role = (
        None if server.ping_role == 0 else await guild.fetch_role(server.ping_role)
    )

    announcement_channel = None
    if server.announcement_channel != 0:
        announcement_channel = await guild.fetch_channel(server.announcement_channel)
        assert isinstance(announcement_channel, TextChannel)

    solve_channel = None
    if server.solve_channel != 0:
        solve_channel = await guild.fetch_channel(server.solve_channel)
        assert isinstance(solve_channel, TextChannel)

    return ResolvedServer(
        server_id, author_role, ping_role, announcement_channel, solve_channel
    )


class ServerSettingsModal(ui.Modal):
    def __init__(self, client: ChallengeBot, server: ResolvedServer):
        super().__init__(title="Server settings")

        self.client = client
        self.server_id = server.id

        self.author_role: ui.RoleSelect[Self] = ui.RoleSelect(
            required=False,
            default_values=[] if server.author_role is None else [server.author_role],
        )

        self.ping_role: ui.RoleSelect[Self] = ui.RoleSelect(
            required=False,
            default_values=[] if server.ping_role is None else [server.ping_role],
        )

        self.announcement_channel: ui.ChannelSelect[Self] = ui.ChannelSelect(
            required=False,
            channel_types=[ChannelType.text],
            default_values=[]
            if server.announcement_channel is None
            else [server.announcement_channel],
        )

        self.solve_channel: ui.ChannelSelect[Self] = ui.ChannelSelect(
            required=False,
            channel_types=[ChannelType.text],
            default_values=[]
            if server.solve_channel is None
            else [server.solve_channel],
        )

        self.add_item(
            ui.Label(
                text="What role can add/edit challenges?", component=self.author_role
            )
        )

        self.add_item(
            ui.Label(
                text="What role should be pinged for announcements?",
                description="If not provided, @everyone will be pinged.",
                component=self.ping_role,
            )
        )

        self.add_item(
            ui.Label(
                text="What channel should announcements be sent to?",
                component=self.announcement_channel,
            )
        )

        self.add_item(
            ui.Label(
                text="What channel should solves be posted to?",
                component=self.solve_channel,
            )
        )

    async def on_error(self, interaction: Interaction, error: Exception):
        await handle_error(interaction, error, self.client.config)

    async def on_submit(self, interaction: Interaction) -> None:
        await self.client.database.update_server(
            self.server_id,
            author_role=0
            if len(self.author_role.values) == 0
            else self.author_role.values[0].id,
            ping_role=0
            if len(self.ping_role.values) == 0
            else self.ping_role.values[0].id,
            announcement_channel=0
            if len(self.announcement_channel.values) == 0
            else self.announcement_channel.values[0].id,
            solve_channel=0
            if len(self.solve_channel.values) == 0
            else self.solve_channel.values[0].id,
        )

        embed = Embed(
            title="Server settings",
            description="Successfully updated server settings!",
            color=Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
