import asyncio
import functools
import json
import logging
import sys
import traceback

import aiohttp
from discord.ext import commands, tasks
import discord
from discord.ext.commands import Context
from discord.ext.commands._types import BotT

import errors
import parameters
from Functions import functions
from Cooldowns import usercooldown
from Checks import discordchecks, checks

logger = logging.getLogger(__name__)


class PlayerManagement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "PlayerManagement"
        self.emoji = "📁"
        self.description = "Player management Commands."

    @commands.command(name="register", aliases=["reg", "rename"], description="Registers/Renames Player")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def register(self, ctx: commands.Context,
                       ign: str = parameters.IGN):

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        first_time = functions.register(ctx.author, ign)

        if first_time is True:
            await webhook.send(
                embed=functions.embed(
                    ctx.guild,
                    "Registration System",
                    "You are now registered!\n"
                    f"{ctx.author.mention}, Welcome to {ctx.guild.name}.",
                    embed_footer_text=True,
                    embed_footer_icon_url=True,
                    embed_timestamp=True,
                    embed_thumbnail_url=ctx.author.display_avatar.url
                )
            )
        else:
            await webhook.send(
                embed=functions.embed(
                    ctx.guild,
                    "Registration System",
                    f"Renamed {ctx.author.mention} to `{ign}`"
                )
            )

        await functions.fix(ctx.author, full_check=True)

    @commands.command(name="nick", description="Change Player's nickname")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def nick(self, ctx: commands.Context, *,
                   nick: str = parameters.parameter(displayed_name="Nickname")):
        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("DELETE FROM nicks WHERE member_id=?",
                       (ctx.author.id,))
        db.commit()

        cursor.execute("INSERT INTO nicks VALUES (?, ?)",
                       (ctx.author.id, nick))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                embed_description="Nickname changed to `{}`".format(nick),
                embed_footer_text="Invoked by {}".format(ctx.author.name)
            )
        )

        await functions.fix(ctx.author, nick_check=True)

    @commands.command(name="removenick", aliases=["rn", "unnick"], description="Removes player's nickname")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def removenick(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("DELETE FROM nicks WHERE member_id=?",
                       (ctx.author.id,))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                embed_description="Removed Nickname",
                embed_footer_text="Invoked by {}".format(ctx.author.name)
            )
        )

        await functions.fix(ctx.author, nick_check=True)

    @commands.command(name="refresh", aliases=["refreshme", "rme"], description="Refreshes Your roles, nickname")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_1P5_COOLDOWN
    async def refresh(self, ctx: commands.Context):
        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await functions.fix(ctx.author, full_check=True)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                embed_description="Refreshed",
                embed_color="ALTERNATIVE"
            )
        )

    @commands.command(name="toggleprefix", description="Toggles elo prefix [elo] next to the user's name")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_1P5_COOLDOWN
    async def toggleprefix(self, ctx: commands.Context, ):
        db, cursor = functions.database(ctx.guild.id)

        toggle_prefix = "ON"

        if cursor.execute("SELECT * FROM toggleprefixusers WHERE member_id=?",
                          (ctx.author.id,)).fetchone() is None:
            toggle_prefix = "OFF"
            cursor.execute("INSERT INTO toggleprefixusers VALUES (?)",
                           (ctx.author.id,))
            db.commit()
        else:
            cursor.execute("DELETE FROM toggleprefixusers WHERE member_id=?",
                           (ctx.author.id,))
            db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "",
                f"ELO prefix is now `{toggle_prefix}`",
                embed_color=0
            )
        )

        await functions.fix(ctx.author, nick_check=True)

    @tasks.loop(minutes=2)
    async def update_igns_json(self):
        ...  # idk

    @update_igns_json.before_loop
    async def before_update_igns_json(self):
        await self.bot.wait_until_ready()

    async def cog_load(self) -> None:
        self.update_igns_json.start()

    async def cog_unload(self) -> None:
        pass

    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        await functions.error_handler(ctx, error, traceback.format_exc())


async def setup(bot: commands.Bot):
    await bot.add_cog(PlayerManagement(bot))
