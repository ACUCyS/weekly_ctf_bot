from datetime import datetime

from discord import Interaction, app_commands
from discord.ext import commands

from .. import ChallengeBot
from ..database import Challenge
from ..ui import (
    ChallengeView,
    InvalidChallengeView,
    NewChallengeModal,
    SelectChallengeView,
    SubmitFlagModal,
    submit_flag,
)


class Challenges(commands.Cog):
    active_challenges: list[Challenge] = []
    challenge_cache_time: datetime = datetime(1970, 1, 1)

    def __init__(self, client: ChallengeBot):
        self.client = client

        self.new_challenge.add_check(self.is_author_check)

    async def get_active_challenges(self) -> list[Challenge]:
        if (
            datetime.now() - self.challenge_cache_time
        ).seconds >= self.client.config.challenge_cache:
            self.active_challenges = list(
                await self.client.database.get_active_challenges()
            )

        return self.active_challenges

    @app_commands.command(
        name="submit-flag", description="Submit the flag for a challenge."
    )
    @app_commands.describe(
        flag="The flag to submit",
        challenge="The challenge to submit the flag to. Leave blank to select the current active challenge.",
    )
    @app_commands.checks.cooldown(1, 3)
    async def submit_flag(
        self, interaction: Interaction, flag: str | None, challenge: str | None
    ):
        if challenge is None or challenge.strip() == "":
            active_challenges = await self.get_active_challenges()
            await interaction.response.send_message(
                view=SelectChallengeView(
                    self.client.database,
                    active_challenges,
                    lambda challenge: SubmitFlagModal(self.client, challenge),
                ),
                ephemeral=True,
            )

            return

        challenge_obj = await self.client.database.get_challenge(challenge)
        if challenge_obj is None:
            await interaction.response.send_message(
                view=InvalidChallengeView(
                    self.client.database,
                    challenge,
                    self.is_author_check(interaction),
                ),
                ephemeral=True,
            )
            return

        if flag is None or flag.strip() == "":
            await interaction.response.send_modal(
                SubmitFlagModal(self.client, challenge_obj)
            )
            return

        await submit_flag(self.client, challenge_obj, flag, interaction)

    @app_commands.command(
        name="challenge", description="Get information about the current challenge(s)."
    )
    @app_commands.describe(
        challenge="The challenge to view. Leave blank to view the current challenge."
    )
    @app_commands.checks.cooldown(1, 1)
    async def challenge(self, interaction: Interaction, challenge: str | None):
        is_author = self.is_author_check(interaction)

        if challenge is None or challenge.strip() == "":
            active_challenges = await self.get_active_challenges()
            await interaction.response.send_message(
                view=SelectChallengeView(
                    self.client.database,
                    active_challenges,
                    lambda challenge: ChallengeView(self.client, challenge, is_author),
                ),
                ephemeral=True,
            )

        else:
            challenge_obj = await self.client.database.get_challenge(challenge)
            if challenge_obj is None:
                await interaction.response.send_message(
                    view=InvalidChallengeView(
                        self.client.database,
                        challenge,
                        is_author,
                    ),
                    ephemeral=True,
                )
                return

            await interaction.response.send_message(
                view=ChallengeView(self.client, challenge_obj, is_author),
                ephemeral=True,
            )

    @app_commands.command(name="new-challenge", description="Create a new challenge.")
    @app_commands.checks.cooldown(1, 10)
    async def new_challenge(self, interaction: Interaction):
        await interaction.response.send_modal(NewChallengeModal(self.client.database))

    def is_author_check(self, interaction: Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:  # type: ignore
            return True

        return (
            False
            if self.client.config.author_role_id is None
            else (
                interaction.user.get_role(self.client.config.author_role_id) is not None  # type: ignore
            )
        )

    @challenge.autocomplete("challenge")
    @submit_flag.autocomplete("challenge")
    async def challenge_autocomplete(
        self, _interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=challenge.name, value=challenge.name)
            for challenge in await self.get_active_challenges()
            if current.lower() in challenge.name.lower()
        ][:25]


async def setup(client: ChallengeBot):
    await client.add_cog(Challenges(client))
