from discord.ext.commands import parameter

ROLE_DATA = parameter(displayed_name="@Role | Role ID")

CHANNEL_DATA = parameter(displayed_name="Channel ID | Channel JumpURL")

PLAYER_DATA = parameter(displayed_name=f"Member IGN | @Member | Member ID")

PLAYER_DATA_OPTIONAL = parameter(displayed_name=f"Member IGN | @Member | Member ID", default=None)

REASON = parameter(displayed_name="Reason", default="Not specified")

ATTACHMENT = parameter(displayed_name="Image URL | Attachment", default=None)

IGN = parameter(displayed_name="IGN")

GAME_ID = parameter(displayed_name="Game ID")

WINNING_TEAM_NUMBER = parameter(displayed_name="Winner team number")

MVPS = parameter(displayed_name="MVPS", default=None)

PAGE = parameter(displayed_name="Page", default=1)

LEADERBOARD_MODE = parameter(displayed_name="Mode", default='elo')

PERIOD = parameter(displayed_name="Period")

USER_DATA = parameter(displayed_name="User ID | @User")
