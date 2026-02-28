from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Self

from discord import ButtonStyle, Color, Embed, Interaction, SelectOption, ui

from .. import ChallengeBot, handle_error
from ..database import Challenge, Submission


@dataclass
class UserSubmissions:
    user_name: str
    has_solved: bool
    submissions: list[Submission]


async def format_submissions(
    client: ChallengeBot, challenge_id: int
) -> dict[int, UserSubmissions]:
    user_submissions: dict[int, UserSubmissions] = {}

    for submission in await client.database.get_submissions(challenge_id):
        if submission.user_id in user_submissions:
            user = user_submissions[submission.user_id]

        else:
            user = UserSubmissions(
                user_name=(await client.fetch_user(submission.user_id)).display_name,
                has_solved=False,
                submissions=[],
            )

            user_submissions[submission.user_id] = user

        if submission.is_correct:
            user.has_solved = True

        user.submissions.append(submission)

    return user_submissions


class SubmissionSelect[V: ui.Modal](ui.Select[V]):
    def __init__(self, user: UserSubmissions):
        super().__init__(
            placeholder="Select a submission...",
            options=[
                SelectOption(
                    label=f"{submission.id} - {submission.timestamp.isoformat()} UTC {'(solve)' if submission.is_correct else ''}",
                    value=str(submission.id),
                )
                for submission in user.submissions
            ],
        )


class DeleteModal(ui.Modal):
    def __init__(
        self,
        client: ChallengeBot,
        user: UserSubmissions,
    ):
        super().__init__(title="Delete submissions")

        self.client = client

        self.submission: SubmissionSelect[Self] = SubmissionSelect(user)
        self.add_item(
            ui.Label(text="Select a submission to delete.", component=self.submission)
        )

    async def on_error(self, interaction: Interaction, error: Exception):
        await handle_error(interaction, error, self.client.config)

    async def on_submit(self, interaction: Interaction):
        submission_id = int(self.submission.values[0])
        await self.client.database.delete_submission(submission_id)

        embed = Embed(
            title="Submission deletion",
            description=f"Successfully deleted submission #{submission_id}.",
            color=Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class DeleteButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(
        self,
        client: ChallengeBot,
        user: UserSubmissions,
    ):
        super().__init__(label="Delete a submission", style=ButtonStyle.danger)

        self.client = client
        self.user = user

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(DeleteModal(self.client, self.user))


class UserSubmissionsView(ui.LayoutView):
    def __init__(
        self,
        client: ChallengeBot,
        user: UserSubmissions,
        challenge: Challenge,
    ):
        super().__init__()

        self.client = client

        container: ui.Container[Self] = ui.Container()
        self.add_item(container)

        container.add_item(
            ui.TextDisplay(f"""
# {user.user_name}'s submissions for {challenge.name}
{"\n".join([f"{submission.id} - <t:{int(submission.timestamp.timestamp())}:S> {'(solve)' if submission.is_correct else ''}" for submission in user.submissions])}
""")
        )

        action_row: ui.ActionRow[Self] = ui.ActionRow()
        container.add_item(action_row)
        action_row.add_item(DeleteButton(client, user))

    async def on_error(
        self, interaction: Interaction, error: Exception, item: ui.Item[Self]
    ):
        await handle_error(interaction, error, self.client.config)


class UserSelect[V: ui.LayoutView](ui.Select[V]):
    def __init__(
        self,
        client: ChallengeBot,
        challenge: Challenge,
        submissions: dict[int, UserSubmissions],
    ):
        self.client = client
        self.challenge = challenge
        self.submissions = submissions

        super().__init__(
            placeholder="Please select a player...",
            options=[
                SelectOption(label=submissions[id].user_name, value=str(id))
                for id in submissions
            ],
        )

    async def callback(self, interaction: Interaction):
        await interaction.response.send_message(
            view=UserSubmissionsView(
                self.client, self.submissions[int(self.values[0])], self.challenge
            ),
            ephemeral=True,
        )


class SubmissionsView(ui.LayoutView):
    def __init__(
        self,
        client: ChallengeBot,
        challenge: Challenge,
        submissions: dict[int, UserSubmissions],
    ):
        super().__init__()

        self.client = client

        container: ui.Container[Self] = ui.Container()
        self.add_item(container)

        container.add_item(
            ui.TextDisplay(f"""
# {challenge.name} submissions
{"\n".join([f"- {user.user_name} - {len(user.submissions)} ({'solved' if user.has_solved else 'unsolved'})" for user in submissions.values()])}
{"There are no submissions yet." if len(submissions) == 0 else ""}
""")
        )

        if len(submissions) > 0:
            action_row: ui.ActionRow[Self] = ui.ActionRow()
            container.add_item(action_row)
            action_row.add_item(UserSelect(client, challenge, submissions))

    async def on_error(
        self, interaction: Interaction, error: Exception, item: ui.Item[Self]
    ):
        await handle_error(interaction, error, self.client.config)
