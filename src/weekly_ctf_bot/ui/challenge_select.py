from datetime import datetime, timezone
from inspect import isawaitable
from typing import Awaitable, Callable, Self, Sequence

from discord import Color, Embed, Interaction, SelectOption, ui

from .. import ChallengeBot, handle_error
from ..database import Challenge, Database
from .update_challenge import InvalidChallengeView


async def select_challenge(
    client: ChallengeBot,
    interaction: Interaction,
    challenge: str | None,
    is_author: bool,
    redirect: Callable[
        [Challenge], ui.LayoutView | ui.Modal | Awaitable[ui.LayoutView | ui.Modal]
    ],
) -> Challenge | None:
    assert interaction.guild_id is not None

    if challenge is None or challenge.strip() == "":
        active_challenges = await client.database.get_active_challenges(
            interaction.guild_id
        )

        if len(active_challenges) == 1:
            return active_challenges[0]

        await interaction.response.send_message(
            view=SelectChallengeView(client, active_challenges, redirect),
            ephemeral=True,
        )

        return

    else:
        challenge_obj = await client.database.search_challenge(
            interaction.guild_id, challenge
        )

        if challenge_obj is None:
            await interaction.response.send_message(
                view=InvalidChallengeView(client, challenge, is_author),
                ephemeral=True,
            )

            return

        return challenge_obj


class ChallengeSelect[V: ui.LayoutView](ui.Select[V]):
    def __init__(
        self,
        database: Database,
        active_challenges: Sequence[Challenge],
        redirect: Callable[
            [Challenge], ui.LayoutView | ui.Modal | Awaitable[ui.LayoutView | ui.Modal]
        ],
    ):
        self.database = database
        self.redirect = redirect

        super().__init__(
            placeholder="Please select a challenge...",
            options=[
                SelectOption(label=challenge.name, value=str(challenge.id))
                for challenge in active_challenges
            ],
        )

    async def callback(self, interaction: Interaction):
        challenge = await self.database.get_challenge(int(self.values[0]))
        if challenge is None:
            embed = Embed(
                title="CTF Challenges",
                description="That challenge has been deleted!",
                color=Color.red(),
                timestamp=datetime.now(timezone.utc),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        redirect = self.redirect(challenge)
        if isawaitable(redirect):
            redirect = await redirect

        if isinstance(redirect, ui.LayoutView):
            await interaction.response.send_message(view=redirect, ephemeral=True)
        else:
            await interaction.response.send_modal(redirect)


class SelectChallengeView(ui.LayoutView):
    def __init__(
        self,
        client: ChallengeBot,
        active_challenges: Sequence[Challenge],
        redirect: Callable[
            [Challenge], ui.LayoutView | ui.Modal | Awaitable[ui.LayoutView | ui.Modal]
        ],
    ):
        super().__init__()

        self.client = client

        if len(active_challenges) == 0:
            container: ui.Container[Self] = ui.Container(accent_color=Color.red())
            self.add_item(container)

            container.add_item(
                ui.TextDisplay("There are currently no active challenges.")
            )

            return

        action_row: ui.ActionRow[Self] = ui.ActionRow()
        self.add_item(action_row)

        action_row.add_item(
            ChallengeSelect(client.database, active_challenges, redirect)
        )

    async def on_error(
        self, interaction: Interaction, error: Exception, item: ui.Item[Self]
    ):
        await handle_error(interaction, error, self.client.config)
