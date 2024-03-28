import re
from typing import Type, Any

from discord import Interaction
from discord._types import ClientT
from discord.ui import Item
from typing_extensions import Self

import discord
from discord.ext import commands

from Checks import checks
import Scoring.functions
from Functions import functions
import classes


class ScoringButtonWinnerTeam1(discord.ui.DynamicItem[discord.ui.Button],
                               template=r'scoring:(?P<game_id>[0-9]+):button:winnerteam1'):
    def __init__(self, game_id: int):
        super().__init__(
            discord.ui.Button(
                label="1",
                style=discord.ButtonStyle.green,
                custom_id=f"scoring:{game_id}:button:winnerteam1",
            )
        )
        self.game_id = game_id

    @classmethod
    async def from_custom_id(
            cls, interaction: Interaction, item: discord.ui.Button, match: re.Match[str], /
    ) -> Self:
        game_id = int(match['game_id'])
        return cls(game_id)

    async def interaction_check(self, interaction: Interaction[ClientT], /) -> bool:
        if checks.check_cmd_permission(interaction.user, 'scoregame', interaction.client):
            return True

        interaction.response: discord.InteractionResponse
        await interaction.response.send_message(
            embed=functions.embed(
                interaction.guild,
                "",
                f"You don't have permission to use this."
            ),
            ephemeral=True
        )

    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        self.item.disabled = True

        for child in self.view.children:
            if not isinstance(child, discord.ui.Button):
                pass
            elif child.label == "2":
                child.disabled = False

        await interaction.message.edit(
            view=self.view
        )

        await interaction.response.send_message(
            "Set team 1 as the winner",
            ephemeral=True
        )


class ScoringButtonWinnerTeam2(discord.ui.DynamicItem[discord.ui.Button],
                               template=r'scoring:(?P<game_id>[0-9]+):button:winnerteam2'):
    def __init__(self, game_id: int):
        super().__init__(
            discord.ui.Button(
                label="2",
                style=discord.ButtonStyle.green,
                custom_id=f"scoring:{game_id}:button:winnerteam2",
            )
        )
        self.game_id = game_id

    @classmethod
    async def from_custom_id(
            cls, interaction: Interaction, item: discord.ui.Button, match: re.Match[str], /
    ) -> Self:
        game_id = int(match['game_id'])
        return cls(game_id)

    async def interaction_check(self, interaction: Interaction[ClientT], /) -> bool:
        if checks.check_cmd_permission(interaction.user, 'scoregame', interaction.client):
            return True

        interaction.response: discord.InteractionResponse
        await interaction.response.send_message(
            embed=functions.embed(
                interaction.guild,
                "",
                f"You don't have permission to use this."
            ),
            ephemeral=True
        )

    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        self.item.disabled = True

        for child in self.view.children:
            if not isinstance(child, discord.ui.Button):
                pass
            elif child.label == "1":
                child.disabled = False

        await interaction.message.edit(
            view=self.view
        )

        await interaction.response.send_message(
            "Set team 2 as the winner",
            ephemeral=True
        )


class ScoringButtonDone(discord.ui.DynamicItem[discord.ui.Button],
                        template=r'scoring:(?P<game_id>[0-9]+):button:done'):
    def __init__(self, game_id: int):
        super().__init__(
            discord.ui.Button(
                emoji='✅',
                style=discord.ButtonStyle.green,
                custom_id=f"scoring:{game_id}:button:done",
            )
        )
        self.game_id = game_id
        self.mvps_ids = None
        self.winner_team_number = 0

    @classmethod
    async def from_custom_id(
            cls, interaction: Interaction, item: discord.ui.Button, match: re.Match[str], /
    ) -> Self:
        game_id = int(match['game_id'])
        return cls(game_id)

    async def interaction_check(self, interaction: Interaction[ClientT], /) -> bool:
        if checks.check_cmd_permission(interaction.user, 'scoregame', interaction.client):
            return True

        interaction.response: discord.InteractionResponse
        await interaction.response.send_message(
            embed=functions.embed(
                interaction.guild,
                "",
                f"You don't have permission to use this."
            ),
            ephemeral=True
        )

    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        self.item.disabled = True

        for child in self.view.children:
            if isinstance(child, discord.ui.Button):
                if child.disabled and (child.label == "1" or child.label == "2"):
                    self.winner_team_number = int(child.label)

                if child.label == "1" or child.label == "2":
                    child.disabled = True

            elif isinstance(child, discord.ui.Select):
                child.disabled = True

        if self.winner_team_number == 0:
            interaction.response: discord.InteractionResponse
            await interaction.response.send_message(
                embed=functions.embed(interaction.guild,
                                      "",
                                      "No winner team selected.", )
                , ephemeral=True
            )
            return

        db, cursor = functions.database(interaction.guild.id)

        mvps_ids_tuple = cursor.execute("SELECT mvps FROM temp_mvps WHERE game_id=?",
                                        (self.game_id,)).fetchone()
        if mvps_ids_tuple is None:
            self.mvps_ids = []
        else:
            self.mvps_ids = [int(t) for t in mvps_ids_tuple[0].split(",")]

        cursor.execute("DELETE FROM temp_mvps WHERE game_id=?",
                       (self.game_id, ))
        db.commit()

        await interaction.message.edit(
            view=self.view
        )

        game = classes.Game.from_game_id(self.game_id, interaction.guild, interaction.client)

        await interaction.response.defer(thinking=True, ephemeral=True)

        await game.score_game(
            self.winner_team_number,
            self.mvps_ids,
            interaction.user
        )

        await interaction.edit_original_response(
            embed=functions.embed(
                interaction.guild,
                "",
                f"Scored game#{game.game_id}."
            )
        )

        await Scoring.functions.refresh_message(interaction, game, self.view)


