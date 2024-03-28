import asyncio
import datetime
import io
import logging
import sys
import traceback
from typing import Optional, Literal

import discord
from discord.ext import commands, tasks
import os

from discord.ext.commands import Context
from discord.ext.commands._types import BotT

import classes
import parameters
from Checks import discordchecks
from Functions import functions

from Scoring import views


class DevOnlyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "DevOnly"
        self.description = "Only the developer can use these commands."
        self.show_help = False

        asyncio.create_task(self.kick_under_30d())

    @commands.command(name="_execute",
                      description="executes a block of code (Only for bot developers)")
    async def _execute(self, ctx: commands.Context, *,
                       code: Optional[str]):
        if ctx.author.id not in self.bot.full_perm_users:
            return

        code_temp = ""

        for line in list(code.splitlines()):
            code_temp += f" {line}\n"
        code_temp = code_temp[:-1]

        file_name = f'execute{datetime.datetime.now().timestamp().__int__()}'

        with open(file_name + ".py", 'a') as execute_file:
            execute_file.write(f"async def main(ctx):\n"
                               f"{code_temp}")
            execute_file.close()
        try:
            exec(f"import asyncio\n"
                 f"import {file_name}\n"
                 f"task = {file_name}.main\n"
                 f"")
            await locals()["task"](ctx)
            await ctx.reply(
                f"Code ran with no issues."
            )
        except:
            await ctx.reply(
                traceback.format_exc()
            )

        os.remove(f"{file_name}.py")

    @commands.command(name="_sqlquery",
                      description="Run a SQL Query on the databse (Only for bot developers)")
    async def _sqlquery(self, ctx: commands.Context, *, query: str = ""):
        if ctx.author.id not in self.bot.full_perm_users:
            return
        db, cursor = functions.database(ctx.guild.id)

        cursor.execute(query)
        db.commit()

    @commands.command(name="_fetchdata",
                      description="Fetches some data from the database (Only for bot developers)")
    async def _fetchdata(self, ctx: commands.Context, *, query: str = ""):
        if ctx.author.id not in self.bot.full_perm_users:
            return
        db, cursor = functions.database(ctx.guild.id)

        data: Optional[list[tuple]] = cursor.execute(query).fetchall()

        if data is not None:
            await ctx.send(
                file=discord.File(
                    io.BytesIO(str('\n\n'.join(str(t) for t in data)).encode('utf-8')),
                    'data.txt'
                )
            )

    @commands.command(name="_testscoringmenu")
    async def _testscoringmenu(self, ctx: commands.Context, game_id: int = parameters.GAME_ID):
        if ctx.author.id not in self.bot.full_perm_users:
            return

        game = classes.Game.from_game_id(game_id, ctx.guild, ctx.bot)

        await ctx.send(
            embed=await game.game_scoring_embed(),
            view=views.ScoreGameView(game)
        )

    @commands.command(name="_fixstreak")
    async def _fixstreak(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)
        s = ""

        for player_tuple in cursor.execute("SELECT * FROM players").fetchall():
            player = classes.NewPlayer.from_tuple(player_tuple, ctx.guild)
            winstreak = 0
            peak_winstreak = 0
            losestreak = 0
            peak_losestreak = 0
            for game_id in player.games_ids:
                game = classes.Game.from_game_id(game_id, ctx.guild, ctx.bot)
                if game.status == "SCORED":
                    scored_game = classes.ScoredGame.from_game_id(game_id, ctx.guild, ctx.bot)
                    if player.player_id in scored_game.winner_team_ids:
                        winstreak += 1
                        losestreak = 0
                        if winstreak > peak_winstreak:
                            peak_winstreak = winstreak
                    else:
                        losestreak += 1
                        winstreak = 0
                        if losestreak > peak_losestreak:
                            peak_losestreak = losestreak

            player.winstreak = winstreak
            player.peak_winstreak = peak_winstreak
            player.losestreak = losestreak
            player.peak_losestreak = peak_losestreak
            s += f"{player.ign} {winstreak} {peak_winstreak} {losestreak} {peak_losestreak}\n"
        await ctx.send("done")

    @commands.command(name="_resetparty",
                      description="Resets parties (Only for bot developers)")
    async def _resetparty(self, ctx: commands.Context):
        if ctx.author.id not in self.bot.full_perm_users:
            return

        db, cursor = functions.database(ctx.guild.id)

        cursor.executescript("DELETE FROM parties;"
                             "DELETE FROM party_invites;"
                             "DELETE FROM party_ignore_lists;"
                             "DELETE FROM party_members;")
        db.commit()

    @commands.command(
        name="_resetwebhooks"
    )
    async def _resetwebhooks(self, ctx: commands.Context):
        if ctx.author.id not in self.bot.full_perm_users:
            return

        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("DELETE FROM webhooks")
        db.commit()

        for channel in await ctx.guild.fetch_channels():
            try:
                for webhook in await channel.webhooks():
                    await webhook.delete(reason="by {}".format(ctx.author.id))
                    await ctx.send(f'Deleted webhook named {webhook.name} in {webhook.channel.jump_url}')
                    await asyncio.sleep(1)
            except:
                pass

    @commands.command("_sync")
    @discordchecks.guild_command_check()
    async def sync(self, ctx: commands.Context, guilds: commands.Greedy[discord.Object],
                   spec: Optional[Literal["~", "*", "^"]] = None) -> None:
        if ctx.author.id not in ctx.bot.full_perm_users:
            return

        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    @commands.command("_restart")
    async def _restart(self, ctx: commands.Context):
        if ctx.author.id not in ctx.bot.full_perm_users:
            return

        ctx.bot.restart = 1
        await ctx.bot.close()

    @commands.command("_unvoid")
    async def _unvoid(self, ctx: commands.Context, game_ids: commands.Greedy[int]):
        if ctx.author.id not in ctx.bot.full_perm_users:
            return

        db, cursor = functions.database(ctx.guild.id)
        for game_id in game_ids:
            cursor.execute("UPDATE games SET status='SUBMITTED' WHERE game_id=?",
                           (game_id,))
        db.commit()
        db.close()

    async def kick_under_30d(self):
        try:
            await self.bot.wait_until_ready()
            now = datetime.datetime.now().timestamp()

            for guild in self.bot.guilds:
                logs_channel = await functions.fetch_channel("LOGS", guild)
                kicked = []
                for member in guild.members:
                    if now - datetime.timedelta(days=30).total_seconds() < member.created_at.timestamp():
                        await guild.kick(member, reason="Account less than 30d old")
                        kicked.append(f"({member.mention}|{member.name}) Account created at "
                                      f"<t:{member.created_at.timestamp().__int__()}:R>")

                if kicked:
                    await logs_channel.send(
                        "Kicked\n" + ("\n".join(kicked))
                    )
        except:
            exc_info = sys.exc_info()
            logger = logging.getLogger('discord')
            logger.error("error in kicking accs under 30d\n", exc_info=exc_info)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        logs_channel = await functions.fetch_channel("LOGS", member.guild)
        now = datetime.datetime.now().timestamp()

        if now - datetime.timedelta(days=30).total_seconds() < member.created_at.timestamp():
            await member.kick(reason="Account less than 30d old")
            await logs_channel.send(
                f"Kicked ({member.mention}|{member.name}) Account created at "
                f"<t:{member.created_at.timestamp().__int__()}:R>")

    async def cog_load(self) -> None:
        pass

    async def cog_unload(self) -> None:
        pass

    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        await functions.error_handler(ctx, error, traceback.format_exc())


async def setup(bot: commands.Bot):
    await bot.add_cog(DevOnlyCog(bot))
