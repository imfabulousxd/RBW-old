import asyncio
import datetime
import glob
import io
import logging
import re
import sqlite3
import traceback
import zoneinfo
from typing import Union, Optional, Literal

import aiohttp
import asqlite
import discord

import errors
import parameters
from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord.ext.commands._types import BotT

import classes
from Checks import discordchecks
from Cooldowns import usercooldown
from Functions import functions

from PIL import Image, ImageDraw, ImageFont
import config


logger = logging.getLogger(__name__)


class Leaderboards(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "Leaderboards"
        self.emoji = "🏅"
        self.description = "leaderboard/stats commands"

    @commands.command(name="editcard",
                      description="Edits Player's Card")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def editcard(self, ctx: commands.Context,
                       card_name: str = parameters.parameter(displayed_name='Card name')):
        db, cursor = functions.database(ctx.guild.id)

        all_cards = [t[0] for t in cursor.execute("SELECT card_name FROM cards").fetchall()]

        if card_name not in all_cards:
            raise commands.errors.BadLiteralArgument(parameters.parameter(displayed_name='Card name'), tuple(all_cards),
                                                     [commands.CommandError(ctx.message.content)], card_name)

        cursor.execute("DELETE FROM cardusers WHERE member_id=?",
                       (ctx.author.id, ))
        db.commit()

        cursor.execute("INSERT INTO cardusers VALUES  (?, ?)",
                       (ctx.author.id, card_name))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Cards",
                f"Set your default card as `{card_name}`."
            )
        )

    @commands.command(name="stats", aliases=['info', 'me', 'i'], description='Displays self or another Player Stats')
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def stats(self, ctx: commands.Context, member_data: Optional[str] = parameters.PLAYER_DATA_OPTIONAL,
                    mode: Optional[Literal['--image', '--text']] = parameters.parameter(displayed_name="Mode (--text or --image)", default='--image')):
        player = None
        member = None
        if member_data is None:

            member = ctx.author
            player = classes.NewPlayer.from_player_id(ctx.author.id, ctx.guild)

        else:

            member = await functions.fetch_member(member_data, ctx.guild)
            player = classes.NewPlayer.from_player_id(member.id,
                                                      ctx.guild)

        if player is None:
            raise errors.MemberNotRegistered(member.id)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        if mode == '--image':
            stats_file = await get_stats_image(player)

            await webhook.send(
                file=stats_file
            )
        else:
            games_list = []

            for game_id in player.games_ids[-5:]:
                game = classes.Game.from_game_id(game_id, ctx.guild)
                if game.is_scored():
                    if player.player_id in game.scored_game.winner_team_ids:
                        if player.player_id in game.scored_game.mvps_ids:
                            games_list.append(f"#{game_id} 🏆 🔥")
                        else:
                            games_list.append(f"#{game_id} 🏆")
                    else:
                        if player.player_id in game.scored_game.mvps_ids:
                            games_list.append(f"#{game_id} 🔴 🔥")
                        else:
                            games_list.append(f"#{game_id} 🔴")
                elif game.status == "VOIDED":
                    games_list.append(f"#{game_id} ☄️")
                else:
                    games_list.append(f"#{game_id} ⏳")

            stats_embed = functions.embed(
                ctx.guild,
                f"Player System",
                f"{member.mention}s' Stats",
                embed_fields=[
                    [
                        f"General Stats",
                        f"**ELO: **{player.elo}\n"
                        f"Peak: {player.peak_elo}\n"
                        f"MVPs: {player.mvps}\n"
                        f"Streak: {f'+{player.streak}' if player.streak > 0 else f'{player.streak}'}\n"
                        f"Wins: {player.wins}\n"
                        f"Losses: {player.losses}\n"
                        f"WLR: {player.wlr}\n"
                        f"WinRate: {player.winrate}\n"
                        f"Games Played: {player.games_played}\n"
                        f"Daily ELO: {player.daily_elo}{'🔸' if player.daily_elo == 0 else ''}{'🔻' if player.daily_elo < 0 else ''}{'🔺' if player.daily_elo > 0 else ''}\n"
                        f"Weekly ELO: {player.weekly_elo}{'🔸' if player.weekly_elo == 0 else ''}{'🔻' if player.weekly_elo < 0 else ''}{'🔺' if player.weekly_elo > 0 else ''}\n",
                        False
                    ],
                    [
                        "Recent Games",
                        '\n'.join(games_list),
                        False
                    ]
                ],
                embed_footer_text='Joined at',
                embed_timestamp=member.joined_at
            )

            await webhook.send(
                embed=stats_embed
            )

    @commands.command(name="viewgame", aliases=['vg'], description='Displays Game info')
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def viewgame(self, ctx: commands.Context, game_id: int = parameters.GAME_ID):
        game = classes.Game.from_game_id(game_id, ctx.guild, ctx.bot)
        if game is None:
            raise errors.LeaderboardsError(f"Game#{game_id} not found.")

        game_embed_fields = []
        if game.is_scored():
            game_embed_fields.append(["Scored", "🟩", True])
            game_embed_fields.append(["Voided", "🟥", True])
        elif game.status == "SUBMITTED":
            game_embed_fields.append(["Scored", "⏳", True])
            game_embed_fields.append(["Voided", "🟥", True])
        elif game.status == "VOIDED":
            game_embed_fields.append(["Scored", "🟥", True])
            game_embed_fields.append(["Voided", "☄️", True])
        else:
            game_embed_fields.append(["Scored", "🟥", True])
            game_embed_fields.append(["Voided", "🟥", True])

        if game.is_scored():
            scored_game = game.scored_game
            game_embed_fields.append(
                [
                    f"Winning Team {scored_game.winner}",
                    "\n".join(
                        [f"{'🔥' if t in scored_game.mvps_ids else '🟩'} <@{t}>" for t in scored_game.winner_team_ids]
                    ), False
                ]
            )
            game_embed_fields.append(
                [
                    f"Losing Team {scored_game.loser}",
                    "\n".join(
                        [f"{'🔥' if t in scored_game.mvps_ids else '🟥'} <@{t}>" for t in scored_game.loser_team_ids]
                    ), True
                ]
            )
            game_embed_fields.append(
                [
                    f"Scored By",
                    f"<@{scored_game.scored_by}>", False
                ]
            )
        else:
            game_embed_fields.extend(
                [["Team 1", "\n".join([f"⬛ <@{t}>" for t in game.team1_players_ids]), False],
                 ["Team 2", "\n".join([f"⬛ <@{t}>" for t in game.team2_players_ids]), True]]
            )
            if game.remaining_players_ids:
                game_embed_fields.append(["Remaining Players", '\n'.join([f"<@{t}>" for t in game.remaining_players_ids]), False])

            if game.status == "VOIDED":
                db, cursor = functions.database(ctx.guild.id)
                voided_by = cursor.execute("SELECT voided_by FROM voided_games WHERE game_id=?",
                               (game.game_id, )).fetchone() or (0, )
                game_embed_fields.append(["Voided By", f"<@{voided_by[0]}>", False])

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Game System",
                f"Game#{game_id}",
                embed_timestamp=True,
                embed_footer_text=True,
                embed_fields=game_embed_fields
            )
        )

    @commands.command(name="games", aliases=['g'], description='Displays self or another Players\' Games')
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def games(self, ctx: commands.Context,
                    member_data: str = parameters.PLAYER_DATA_OPTIONAL,
                    page: int = parameters.PAGE):
        member = ctx.author
        if member_data is not None:
            member = await functions.fetch_member(member_data, ctx.guild)
        player = classes.NewPlayer.from_player_id(member.id, ctx.guild)
        if player is None:
            raise errors.MemberNotRegistered(member.id)

        games_list = []

        for game_id in player.games_ids[::-1]:
            game = classes.Game.from_game_id(game_id, ctx.guild)
            if game.is_scored():
                if player.player_id in game.scored_game.winner_team_ids:
                    if player.player_id in game.scored_game.mvps_ids:
                        games_list.append(f"#{game_id} 🏆 🔥")
                    else:
                        games_list.append(f"#{game_id} 🏆")
                else:
                    if player.player_id in game.scored_game.mvps_ids:
                        games_list.append(f"#{game_id} 🔴 🔥")
                    else:
                        games_list.append(f"#{game_id} 🔴")
            elif game.status == "VOIDED":
                games_list.append(f"#{game_id} ☄️")
            else:
                games_list.append(f"#{game_id} ⏳")

        await functions.send_leaderboard_message(
            ctx.channel,
            ctx.bot,
            games_list,
            9,
            f"Games for {player.ign}",
            "",
            "\n"
            "🏆: Won\n"
            "🔴: Lost\n"
            "🔥: MVP\n"
            "⏳: Pending\n"
            "☄️: Voided",
            page,
            ctx.author.id
        )

    @commands.command(name="leaderboard", aliases=['lb'], description='Displays Global Leaderboard Positions')
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def leaderboard(self, ctx: commands.Context,
                          mode: Literal["elo",
                                        "mvps",
                                        "wins",
                                        "losses",
                                        "wlr",
                                        "games",
                                        "peak_elo",
                                        "peak",
                                        "winrate",
                                        "wr",
                                        "winstreak",
                                        "ws",
                                        "losestreak",
                                        "ls",
                                        "peak_ws",
                                        "peak_ls"] = parameters.LEADERBOARD_MODE,
                          page: int = parameters.PAGE):
        modes = {
            "elo": "elo",
            "mvps": "mvps",
            "wins": "wins",
            "losses": "losses",
            "wlr": "wlr",
            "games": "games_played",
            "peak_elo": "peak_elo",
            "peak": "peak_elo",
            "winrate": "winrate",
            "wr": "winrate",
            "winstreak": "winstreak",
            "ws": "winstreak",
            "losestreak": "losestreak",
            "ls": "losestreak",
            "peak_ws": "peak_winstreak",
            "peak_ls": "peak_losestreak"
        }

        showing_modes = {
            "elo": "ELO",
            "mvps": "MVPs",
            "wins": "Wins",
            "losses": "Losses",
            "wlr": "WLR",
            "games": "Games played",
            "peak_elo": "Peak ELO",
            "peak": "Peak ELO",
            "winrate": "Winrate",
            "wr": "Winrate",
            "winstreak": "Winstreak",
            "ws": "Winstreak",
            "losestreak": "Losestreak",
            "ls": "Losestreak",
            "peak_ws": "Peak winstreak",
            "peak_ls": "Peak losestreak"
        }

        mode_list = []

        db, cursor = functions.database(ctx.guild.id)
        for player_id_tuple in cursor.execute("SELECT id FROM players").fetchall():
            player = classes.NewPlayer.from_player_id(player_id_tuple[0], ctx.guild)
            mode_list.append((getattr(player, modes[mode]), player.ign))

        mode_list.sort(reverse=True)

        lb_list = [f"** #{i + 1} {stat_ign_tuple[1]} •** {stat_ign_tuple[0]}" for i, stat_ign_tuple in enumerate(mode_list)]

        await functions.send_leaderboard_message(ctx.channel,
                                                 ctx.bot,
                                                 lb_list,
                                                 10,
                                                 "Leaderboard",
                                                 f"**{showing_modes[mode]} Leaderboard**\n\n",
                                                 "",
                                                 page,
                                                 ctx.author.id)

    @commands.command(name="weekly", aliases=['wl'], description='Displays Weekly Leaderboard Positions')
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def weekly(self, ctx: commands.Context,
                          mode: Literal["elo",
                                        "mvps",
                                        "wins",
                                        "losses",
                                        "wlr",
                                        "games",
                                        "winrate",
                                        "wr"] = parameters.LEADERBOARD_MODE,
                          page: int = parameters.PAGE):
        modes = {
            "elo": "elo",
            "mvps": "mvps",
            "wins": "wins",
            "losses": "losses",
            "wlr": "wlr",
            "games": "games_played",
            "winrate": "winrate",
            "wr": "winrate"
        }

        showing_modes = {
            "elo": "ELO",
            "mvps": "MVPs",
            "wins": "Wins",
            "losses": "Losses",
            "wlr": "WLR",
            "games": "Games played",
            "winrate": "Winrate",
            "wr": "Winrate"
        }

        mode_list = []

        db, cursor = functions.database(ctx.guild.id)
        for player_id_tuple in cursor.execute("SELECT id FROM players").fetchall():
            player = classes.NewPlayer.from_player_id(player_id_tuple[0], ctx.guild)
            mode_list.append((getattr(player, f"weekly_{modes[mode]}"), player.ign))

        mode_list.sort(reverse=True)

        lb_list = [f"** #{i + 1} {stat_ign_tuple[1]} •** {stat_ign_tuple[0]}" for i, stat_ign_tuple in
                   enumerate(mode_list)]

        weekly_reset_at: datetime.datetime = functions.get_info_value("WEEKLYLBRESET", ctx.guild)

        await functions.send_leaderboard_message(ctx.channel,
                                                 ctx.bot,
                                                 lb_list,
                                                 10,
                                                 "Leaderboard",
                                                 f"**{showing_modes[mode]} Leaderboard**\n\n",
                                                 f"\nResets <t:{weekly_reset_at.timestamp().__int__()}:R>",
                                                 page,
                                                 ctx.author.id)

    @commands.command(name="daily", aliases=['d'], description='Displays Daily Leaderboard Positions')
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def daily(self, ctx: commands.Context,
                     mode: Literal["elo",
                     "mvps",
                     "wins",
                     "losses",
                     "wlr",
                     "games",
                     "winrate",
                     "wr"] = parameters.LEADERBOARD_MODE,
                     page: int = parameters.PAGE):
        modes = {
            "elo": "elo",
            "mvps": "mvps",
            "wins": "wins",
            "losses": "losses",
            "wlr": "wlr",
            "games": "games_played",
            "winrate": "winrate",
            "wr": "winrate"
        }

        showing_modes = {
            "elo": "ELO",
            "mvps": "MVPs",
            "wins": "Wins",
            "losses": "Losses",
            "wlr": "WLR",
            "games": "Games played",
            "winrate": "Winrate",
            "wr": "Winrate"
        }

        mode_list = []

        db, cursor = functions.database(ctx.guild.id)
        for player_id_tuple in cursor.execute("SELECT id FROM players").fetchall():
            player = classes.NewPlayer.from_player_id(player_id_tuple[0], ctx.guild)
            mode_list.append((getattr(player, f"daily_{modes[mode]}"), player.ign))

        mode_list.sort(reverse=True)

        lb_list = [f"** #{i + 1} {stat_ign_tuple[1]} •** {stat_ign_tuple[0]}" for i, stat_ign_tuple in
                   enumerate(mode_list)]

        daily_reset_at: datetime.datetime = functions.get_info_value("DAILYLBRESET", ctx.guild)

        await functions.send_leaderboard_message(ctx.channel,
                                                 ctx.bot,
                                                 lb_list,
                                                 10,
                                                 "Leaderboard",
                                                 f"**{showing_modes[mode]} Leaderboard**\n\n",
                                                 f"\nResets <t:{daily_reset_at.timestamp().__int__()}:R>",
                                                 page,
                                                 ctx.author.id)

    async def cog_load(self) -> None:
        for guild_folder_path in glob.glob("Guilds/*"):
            guild_id = int(re.compile(r"Guilds[/\\]([0-9]+)").fullmatch(guild_folder_path).group(1))

            asyncio.create_task(self.reset_daily_leaderboard(guild_id))
            asyncio.create_task(self.reset_weekly_leaderboard(guild_id))

    async def cog_unload(self) -> None:
        pass

    # noinspection SqlWithoutWhere
    @staticmethod
    async def reset_daily_leaderboard(guild_id: int):
        def reset_daily_lb():
            db, cursor = functions.database(guild_id)
            cursor.execute("DELETE FROM daily")
            db.commit()

            cursor.execute("DELETE FROM info WHERE info_name='LASTDAILYLBRESET'")
            db.commit()

            cursor.execute("INSERT INTO info VALUES (?, ?)",
                           ('LASTDAILYLBRESET', datetime.datetime.now().timestamp().__int__()))
            db.commit()
            logger.info(f"[Guild: {guild_id}]: Reset daily leaderboard")

        now = datetime.datetime.now()
        reset_at: datetime.datetime = functions.get_info_value('DAILYLBRESET', guild_id)

        db, cursor = functions.database(guild_id)

        if reset_at - datetime.timedelta(days=1) > datetime.datetime.fromtimestamp(
                (cursor.execute("SELECT info_value FROM info WHERE info_name='LASTDAILYLBRESET'").fetchone() or (0,))[0]):
            reset_daily_lb()

        await asyncio.sleep((reset_at - now).seconds)

        while 1:
            reset_daily_lb()
            await asyncio.sleep(24 * 3600)

    # noinspection SqlWithoutWhere
    @staticmethod
    async def reset_weekly_leaderboard(guild_id: int):
        def reset_weekly_lb():
            db, cursor = functions.database(guild_id)
            cursor.execute("DELETE FROM weekly")
            db.commit()

            cursor.execute("DELETE FROM info WHERE info_name='LASTWEEKLYLBRESET'")
            db.commit()

            cursor.execute("INSERT INTO info VALUES (?, ?)",
                           ('LASTWEEKLYLBRESET', datetime.datetime.now().timestamp().__int__()))
            db.commit()
            logger.info(f"[Guild: {guild_id}]: Reset weekly leaderboard")

        now = datetime.datetime.now()
        reset_at: datetime.datetime = functions.get_info_value('WEEKLYLBRESET', guild_id)

        db, cursor = functions.database(guild_id)

        if reset_at - datetime.timedelta(weeks=1) > datetime.datetime.fromtimestamp(
                (cursor.execute("SELECT info_value FROM info WHERE info_name='LASTWEEKLYLBRESET'").fetchone() or (0,))[
                    0]):
            reset_weekly_lb()

        await asyncio.sleep((reset_at - now).seconds)

        while 1:
            reset_weekly_lb()
            await asyncio.sleep(7 * 24 * 3600)

    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        await functions.error_handler(ctx, error, traceback.format_exc())


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboards(bot))


