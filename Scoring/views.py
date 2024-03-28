import discord
from discord.ext import commands

import classes

from Scoring import buttons, selects
import Scoring


class ScoreGameView(discord.ui.View):
    def __init__(self, game: classes.Game):
        super().__init__(timeout=None)
        self.game = game

        self.add_item(buttons.ScoringButtonWinnerTeam1(game.game_id))
        self.add_item(buttons.ScoringButtonWinnerTeam2(game.game_id))
        self.add_item(buttons.ScoringButtonDone(game.game_id))
        self.add_item(buttons.ScoringButtonRefresh(game.game_id))
        self.add_item(buttons.ScoringButtonVoid(game.game_id))
        self.add_item(selects.ScoringSelectMVPs(game))

        Scoring.functions.refresh_view(self, game)

