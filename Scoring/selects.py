import re
import traceback
from typing import Self, Any

import discord
from discord import Interaction

import classes
from Functions import functions


class ScoringSelectMVPs(discord.ui.DynamicItem[discord.ui.Select],
                        template=r'scoring:(?P<game_id>[0-9]+):select:mvps'):
    def __init__(self, game):
        mvps_options = []

        for player_id in game.players_ids:
            mvps_options.append(
                discord.SelectOption(
                    label=functions.get_ign_nick(player_id, game.guild),
                    value=f"{player_id}",
                )
            )

        super().__init__(
            discord.ui.Select(
                placeholder="Select MVP(s) ...",
                max_values=len(game.players_ids),
                options=mvps_options,
                custom_id=f"scoring:{game.game_id}:select:mvps"
            )
        )

        self.game = game

    @classmethod
    async def from_custom_id(
        cls, interaction: Interaction, item: discord.ui.Select, match: re.Match[str], /
    ) -> Self:
        game_id = int(match['game_id'])
        game = classes.Game.from_game_id(game_id, interaction.guild, interaction.client)
        return cls(game)

    async def callback(self, interaction: Interaction) -> Any:
        db, cursor = functions.database(interaction.guild.id)

        cursor.execute("DELETE FROM temp_mvps WHERE game_id=?",
                       (self.game.game_id, ))
        db.commit()

        cursor.execute("INSERT INTO temp_mvps VALUES (?, ?)",
                       (self.game.game_id, ",".join(self.item.values)))
        db.commit()

        for option in self.item.options:
            if option.value in self.item.values:
                option.default = True

        try:
            await interaction.message.edit(view=self.view)
        except:
            ...
        await interaction.response.defer()
