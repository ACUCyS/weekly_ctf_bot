from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Self, Sequence

from discord import Color, Embed, Interaction, SelectOption, ui

from .. import ChallengeBot
from ..database import Challenge, Submission


@dataclass
class UserSubmissions:
    user_name: str
    has_solved: bool
    submissions: list[Submission]


async def format_submissions(
    client: ChallengeBot, submissions: Sequence[Submission]
) -> dict[int, UserSubmissions]:
    user_submissions: dict[int, UserSubmissions] = {}

    for submission in submissions:
        if submission.user_id in user_submissions:
            user = user_submissions[submission.user_id]

        else:
            user = UserSubmissions(
                user_name=(await client.fetch_user(submission.user_id)).display_name,
                has_solved=False,
                submissions=[],
            )

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
                    label=f"{submission.id} - <t:{int(submission.timestamp.timestamp())}:S>",
                    value=str(submission.id),
                )
                for submission in user.submissions
            ],
        )


class DeleteModal(ui.Modal):
    def __init__(
        self,
        user: UserSubmissions,
        client: ChallengeBot,
    ):
        super().__init__(title="Delete submissions")

        self.client = client

        self.submission: SubmissionSelect[Self] = SubmissionSelect(user)
        self.add_item(
            ui.Label(text="Select a submission to delete.", component=self.submission)
        )

    async def on_submit(self, interaction: Interaction):
        submission_id = int(self.submission.values[0])
        await self.client.database.delete_submission(submission_id)

        embed = Embed(
            title="Submission deletion",
            description=f"Successfully deleted submission #{submission_id}",
            color=Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class DeleteButton[V: ui.LayoutView](ui.Button[V]):
    def __init__(
        self,
        user: UserSubmissions,
        client: ChallengeBot,
    ):
        super().__init__(label="Delete a submission")

        self.client = client
        self.user = user

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(DeleteModal(self.user, self.client))


class UserSubmissionsView(ui.LayoutView):
    def __init__(
        self,
        user: UserSubmissions,
        client: ChallengeBot,
        challenge: Challenge,
    ):
        super().__init__()

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
        action_row.add_item(DeleteButton(user, client))


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
                self.submissions[int(self.values[0])], self.client, self.challenge
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

        container: ui.Container[Self] = ui.Container()
        self.add_item(container)

        container.add_item(
            ui.TextDisplay(f"""
# {challenge.name} submissions
{"\n".join([f"- {user.user_name} - {len(user.submissions)} ({'solved' if user.has_solved else 'unsolved'})" for user in submissions.values()])}
{"There are no submissions yet." if len(submissions) == 0 else ""}
""")
        )

        select_row: ui.ActionRow[Self] = ui.ActionRow()
        select_row.add_item(UserSelect(client, challenge, submissions))
