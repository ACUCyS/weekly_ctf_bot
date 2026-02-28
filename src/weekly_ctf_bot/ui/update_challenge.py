from datetime import datetime, timedelta, timezone
from typing import Self

from discord import ButtonStyle, Color, Interaction, TextStyle, ui

from .. import ChallengeBot, handle_error
from ..database import (
    MAX_FLAG_LENGTH,
    MAX_NAME_LENGTH,
    MAX_URL_LENGTH,
    Challenge,
    file_list_to_str,
    str_to_file_list,
)
from .update_status import UpdateStatusView


class NewChallengeButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(self, client: ChallengeBot):
        super().__init__(label="Create new challenge", style=ButtonStyle.primary)

        self.client = client

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(UpdateChallengeModal(self.client))


class InvalidChallengeView(ui.LayoutView):
    def __init__(self, client: ChallengeBot, challenge_name: str, is_author: bool):
        super().__init__()

        self.client = client

        container: ui.Container[Self] = ui.Container(accent_color=Color.red())
        self.add_item(container)

        container.add_item(
            ui.TextDisplay(f"There are no challenges by the name `{challenge_name}`!")
        )

        if is_author:
            action_row: ui.ActionRow[Self] = ui.ActionRow()
            container.add_item(action_row)
            action_row.add_item(NewChallengeButton(client))

    async def on_error(
        self, interaction: Interaction, error: Exception, item: ui.Item[Self]
    ):
        await handle_error(interaction, error, self.client.config)


class UpdateChallengeModal(ui.Modal):
    def __init__(self, client: ChallengeBot, challenge: Challenge | None = None):
        super().__init__(
            title="Create new challenge" if challenge is None else "Edit challenge info"
        )

        self.client = client
        self.challenge = challenge

        self.name: ui.TextInput[Self] = ui.TextInput(
            min_length=3, max_length=MAX_NAME_LENGTH
        )

        self.description: ui.TextInput[Self] = ui.TextInput(
            required=False, style=TextStyle.long
        )

        self.flag: ui.TextInput[Self] = ui.TextInput(
            min_length=2, max_length=MAX_FLAG_LENGTH
        )
        self.url: ui.TextInput[Self] = ui.TextInput(
            required=False, max_length=MAX_URL_LENGTH
        )

        self.files: ui.TextInput[Self] = ui.TextInput(
            required=False, style=TextStyle.long
        )

        if challenge is not None:
            self.name.default = challenge.name
            self.description.default = challenge.description
            self.flag.default = challenge.flag
            self.url.default = challenge.url
            self.files.default = file_list_to_str(challenge.files)

        self.add_item(
            ui.Label(
                text="What is the challenge name?",
                description="Please pick something unique.",
                component=self.name,
            )
        )

        self.add_item(
            ui.Label(
                text="What is the challenge description?",
                description="Please provide all required context to complete the challenge here.",
                component=self.description,
            )
        )

        self.add_item(
            ui.Label(
                text="What is the flag?",
                description="Please pick something unique. Flag submission is case-insensitive.",
                component=self.flag,
            )
        )

        self.add_item(
            ui.Label(
                text="What is the connection url/command?",
                description="This can either be a web URL, or a command to access the challenge.",
                component=self.url,
            )
        )

        self.add_item(
            ui.Label(
                text="What files are needed for this challenge?",
                description="Provide the files as '<filename> <URL>', each on their own line.",
                component=self.files,
            )
        )

    async def on_error(self, interaction: Interaction, error: Exception):
        await handle_error(interaction, error, self.client.config)

    async def on_submit(self, interaction: Interaction):
        is_creation = self.challenge is None

        if self.challenge is None:
            self.challenge = Challenge(
                name=self.name.value,
                description=self.description.value,
                visible=False,
                flag=self.flag.value,
                files=str_to_file_list(self.files.value),
                url=self.url.value,
                start=datetime.now(timezone.utc),
                finish=datetime.now(timezone.utc) + timedelta(weeks=1),
                server_id=interaction.guild_id,
            )

            await self.client.database.add_challenge(self.challenge)

        else:
            await self.client.database.update_challenge(
                self.challenge.id,
                name=self.name.value,
                description=self.description.value,
                flag=self.flag.value,
                files=str_to_file_list(self.files.value),
                url=self.url.value,
            )

            self.challenge.name = self.name.value

        await interaction.response.send_message(
            view=UpdateStatusView(self.client, self.challenge, is_creation),
            ephemeral=True,
        )
