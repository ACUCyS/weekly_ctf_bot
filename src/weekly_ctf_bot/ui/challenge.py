from datetime import datetime, timezone
from typing import Self

from discord import ButtonStyle, Color, Embed, Interaction, ui

from .. import ChallengeBot
from ..database import Challenge, Database
from .flag_submission import SubmitFlagModal
from .submissions import SubmissionsView, format_submissions


class SubmitFlagButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(self, client: ChallengeBot, challenge: Challenge):
        super().__init__(label="Submit flag", style=ButtonStyle.primary)

        self.client = client
        self.challenge = challenge

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(
            SubmitFlagModal(self.client, self.challenge)
        )


class HideButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(self, client: ChallengeBot, challenge: Challenge):
        super().__init__(
            label="Hide challenge" if challenge.visible else "Unhide challenge"
        )

        self.client = client
        self.challenge = challenge

    async def callback(self, interaction: Interaction):
        await self.client.database.update_challenge(
            self.challenge.id, visible=not self.challenge.visible
        )

        embed = Embed(
            title="Updated challenge",
            description=f"{self.challenge.name} has been successfully {'hidden' if self.challenge.visible else 'unhidden'}!",
            color=Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class DeleteModal(ui.Modal):
    def __init__(self, database: Database, challenge: Challenge):
        super().__init__(title=f"Delete {challenge.name}")

        self.database = database
        self.challenge = challenge

        self.check: ui.Label[Self] = ui.Label(
            text=f"Are you sure you want to delete {challenge.name}?",
            component=ui.Checkbox(),
        )

    async def on_submit(self, interaction: Interaction):
        # This is needed to fix type checking.
        assert isinstance(self.check.component, ui.Checkbox)

        if self.check.component.value:
            await self.database.delete_challenge(self.challenge.id)

            embed = Embed(
                title="Deleted challenge",
                description=f"Successfully deleted {self.challenge.name}.",
                color=Color.green(),
                timestamp=datetime.now(timezone.utc),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)


class DeleteButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(self, database: Database, challenge: Challenge):
        super().__init__(label="Delete challenge", style=ButtonStyle.danger)

        self.database = database
        self.challenge = challenge

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(
            DeleteModal(self.database, self.challenge)
        )


class SubmissionsButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(self, client: ChallengeBot, challenge: Challenge):
        super().__init__(label="View submissions")

        self.client = client
        self.challenge = challenge

    async def callback(self, interaction: Interaction):
        submissions = await format_submissions(
            self.client, await self.client.database.get_submissions(self.challenge.id)
        )

        await interaction.response.send_message(
            view=SubmissionsView(self.client, self.challenge, submissions),
            ephemeral=True,
        )


class ChallengeView(ui.LayoutView):
    def __init__(self, client: ChallengeBot, challenge: Challenge, is_author: bool):
        super().__init__()

        self.client = client
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
            container.add_item(ui.File(file))

        action_row: ui.ActionRow[Self] = ui.ActionRow()
        self.add_item(action_row)

        action_row.add_item(SubmitFlagButton(client, challenge))

        if is_author:
            action_row.add_item(SubmissionsButton(client, challenge))
            action_row.add_item(HideButton(client, challenge))
            action_row.add_item(DeleteButton(client.database, challenge))
