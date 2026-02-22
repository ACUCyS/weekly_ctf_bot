from datetime import datetime, timezone

from aiohttp import ClientSession, ClientTimeout
from discord import Color, Embed, Interaction, Webhook, app_commands
from discord.ext import commands

from weekly_ctf_bot import ChallengeBot
from weekly_ctf_bot.database import Challenge, Database


class Challenges(commands.Cog):
    database: Database
    active_challenges: list[Challenge] = []
    challenge_cache_time: datetime = datetime(1970, 1, 1)

    def __init__(self, client: ChallengeBot):
        self.client = client

    async def cog_load(self):
        self.database = await Database.create(self.client.config.database_url)

    async def cog_unload(self):
        await self.database.close()

    async def get_active_challenges(self) -> list[Challenge]:
        if (
            datetime.now() - self.challenge_cache_time
        ).seconds >= self.client.config.challenge_cache:
            self.active_challenges = list(await self.database.get_active_challenges())

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
        self, interaction: Interaction, flag: str, challenge: str | None
    ):
        TITLE = ":triangular_flag_on_post: Flag submission"

        if flag.strip() == "":
            embed = Embed(
                title=TITLE,
                description="Please enter a flag.",
                color=Color.red(),
                timestamp=datetime.now(timezone.utc),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if challenge is None or challenge.strip() == "":
            active = await self.get_active_challenges()

            if len(active) == 0:
                embed = Embed(
                    title=TITLE,
                    description="There are currently no active challenges!",
                    color=Color.red(),
                    timestamp=datetime.now(timezone.utc),
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            elif len(active) > 1:
                desc = (
                    "There are multiple active challenges. Please select from the challenges below.\n"
                    + "\n".join([f"- {challenge.name}" for challenge in active])
                )

                embed = Embed(
                    title=TITLE,
                    description=desc,
                    color=Color.teal(),
                    timestamp=datetime.now(timezone.utc),
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            challenge_obj = active[0]

        else:
            challenge_obj = await self.database.get_challenge(challenge)
            if challenge_obj is None:
                embed = Embed(
                    title=TITLE,
                    description=f"There are no challenges by the name `{challenge}`.",
                    color=Color.red(),
                    timestamp=datetime.now(timezone.utc),
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        solve = await self.database.get_solve(challenge_obj.id, interaction.user.id)
        if solve is not None:
            embed = Embed(
                title=TITLE,
                description=f"You've already solved {challenge_obj.name}!",
                color=Color.teal(),
                timestamp=datetime.now(timezone.utc),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        is_correct = await self.database.add_submission(
            challenge_obj, interaction.user.id, flag
        )

        if is_correct:
            if self.client.config.solve_webhook is not None:
                async with ClientSession(
                    timeout=ClientTimeout(total=self.client.config.webhook_timeout)
                ) as session:
                    webhook = Webhook.from_url(
                        self.client.config.solve_webhook,
                        session=session,
                    )

                    await webhook.send(
                        f"<@{interaction.user.id}> just solved {challenge_obj.name}!"
                    )

            embed = Embed(
                title=TITLE,
                description=f"You have solved {challenge_obj.name}!",
                color=Color.green(),
                timestamp=datetime.now(timezone.utc),
            )

        else:
            embed = Embed(
                title=TITLE,
                description=f"The flag `{flag}` is incorrect. Try again.",
                color=Color.orange(),
                timestamp=datetime.now(timezone.utc),
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

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
