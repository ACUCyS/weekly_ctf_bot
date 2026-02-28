from datetime import datetime, timezone
from typing import Self

from discord import ButtonStyle, Color, Embed, Interaction, ui

from .. import ChallengeBot, handle_error
from ..database import Challenge
from .flag_submission import SubmitFlagModal
from .submissions import SubmissionsView, format_submissions
from .update_challenge import UpdateChallengeModal
from .update_status import UpdateStatusButton


class SubmitFlagButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(self, client: ChallengeBot, challenge: Challenge):
        super().__init__(label="Submit flag", style=ButtonStyle.primary)

        self.client = client
        self.challenge = challenge

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(
            SubmitFlagModal(self.client, self.challenge)
        )


class DeleteModal(ui.Modal):
    def __init__(self, client: ChallengeBot, challenge: Challenge):
        super().__init__(title=f"Delete {challenge.name}")

        self.client = client
        self.challenge = challenge

        self.check: ui.Label[Self] = ui.Label(
            text=f"Are you sure you want to delete {challenge.name}?",
            component=ui.Checkbox(),
        )

    async def on_error(self, interaction: Interaction, error: Exception):
        await handle_error(interaction, error, self.client.config)

    async def on_submit(self, interaction: Interaction):
        # This is needed to fix type checking.
        assert isinstance(self.check.component, ui.Checkbox)

        if self.check.component.value:
            await self.client.database.delete_challenge(self.challenge.id)

            if self.challenge.id in self.client.start_events:
                self.client.start_events[self.challenge.id].cancel()
                del self.client.start_events[self.challenge.id]

            if self.challenge.id in self.client.finish_events:
                self.client.finish_events[self.challenge.id].cancel()
                del self.client.finish_events[self.challenge.id]

            embed = Embed(
                title="Deleted challenge",
                description=f"Successfully deleted {self.challenge.name}.",
                color=Color.green(),
                timestamp=datetime.now(timezone.utc),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)


class DeleteButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(self, client: ChallengeBot, challenge: Challenge):
        super().__init__(label="Delete challenge", style=ButtonStyle.danger)

        self.client = client
        self.challenge = challenge

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(DeleteModal(self.client, self.challenge))


class SubmissionsButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(self, client: ChallengeBot, challenge: Challenge):
        super().__init__(label="View submissions")

        self.client = client
        self.challenge = challenge

    async def callback(self, interaction: Interaction):
        submissions = await format_submissions(self.client, self.challenge.id)
        await interaction.response.send_message(
            view=SubmissionsView(self.client, self.challenge, submissions),
            ephemeral=True,
        )


class EditButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(self, client: ChallengeBot, challenge: Challenge):
        super().__init__(label="Edit challenge info")

        self.client = client
        self.challenge = challenge

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(
            UpdateChallengeModal(self.client, self.challenge)
        )


class ChallengeView(ui.LayoutView):
    def __init__(self, client: ChallengeBot, challenge: Challenge, is_author: bool):
        super().__init__()

        self.client = client

        container: ui.Container[Self] = ui.Container()
        self.add_item(container)

        container.add_item(
            ui.TextDisplay(f"""
# {challenge.name}
{challenge.description}

*Opens at:* <t:{int(challenge.start.timestamp())}:s>
*Closes at:* <t:{int(challenge.finish.timestamp())}:s>
{"" if challenge.url == "" else f"*Connect at:* {challenge.url}\n"}
{"\n".join([f"[{file.filename}]({file.url})" for file in challenge.files])}

{"" if challenge.visible else "-# This challenge is currently hidden."}
""")
        )

        action_row: ui.ActionRow[Self] = ui.ActionRow()
        self.add_item(action_row)

        action_row.add_item(SubmitFlagButton(client, challenge))

        if is_author:
            action_row.add_item(SubmissionsButton(client, challenge))
            action_row.add_item(EditButton(client, challenge))
            action_row.add_item(UpdateStatusButton(client, challenge))
            action_row.add_item(DeleteButton(client, challenge))

    async def on_error(
        self, interaction: Interaction, error: Exception, item: ui.Item[Self]
    ) -> None:
        await handle_error(interaction, error, self.client.config)
