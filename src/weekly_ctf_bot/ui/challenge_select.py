from datetime import datetime, timezone
from typing import Callable, Self

from discord import Color, Embed, Interaction, SelectOption, ui

from ..database import Challenge, Database


class ChallengeSelect[V: ui.LayoutView](ui.Select[V]):
    def __init__(
        self,
        database: Database,
        active_challenges: list[Challenge],
        redirect: Callable[[Challenge], ui.LayoutView | ui.Modal],
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
        challenge = await self.database.get_challenge_by_id(int(self.values[0]))
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
        if isinstance(redirect, ui.LayoutView):
            await interaction.response.send_message(view=redirect, ephemeral=True)
        else:
            await interaction.response.send_modal(redirect)


class SelectChallengeView(ui.LayoutView):
    def __init__(
        self,
        database: Database,
        active_challenges: list[Challenge],
        redirect: Callable[[Challenge], ui.LayoutView | ui.Modal],
    ):
        super().__init__()

        if len(active_challenges) == 0:
            container: ui.Container[Self] = ui.Container(accent_color=Color.red())
            self.add_item(container)

            container.add_item(
                ui.TextDisplay("There are currently no active challenges.")
            )

            return

        action_row: ui.ActionRow[Self] = ui.ActionRow()
        self.add_item(action_row)

        action_row.add_item(ChallengeSelect(database, active_challenges, redirect))
