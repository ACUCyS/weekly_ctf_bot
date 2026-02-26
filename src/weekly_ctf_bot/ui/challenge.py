from datetime import datetime, timezone
from typing import Self

from discord import Color, Embed, Interaction, SelectOption, ui

from ..database import Challenge, Database


class ChallengeView(ui.LayoutView):
    def __init__(self, database: Database, challenge: Challenge, is_author: bool):
        super().__init__()

        self.database = database
        self.is_author = is_author

        container: ui.Container[Self] = ui.Container()
        self.add_item(container)

        container.add_item(
            ui.TextDisplay(f"""
# {challenge.name}
{challenge.description}

*Opens at:* <t:{int(challenge.start.timestamp())}:s>
*Closes at:* <t:{int(challenge.finish.timestamp())}:s>
{"" if challenge.url == "" else f"*Connect at:* {challenge.url}"}

{"" if challenge.visible else "-# This challenge is currently hidden."}
""")
        )

        for file in challenge.files:
            container.add_item(ui.File(file.url))


class ChallengeSelect[V: ui.View](ui.Select[V]):
    def __init__(
        self, database: Database, active_challenges: list[Challenge], is_author: bool
    ):
        self.database = database
        self.is_author = is_author

        super().__init__(
            placeholder="Please select a challenge to view...",
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

        await interaction.response.send_message(
            view=ChallengeView(self.database, challenge, self.is_author),
            ephemeral=True,
        )


class ActiveChallengesView(ui.LayoutView):
    def __init__(
        self, database: Database, active_challenges: list[Challenge], is_author: bool
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

        action_row.add_item(ChallengeSelect(database, active_challenges, is_author))