class ScoringButtonRefresh(discord.ui.DynamicItem[discord.ui.Button],
                           template=r'scoring:(?P<game_id>[0-9]+):button:refresh'):
    def __init__(self, game_id: int):
        super().__init__(
            discord.ui.Button(
                emoji='🔄',
                style=discord.ButtonStyle.gray,
                custom_id=f"scoring:{game_id}:button:refresh",
            )
        )
        self.game_id = game_id

    @classmethod
    async def from_custom_id(
            cls, interaction: Interaction, item: discord.ui.Button, match: re.Match[str], /
    ) -> Self:
        game_id = int(match['game_id'])
        return cls(game_id)

    async def interaction_check(self, interaction: Interaction[ClientT], /) -> bool:
        if checks.check_cmd_permission(interaction.user, 'scoregame', interaction.client):
            return True

        interaction.response: discord.InteractionResponse
        await interaction.response.send_message(
            embed=functions.embed(
                interaction.guild,
                "",
                f"You don't have permission to use this."
            ),
            ephemeral=True
        )

    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        game = classes.Game.from_game_id(self.game_id, interaction.guild, interaction.client)

        await interaction.response.send_message(
            "Refreshed",
            ephemeral=True
        )

        await Scoring.functions.refresh_message(interaction, game, self.view)


class ScoringButtonVoid(discord.ui.DynamicItem[discord.ui.Button],
                        template=r'scoring:(?P<game_id>[0-9]+):button:void'):
    def __init__(self, game_id: int):
        super().__init__(
            discord.ui.Button(
                emoji='🟥',
                style=discord.ButtonStyle.red,
                custom_id=f"scoring:{game_id}:button:void",
            )
        )
        self.game_id = game_id

    @classmethod
    async def from_custom_id(
            cls, interaction: Interaction, item: discord.ui.Button, match: re.Match[str], /
    ) -> Self:
        game_id = int(match['game_id'])
        return cls(game_id)

    async def interaction_check(self, interaction: Interaction[ClientT], /) -> bool:
        if checks.check_cmd_permission(interaction.user, 'voidgame', interaction.client):
            return True

        interaction.response: discord.InteractionResponse
        await interaction.response.send_message(
            embed=functions.embed(
                interaction.guild,
                "",
                f"You don't have permission to use this."
            ),
            ephemeral=True
        )

    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        game = classes.Game.from_game_id(self.game_id, interaction.guild, interaction.client)

        if game.status == "SCORED":
            await interaction.response.defer(thinking=True, ephemeral=True)
            await game.scored_game.void_game(interaction.user)
            await interaction.edit_original_response(
                embed=functions.embed(
                    interaction.guild,
                    "Scoring System",
                    f"Successfully Undone game#{game.game_id}"
                )
            )
            await Scoring.functions.refresh_message(interaction, game, self.view)

        # elif game.status == "SUBMITTED":
        #     await interaction.response.defer(thinking=True, ephemeral=True)
        #     await game.void_game(interaction.user, "Game voiding")
        #     await interaction.edit_original_response(
        #         embed=functions.embed(
        #             interaction.guild,
        #             "Scoring System",
        #             f"Successfully Voided game#{game.game_id} Completely"
        #         )
        #     )
        #     await Scoring.functions.refresh_message(interaction, game, self.view)
        else:
            await interaction.response.send_message(
                embed=functions.embed(
                    interaction.guild,
                    "",
                    "You cannot void this game in its' current state.\n"
                    "Use the command =voidgame to void the game COMPLETELY (This action CANNOT BE UNDONE)"
                )
            )
