from datetime import datetime, timezone
from typing import Self

from discord import ButtonStyle, Color, Embed, Interaction, TextStyle, ui

from ..database import Challenge, Database


class NewChallengeButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(self, database: Database):
        super().__init__(label="Create new challenge", style=ButtonStyle.primary)

        self.database = database

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(NewChallengeModal(self.database))


class InvalidChallengeView(ui.LayoutView):
    def __init__(self, database: Database, challenge_name: str, is_author: bool):
        super().__init__()

        self.database = database
        self.is_author = is_author

        container: ui.Container[Self] = ui.Container(accent_color=Color.red())
        self.add_item(container)

        container.add_item(
            ui.TextDisplay(f"There are no challenges by the name `{challenge_name}`!")
        )

        if is_author:
            container.add_item(NewChallengeButton(self.database))


class NewChallengeModal(ui.Modal):
    name: ui.Label[Self] = ui.Label(
        text="What is the challenge name?",
        description="Please pick something unique.",
        component=ui.TextInput(min_length=3, max_length=32),
    )

    description: ui.Label[Self] = ui.Label(
        text="What is the challenge description?",
        description="Please provide all required context to complete the challenge here.",
        component=ui.TextInput(required=False, style=TextStyle.long),
    )

    flag: ui.Label[Self] = ui.Label(
        text="What is the flag?",
        description="Please pick something unique. Flag submission is case-insensitive.",
        component=ui.TextInput(min_length=2, max_length=32),
    )

    url: ui.Label[Self] = ui.Label(
        text="What is the connection url/command?",
        description="This can either be a web URL, or a command to access the challenge.",
        component=ui.TextInput(required=False, max_length=64),
    )

    files: ui.Label[Self] = ui.Label(
        text="What files are needed to complete this challenge?",
        description="Provide the files as URLs, each on their own line.",
        component=ui.TextInput(required=False, style=TextStyle.long),
    )

    start: ui.Label[Self] = ui.Label(
        text="When should the challenge open/start?",
        description="Please provide this as a UTC unix epoch timestamp. Visit https://www.epochconverter.com/ for help. If not provided, the challenge will open now.",
        component=ui.TextInput(required=False),
    )

    finish: ui.Label[Self] = ui.Label(
        text="When should the challenge close/finish?",
        description="Please provide this as a UTC unix epoch timestamp. Visit https://www.epochconverter.com/ for help.",
        component=ui.TextInput(),
    )

    hidden: ui.Label[Self] = ui.Label(
        text="Should the challenge be hidden?",
        description="If checked, this challenge will not be shown to any users until unhidden.",
        component=ui.Checkbox(),
    )

    def __init__(self, database: Database):
        super().__init__(title="Create new challenge")

        self.database = database

    async def on_submit(self, interaction: Interaction):
        # This is needed to fix type checking.
        assert isinstance(self.name.component, ui.TextInput)
        assert isinstance(self.description.component, ui.TextInput)
        assert isinstance(self.flag.component, ui.TextInput)
        assert isinstance(self.url.component, ui.TextInput)
        assert isinstance(self.files.component, ui.TextInput)
        assert isinstance(self.start.component, ui.TextInput)
        assert isinstance(self.finish.component, ui.TextInput)
        assert isinstance(self.hidden.component, ui.Checkbox)

        try:
            start = datetime.fromtimestamp(
                float(self.start.component.value), timezone.utc
            )

        except ValueError:
            embed = Embed(
                title="Challenge creation",
                description=f"`{self.start.component.value}` is an invalid unix epoch timestamp!",
                color=Color.red(),
                timestamp=datetime.now(timezone.utc),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            finish = datetime.fromtimestamp(
                float(self.finish.component.value), timezone.utc
            )

        except ValueError:
            embed = Embed(
                title="Challenge creation",
                description=f"`{self.finish.component.value}` is an invalid unix epoch timestamp!",
                color=Color.red(),
                timestamp=datetime.now(timezone.utc),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self.database.add_challenge(
            Challenge(
                name=self.name.component.value,
                description=self.description.component.value,
                visible=not self.hidden.component.value,
                flag=self.flag.component.value,
                files=self.files.component.value.splitlines(),
                url=self.url.component.value,
                start=start,
                finish=finish,
            )
        )

        embed = Embed(
            title="Challenge creation",
            description=f"Successfully created '{self.name.component.value}'",
            color=Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