async def get_stats_image(player: classes.NewPlayer):
    db, cursor = functions.database(player.guild.id)

    card_name_tuple = cursor.execute("SELECT card_name FROM cardusers WHERE member_id=?",
                                     (player.player_id,)).fetchone()
    card_name = card_name_tuple[0] if card_name_tuple is not None else \
        functions.get_info_value("DEFAULTCARDNAME", player.guild)

    card_info_tuple = cursor.execute("SELECT * FROM cards WHERE card_name=?",
                                     (card_name,)).fetchone()

    card = classes.Card.from_tuple(card_info_tuple, player.guild)

    card_image = Image.open(f'Guilds/{player.guild.id}/Cards/{card.card_file_name}')

    drawer = ImageDraw.Draw(card_image)

    default_font = ImageFont.truetype('Minecraftia-Regular.ttf', size=20)

    # discord name
    if card.discord_name is not None:
        player.member = await functions.fetch_member(player.player_id, player.guild)

        discord_name_font, discord_name_box = fetch_font_size(player.member.name, default_font, card.discord_name[:4])

        drawer.text(discord_name_box, text=player.member.name, fill=int_to_rgb(card.discord_name[4]),
                    font=discord_name_font)

    # ign
    if card.ign is not None:
        ign_font, ign_box = fetch_font_size(player.ign, default_font, card.ign[:4])

        drawer.text(ign_box, text=player.ign, fill=int_to_rgb(card.ign[4]), font=ign_font)

    # elo
    if card.elo is not None:
        elo_font, elo_box = fetch_font_size(str(player.elo), default_font, card.elo[:4])

        drawer.text(elo_box, text=str(player.elo), fill=int_to_rgb(player.rank.role_color), font=elo_font)

    # daily elo
    if card.daily_elo is not None:

        daily_elo_font, daily_elo_box = fetch_font_size(str(player.daily_elo), default_font, card.daily_elo[:4])

        drawer.text(daily_elo_box,
                    text=str(player.daily_elo),
                    fill=int_to_rgb(card.daily_elo[4] if player.daily_elo > 0 else (card.daily_elo[5] if player.daily_elo < 0 else card.daily_elo[6])),
                    font=daily_elo_font)

    # wins
    if card.wins is not None:
        wins_font, wins_box = fetch_font_size(str(player.wins), default_font, card.wins[:4])

        drawer.text(wins_box, text=str(player.wins), fill=int_to_rgb(card.wins[4]), font=wins_font)

    # losses
    if card.losses is not None:
        losses_font, losses_box = fetch_font_size(str(player.losses), default_font, card.losses[:4])

        drawer.text(losses_box, text=str(player.losses), fill=int_to_rgb(card.losses[4]), font=losses_font)

    # streak
    if card.streak is not None:
        streak_font, streak_box = fetch_font_size(str(player.streak), default_font, card.streak[:4])

        streak_font_color = None

        if player.streak > 0:
            streak_font_color = int_to_rgb(card.streak[4])
        elif player.streak < 0:
            streak_font_color = int_to_rgb(card.streak[5])
        else:
            streak_font_color = int_to_rgb(card.streak[6])

        drawer.text(streak_box, text=str(player.streak), fill=streak_font_color, font=streak_font)

    # mvps
    if card.mvps is not None:
        mvps_font, mvps_box = fetch_font_size(str(player.mvps), default_font, card.mvps[:4])

        drawer.text(mvps_box, text=str(player.mvps), fill=int_to_rgb(card.mvps[4]), font=mvps_font)

    # games played
    if card.games_played is not None:
        games_played_font, games_played_box = fetch_font_size(str(player.games_played), default_font, card.games_played[:4])

        drawer.text(games_played_box, text=str(player.games_played), fill=int_to_rgb(card.games_played[4]),
                    font=games_played_font)

    # wlr
    if card.wlr is not None:
        wlr_font, wlr_box = fetch_font_size(f"{player.wlr: .2f}", default_font, card.wlr[:4])

        drawer.text(wlr_box, text=f"{player.wlr: .2f}", fill=int_to_rgb(card.wlr[4]), font=wlr_font)

    # winrate
    if card.winrate is not None:
        winrate_font, winrate_box = fetch_font_size(f"{player.winrate.__int__()}%", default_font, card.winrate[:4])

        drawer.text(winrate_box, text=f"{player.winrate.__int__()}%", fill=int_to_rgb(card.winrate[4]), font=winrate_font)

    # games
    if card.games is not None:
        games: list[tuple[str, tuple[int, int, int]]] = []
        for game_id in player.games_ids[-5:]:
            game = classes.Game.from_game_id(game_id, player.guild)
            if game.is_scored():
                scored_game = game.scored_game
                if player.player_id in scored_game.winner_team_ids:
                    if player.player_id in scored_game.mvps_ids:
                        games.append((f"# {game.game_id}", int_to_rgb(card.games[4])))
                    else:
                        games.append((f"# {game.game_id}", int_to_rgb(card.games[5])))
                else:
                    games.append((f"# {game.game_id}", int_to_rgb(card.games[6])))
            elif game.status == "VOIDED":
                games.append((f"# {game.game_id}", int_to_rgb(card.games[7])))
            else:
                games.append((f"# {game.game_id}", int_to_rgb(card.games[8])))

        games.reverse()

        games_height = (int(card.games[3]) - int(card.games[1])) / 5
        games_start_at_y = int(card.games[1])
        games_end_at_y = int(card.games[1]) + games_height

        for game_num_str, rgb_color in games:
            game_placed_at_tuple = (int(card.games[0]), games_start_at_y, int(card.games[2]), games_end_at_y)
            game_font, game_box = fetch_font_size(
                game_num_str, default_font,
                game_placed_at_tuple,
                center=False)
            drawer.text(game_box, text=game_num_str, fill=rgb_color, font=game_font)

            games_start_at_y += games_height
            games_end_at_y += games_height

    # rank
    if card.rank is not None:
        rank_font, rank_box = fetch_font_size(str(player.leaderboard_spot), default_font, card.rank[:4])

        drawer.text(rank_box, text=str(player.leaderboard_spot), fill=int_to_rgb(card.rank[4]), font=rank_font)

    # rank icon
    if card.rank_icon is not None:
        rank_icon = Image.open(glob.glob(f"Guilds/{player.guild.id}/Ranks/{player.rank.role_id}.*")[0])

        rank_icon = rank_icon.convert('RGBA')

        rank_icon_size_multiplier = ((int(card.rank_icon[2]) - int(card.rank_icon[0])) / rank_icon.width if
                                     ((int(card.rank_icon[2]) - int(card.rank_icon[0])) / rank_icon.width) <=
                                     ((int(card.rank_icon[3]) - int(card.rank_icon[1])) / rank_icon.height)
                                     else (int(card.rank_icon[3]) - int(card.rank_icon[1])) / rank_icon.height)

        rank_icon = rank_icon.resize(
            (int(rank_icon.width * rank_icon_size_multiplier), int(rank_icon.height * rank_icon_size_multiplier)))

        card_image.paste(rank_icon, (
            int(int(card.rank_icon[0]) + (int(card.rank_icon[2]) - int(card.rank_icon[0])) / 2 - rank_icon.width / 2),
            int(int(card.rank_icon[1]) + (int(card.rank_icon[3]) - int(card.rank_icon[1])) / 2 - rank_icon.height / 2)
        ), rank_icon)

    # skin
    if card.skin is not None:
        skin_image_bytes_io = None
        try:
            async with aiohttp.ClientSession() as client_session:
                uuid = None
                mojang_response = await client_session.get(f'https://api.mojang.com/users/profiles/minecraft/{player.ign}')
                if mojang_response.ok:
                    uuid = (await mojang_response.json())['id']
                else:
                    mojang_response.raise_for_status()
                async with client_session.get(f"https://visage.surgeplay.com/full/384/{uuid}", headers={
                    "User-Agent": config.USER_AGENT
                }, timeout=3) as response:
                    if response.ok:
                        skin_image_bytes_io = io.BytesIO(await response.read())
                    else:
                        response.raise_for_status()
        except:
            file = open('default-skin.png', 'rb')
            skin_image_bytes_io = io.BytesIO(file.read())

        skin_image_bytes_io.seek(0)

        skin_image = Image.open(skin_image_bytes_io)

        skin_image = skin_image.convert('RGBA')

        skin_image_size_multiplier_x = (int(card.skin[2]) - int(card.skin[0])) / skin_image.width
        skin_image_size_multiplier_y = (int(card.skin[3]) - int(card.skin[1])) / skin_image.height

        skin_image_size_multiplier = skin_image_size_multiplier_x if \
            skin_image_size_multiplier_x <= skin_image_size_multiplier_y \
            else skin_image_size_multiplier_y

        skin_image = skin_image.resize(
            (int(skin_image.width * skin_image_size_multiplier), int(skin_image.height * skin_image_size_multiplier)))

        card_image.paste(skin_image, (
            int(int(card.skin[0]) + (int(card.skin[2]) - int(card.skin[0])) / 2 - skin_image.width / 2),
            int(int(card.skin[1]) + (int(card.skin[3]) - int(card.skin[1])) / 2 - skin_image.height / 2)
        ), skin_image)

    image_binary = io.BytesIO()

    card_image.save(image_binary, card.card_file_type)

    image_binary.seek(0)

    return discord.File(image_binary, filename=f"{player.ign}.{card.card_file_type}")


