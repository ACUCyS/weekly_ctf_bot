from datetime import datetime, timezone
from typing import Self

from discord import Color, Embed, Interaction, TextChannel, ui

from .. import ChallengeBot, handle_error
from ..database import MAX_FLAG_LENGTH, Challenge


async def submit_flag(
    client: ChallengeBot, challenge: Challenge, flag: str, interaction: Interaction
):
    assert interaction.guild_id is not None

    TITLE = f":triangular_flag_on_post: Flag submission for {challenge.name}"

    solve = await client.database.get_solve(challenge.id, interaction.user.id)

    if solve is not None:
        embed = Embed(
            title=TITLE,
            description=f"You've already solved {challenge.name}!",
            color=Color.teal(),
            timestamp=datetime.now(timezone.utc),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    is_correct = await client.database.add_submission(
        challenge, interaction.user.id, flag
    )

    if is_correct:
        server = await client.database.get_server(interaction.guild_id)
        if server.solve_channel != 0:
            channel = await client.fetch_channel(server.solve_channel)
            assert isinstance(channel, TextChannel)

            await channel.send(
                f"<@{interaction.user.id}> just solved {challenge.name}!"
            )

        embed = Embed(
            title=TITLE,
            description=f"You have solved {challenge.name}!",
            color=Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

    else:
        embed = Embed(
            title=TITLE,
            description=f"The flag `{flag}` is incorrect. Try again.",
            color=Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)


class SubmitFlagModal(ui.Modal):
    flag: ui.Label[Self] = ui.Label(
        text="What is the flag?",
        component=ui.TextInput(min_length=2, max_length=MAX_FLAG_LENGTH),
    )

    def __init__(self, client: ChallengeBot, challenge: Challenge):
        super().__init__(title=f"Submit flag for {challenge.name}")

        self.client = client
        self.challenge = challenge

    async def on_error(self, interaction: Interaction, error: Exception):
        await handle_error(interaction, error, self.client.config)

    async def on_submit(self, interaction: Interaction):
        # This is needed to fix type checking.
        assert isinstance(self.flag.component, ui.TextInput)

        await submit_flag(
            self.client, self.challenge, self.flag.component.value, interaction
        )
