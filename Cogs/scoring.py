import traceback

from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands._types import BotT

import classes
import errors
import parameters
from Checks import discordchecks
from Cooldowns import usercooldown
from Functions import functions

from typing import Literal

from Scoring import views as ScoringViews, buttons as ScoringButtons, selects as ScoringSelects, \
    functions as ScoringFuncs


class Scoring(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "Scoring"
        self.emoji = "📋"
        self.description = "Scoring Commands."

    @commands.command(name="scoregame", aliases=["fscore", "game"], description="Calculates The OutCome of a Game")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def scoregame(self, ctx: commands.Context,
                        game_id: int = parameters.GAME_ID,
                        winning_team_number: Literal[1, 2] = parameters.WINNING_TEAM_NUMBER,
                        *, mvps_data: str = parameters.MVPS):

        game = classes.Game.from_game_id(game_id, ctx.guild, ctx.bot)

        if not game.can_be_scored():
            raise errors.ScoringError("Game#{} cannot be scored at its' current state.".format(game.game_id))

        if game is None:
            raise errors.ScoringError(f"Game#{game_id} does not exist.")

        mvps_ids = []

        if mvps_data is not None:
            for mvp_data in list(mvps_data.split(" ")):
                mvp_member = await functions.fetch_member(mvp_data, ctx.guild)
                mvps_ids.append(mvp_member.id)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        scoring_message = await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Scoring System",
                f"Scoring Game#{game.game_id}..."
            ),
            wait=True
        )

        game_scored_msg = await game.score_game(winning_team_number, mvps_ids, ctx.author)

        await scoring_message.edit(
            embed=functions.embed(
                ctx.guild,
                "Scoring System",
                f"Scored Game#{game.game_id}. {game_scored_msg.jump_url}"
            )
        )

        await game.close_tc_and_vcs("Game Scored.")

    @commands.command(name="mvp", description="Gives MVP bonus")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def mvp(self, ctx: commands.Context,
                  game_id: int = parameters.GAME_ID,
                  player_data: str = parameters.PLAYER_DATA):
        game = classes.Game.from_game_id(game_id, ctx.guild, ctx.bot)

        if game is None:
            raise errors.GameDoesNotExist(game_id)

        member = await functions.fetch_member(player_data, ctx.guild)

        player = classes.NewPlayer.from_player_id(member.id, ctx.guild)

        if player is None:
            raise errors.MemberNotRegistered(member.id)

        scored_game = classes.ScoredGame.from_game_id(game_id, ctx.guild, ctx.bot)

        if scored_game is None:
            raise errors.QueueError(f"Game#{game_id} is not scored.")

        if member.id not in game.players_ids:
            raise errors.QueueError(f"Player({member.mention}) did not play in this game.")

        if member.id in scored_game.mvps_ids:
            raise errors.ScoringError(f"Player({member.mention}) has already got the MVP bonus.")

        old_elo = 0
        new_elo = 0

        if member.id in game.team1_players_ids:
            for i, team1_player_id_elo_change in enumerate(scored_game.team1_elo_changes):
                team1_player_id, team1_player_elo_change = team1_player_id_elo_change
                if team1_player_id == member.id:
                    old_elo = player.elo
                    player.elo += player.rank.mvp_elo
                    new_elo = player.elo
                    player.mvps += 1

                    scored_game.team1_elo_changes[i] = (team1_player_id, new_elo - old_elo + team1_player_elo_change)

                    try:
                        await functions.fix(member, nick_check=True, rank_check=True)
                    except:
                        pass

                    break
        else:
            for i, team2_player_id_elo_change in enumerate(scored_game.team2_elo_changes):
                team2_player_id, team2_player_elo_change = team2_player_id_elo_change
                if team2_player_id == member.id:
                    old_elo = player.elo
                    player.elo += player.rank.mvp_elo
                    new_elo = player.elo
                    player.mvps += 1

                    scored_game.team2_elo_changes[i] = (team2_player_id, new_elo - old_elo + team2_player_elo_change)

                    try:
                        await functions.fix(member, nick_check=True, rank_check=True)
                    except:
                        pass

                    break

        new_team1_elo_changes_str = ",".join([f"{t1},{t2}" for t1, t2 in scored_game.team1_elo_changes])
        new_team2_elo_changes_str = ",".join([f"{t1},{t2}" for t1, t2 in scored_game.team2_elo_changes])
        scored_game.mvps_ids.append(member.id)
        new_mvps_str = ','.join([str(t) for t in scored_game.mvps_ids])

        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("UPDATE scored_games SET team1=?,team2=?,mvps=? WHERE game_id=?",
                       (new_team1_elo_changes_str, new_team2_elo_changes_str, new_mvps_str, game_id))
        db.commit()

        scoring_channel = await functions.fetch_channel('SCORING', ctx.guild)

        scoring_channel_webhook = await functions.fetch_webhook(scoring_channel, ctx.bot)

        await scoring_channel_webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Scoring System",
                f"{member.mention} `{new_elo - old_elo if new_elo - old_elo < 0 else f'+{new_elo - old_elo}'}` "
                f"[`{old_elo}` ➜ `{new_elo}`]"
            )
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Scoring System",
                f"Successfully game Player({member.mention}) the MVP bonus "
                f"for game#{game_id}."
            )
        )

    @commands.command(name="unscoredgames", description="Shows all unscored games")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def unscoredgames(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        unscored_games_ids_tuples = cursor.execute("SELECT game_id FROM games WHERE status='SUBMITTED'").fetchall()
        unscored_games_ids = [str(t[0]) for t in unscored_games_ids_tuples]

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Unscored games IDs",
                "\n".join(unscored_games_ids)
            )
        )

    @commands.command(name="voidgame", aliases=['undo'], description="Voids the Game or Reverts its outcome")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def voidgame(self, ctx: commands.Context,
                       game_id: int = parameters.GAME_ID):
        game = classes.Game.from_game_id(game_id, ctx.guild, ctx.bot)

        if game is None:
            raise errors.GameDoesNotExist(game_id)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        if game.status == "SCORED":
            await game.scored_game.void_game(ctx.author)
            await webhook.send(
                embed=functions.embed(
                    ctx.guild,
                    "Scoring System",
                    f"Successfully Undone game#{game.game_id}"
                )
            )

        elif game.status == "SUBMITTED":
            await game.void_game(ctx.author, "Game voiding")
            await webhook.send(
                embed=functions.embed(
                    ctx.guild,
                    "Scoring System",
                    f"Successfully Voided game#{game.game_id} Completely"
                )
            )
        else:
            await webhook.send(
                embed=functions.embed(
                    ctx.guild,
                    "",
                    "You cannot void this game in its' current state."
                )
            )

    @commands.command(name="topscorers", description="Shows Top Scorers of the season", aliases=["ts"])
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def topscorers(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        scorers = []

        for scorer_id_tuple in cursor.execute("SELECT DISTINCT scored_by FROM scored_games").fetchall():
            games_scored_count = cursor.execute("SELECT COUNT(*) FROM scored_games WHERE scored_by=?",
                                                scorer_id_tuple).fetchone()
            scorers.append((scorer_id_tuple[0], games_scored_count[0]))

        scorers.sort(key=lambda scorer_tuple: scorer_tuple[1], reverse=True)

        embed_description_items = []
        for i, scorer_tuple in enumerate(scorers):
            scorer_id, games_scored_count = scorer_tuple
            embed_description_items.append(f"#{i + 1} <@{scorer_id}> : {games_scored_count}")

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Scorers",
                '\n'.join(embed_description_items),
                embed_footer_text=True
            ),
        )

    @commands.command(name="topssers", description="Shows Top Screensharers of the season", aliases=["tss"])
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def topssers(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        ssers = []

        for sser_id_tuple in cursor.execute("SELECT DISTINCT screensharer FROM screenshares").fetchall():
            if sser_id_tuple[0] is None:
                continue

            ss_count = cursor.execute("SELECT COUNT(*) FROM screenshares WHERE screensharer=?",
                                      sser_id_tuple).fetchone()
            ssers.append((sser_id_tuple[0], ss_count[0]))

        ssers.sort(key=lambda ss_tuple: ss_tuple[1], reverse=True)

        embed_description_items = []
        for i, sser_tuple in enumerate(ssers):
            sser_id, ss_count = sser_tuple
            embed_description_items.append(f"#{i + 1} <@{sser_id}> : {ss_count}")

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Screensharers",
                '\n'.join(embed_description_items),
                embed_footer_text=True
            ),
        )

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(
            ScoringButtons.ScoringButtonWinnerTeam1,
            ScoringButtons.ScoringButtonWinnerTeam2,
            ScoringButtons.ScoringButtonDone,
            ScoringButtons.ScoringButtonRefresh,
            ScoringButtons.ScoringButtonVoid,
            ScoringSelects.ScoringSelectMVPs
        )

    async def cog_unload(self) -> None:
        pass

    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        await functions.error_handler(ctx, error, traceback.format_exc())


async def setup(bot: commands.Bot):
    await bot.add_cog(Scoring(bot))