def fetch_font_size(text: str, font: ImageFont.FreeTypeFont, box_tuple: tuple, minus_amount: int = 0,
                    center: bool = True,
                    *args, **kwargs):
    left_padding = 0
    box_start_x = int(box_tuple[0])
    box_start_y = int(box_tuple[1])
    box_end_x = int(box_tuple[2])
    box_end_y = int(box_tuple[3])

    box_width = box_end_x - box_start_x
    box_height = box_end_y - box_start_y

    font_size = 1
    temp_font_size = 1
    while 1:
        font = font.font_variant(size=temp_font_size)
        left, top, right, bottom = font.getbbox(text)
        if right - left > box_width or bottom - top > box_height:
            break
        else:
            font_size = temp_font_size
            temp_font_size += 1
            continue

    font = font.font_variant(size=font_size - minus_amount)

    left, top, right, bottom = font.getbbox(text)

    box_start_x = box_start_x + (box_width / 2) - (
            (right - left) / 2) + left_padding * box_width if center else box_start_x + left_padding * box_width
    box_start_y = box_start_y + (box_height / 2) - ((bottom - top) / 2)

    return font, (box_start_x, box_start_y)


def int_to_rgb(rgbint: Union[int, str]):
    rgbint = int(rgbint)
    return rgbint // 256 // 256 % 256, rgbint // 256 % 256, rgbint % 256
