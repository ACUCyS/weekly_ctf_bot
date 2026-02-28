from datetime import datetime

from discord import Interaction, Member, app_commands
from discord.ext import commands

from .. import ChallengeBot
from ..database import Challenge
from ..ui import (
    ChallengeView,
    SubmissionsView,
    SubmitFlagModal,
    UpdateChallengeModal,
    UpdateStatusModal,
    format_submissions,
    select_challenge,
    submit_flag,
)


class Challenges(commands.Cog):
    active_challenges: list[Challenge] = []
    challenge_cache_time: datetime = datetime(1970, 1, 1)

    def __init__(self, client: ChallengeBot):
        self.client = client

        self.new_challenge.add_check(self.is_author_check)
        self.edit_challenge.add_check(self.is_author_check)
        self.submissions.add_check(self.is_author_check)
        self.set_challenge_status.add_check(self.is_author_check)

    async def is_author_check(self, interaction: Interaction) -> bool:
        assert isinstance(interaction.user, Member)
        assert interaction.guild_id is not None

        if interaction.user.guild_permissions.administrator:
            return True

        server = await self.client.database.get_server(interaction.guild_id)

        return (
            False
            if server.author_role == 0
            else (interaction.user.get_role(server.author_role) is not None)
        )

    @app_commands.command(name="new-challenge", description="Create a new challenge.")
    @app_commands.checks.cooldown(1, 10)
    async def new_challenge(self, interaction: Interaction):
        await interaction.response.send_modal(UpdateChallengeModal(self.client))

    @app_commands.command(
        name="challenge", description="Get information about the current challenge(s)."
    )
    @app_commands.describe(
        challenge="The challenge to view. Leave blank to view the current challenge."
    )
    @app_commands.checks.cooldown(1, 1)
    async def challenge(self, interaction: Interaction, challenge: str | None):
        is_author = await self.is_author_check(interaction)
        challenge_obj = await select_challenge(
            self.client,
            interaction,
            challenge,
            is_author,
            lambda challenge: ChallengeView(self.client, challenge, is_author),
        )

        if challenge_obj is None:
            return

        await interaction.response.send_message(
            view=ChallengeView(self.client, challenge_obj, is_author),
            ephemeral=True,
        )

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
        challenge_obj = await select_challenge(
            self.client,
            interaction,
            challenge,
            await self.is_author_check(interaction),
            lambda challenge: SubmitFlagModal(self.client, challenge),
        )

        if challenge_obj is None:
            return

        if flag is None or flag.strip() == "":
            await interaction.response.send_modal(
                SubmitFlagModal(self.client, challenge_obj)
            )
            return

        await submit_flag(self.client, challenge_obj, flag, interaction)

    @app_commands.command(
        name="submissions",
        description="Get information about a challenge's submissions.",
    )
    @app_commands.describe(
        challenge="The challenge to view the submissions for. Leave blank to view the current challenge."
    )
    @app_commands.checks.cooldown(1, 1)
    async def submissions(self, interaction: Interaction, challenge: str | None):
        async def callback(challenge: Challenge):
            submissions = await format_submissions(self.client, challenge.id)
            return SubmissionsView(self.client, challenge, submissions)

        challenge_obj = await select_challenge(
            self.client,
            interaction,
            challenge,
            True,
            callback,
        )

        if challenge_obj is None:
            return

        await interaction.response.send_message(
            view=await callback(challenge_obj), ephemeral=True
        )

    @app_commands.command(name="edit-challenge", description="Edit a challenge.")
    @app_commands.describe(
        challenge="The challenge to edit. Leave blank to edit the current challenge."
    )
    @app_commands.checks.cooldown(1, 10)
    async def edit_challenge(self, interaction: Interaction, challenge: str | None):
        challenge_obj = await select_challenge(
            self.client,
            interaction,
            challenge,
            True,
            lambda challenge: UpdateChallengeModal(self.client, challenge),
        )

        if challenge_obj is None:
            return

        await interaction.response.send_modal(
            UpdateChallengeModal(self.client, challenge_obj)
        )

    @app_commands.command(
        name="set-challenge-status", description="Set a challenge's status."
    )
    @app_commands.describe(
        challenge="The challenge to update. Leave blank to update the current challenge."
    )
    @app_commands.checks.cooldown(1, 10)
    async def set_challenge_status(
        self, interaction: Interaction, challenge: str | None
    ):
        challenge_obj = await select_challenge(
            self.client,
            interaction,
            challenge,
            True,
            lambda challenge: UpdateStatusModal(self.client, challenge),
        )

        if challenge_obj is None:
            return

        await interaction.response.send_modal(
            UpdateStatusModal(self.client, challenge_obj)
        )

    @challenge.autocomplete("challenge")
    @submit_flag.autocomplete("challenge")
    @submissions.autocomplete("challenge")
    @edit_challenge.autocomplete("challenge")
    @set_challenge_status.autocomplete("challenge")
    async def challenge_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        assert interaction.guild_id is not None

        return [
            app_commands.Choice(name=challenge.name, value=challenge.name)
            for challenge in await self.client.database.get_active_challenges(
                interaction.guild_id
            )
            if current.lower() in challenge.name.lower()
        ][:25]


async def setup(client: ChallengeBot):
    await client.add_cog(Challenges(client))
