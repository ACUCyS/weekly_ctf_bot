from datetime import datetime, timezone
from typing import Self

from discord import Color, Embed, Interaction, ui

from .. import ChallengeBot, handle_error
from ..database import Challenge


class UpdateStatusButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(self, client: ChallengeBot, challenge: Challenge):
        super().__init__(label="Set challenge status")

        self.client = client
        self.challenge = challenge

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(
            UpdateStatusModal(self.client, self.challenge)
        )


class UpdateStatusView(ui.LayoutView):
    def __init__(self, client: ChallengeBot, challenge: Challenge, is_creation: bool):
        super().__init__()

        self.client = client

        container: ui.Container[Self] = ui.Container(accent_color=Color.green())
        self.add_item(container)

        container.add_item(
            ui.TextDisplay(f"""
Successfully {"created" if is_creation else "updated"} {challenge.name}!
{"Upon creation this challenge is hidden, and it set to start now, and finish a week from now." if is_creation else ""}
{"To change this, click the button below." if is_creation else "To change the challenge start/finish times and visibility, click the button below."}
""")
        )

        action_row: ui.ActionRow[Self] = ui.ActionRow()
        self.add_item(action_row)
        action_row.add_item(UpdateStatusButton(client, challenge))

    async def on_error(
        self, interaction: Interaction, error: Exception, item: ui.Item[Self]
    ):
        await handle_error(interaction, error, self.client.config)


class UpdateStatusModal(ui.Modal):
    def __init__(
        self,
        client: ChallengeBot,
        challenge: Challenge,
    ):
        super().__init__(title=f"Set challenge status for {challenge.name}")

        self.client = client
        self.challenge = challenge

        self.start: ui.TextInput[Self] = ui.TextInput(
            required=False, default=str(int(challenge.start.timestamp()))
        )

        self.finish: ui.TextInput[Self] = ui.TextInput(
            default=str(int(challenge.finish.timestamp()))
        )

        self.hidden: ui.Checkbox[Self] = ui.Checkbox(default=not challenge.visible)

        self.add_item(
            ui.Label(
                text="When should the challenge open/start?",
                description="Please provide this as a UTC unix epoch timestamp. Visit https://www.epochconverter.com/ for help.",
                component=self.start,
            )
        )

        self.add_item(
            ui.Label(
                text="When should the challenge close/finish?",
                description="Please provide this as a UTC unix epoch timestamp. Visit https://www.epochconverter.com/ for help.",
                component=self.finish,
            )
        )

        self.add_item(
            ui.Label(
                text="Should the challenge be hidden?",
                description="If checked, this challenge will not be shown to any users until unhidden.",
                component=self.hidden,
            )
        )

    async def on_error(self, interaction: Interaction, error: Exception):
        await handle_error(interaction, error, self.client.config)

    async def on_submit(self, interaction: Interaction):
        TITLE = "Challenge status"

        try:
            if self.start.value == "":
                start = datetime.now(timezone.utc)
            else:
                start = datetime.fromtimestamp(float(self.start.value), timezone.utc)

        except ValueError:
            embed = Embed(
                title=TITLE,
                description=f"`{self.start.value}` is an invalid unix epoch timestamp!",
                color=Color.red(),
                timestamp=datetime.now(timezone.utc),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            finish = datetime.fromtimestamp(float(self.finish.value), timezone.utc)

        except ValueError:
            embed = Embed(
                title=TITLE,
                description=f"`{self.finish.value}` is an invalid unix epoch timestamp!",
                color=Color.red(),
                timestamp=datetime.now(timezone.utc),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self.client.database.update_challenge(
            self.challenge.id,
            visible=not self.hidden.value,
            start=start,
            finish=finish,
        )

        if self.challenge.id in self.client.start_events:
            self.client.start_events[self.challenge.id].cancel()
            del self.client.start_events[self.challenge.id]

        if self.challenge.id in self.client.finish_events:
            self.client.finish_events[self.challenge.id].cancel()
            del self.client.finish_events[self.challenge.id]

        if not self.hidden.value:
            challenge = self.challenge
            challenge.start = start
            challenge.finish = finish

            now = datetime.now(timezone.utc)
            if start > now:
                self.client.add_start_event(challenge)
            elif finish > now:
                self.client.add_finish_event(challenge)

        embed = Embed(
            title=TITLE,
            description=f"Successfully updated status of {self.challenge.name}",
            color=Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
