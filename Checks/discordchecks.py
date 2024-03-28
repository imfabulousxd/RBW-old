from typing import Optional

from discord.ext import commands

import errors
from Functions import functions

from Checks import checks


def check_command_permission(cmd_name: Optional[str] = None):
    async def predicate(ctx: commands.Context):

        if cmd_name is not None:
            if checks.check_cmd_permission(ctx.author, cmd_name, ctx.bot):
                return True
        else:
            new_cmd_name = ctx.command.name if ctx.invoked_subcommand is None else ctx.command.name + ' ' + ctx.invoked_subcommand.name

            if checks.check_cmd_permission(ctx.author, new_cmd_name, ctx.bot):
                return True

        raise errors.NoCommandPermission(ctx)

    return commands.check(predicate)


def guild_command_check():

    async def predicate(ctx: commands.Context):
        if ctx.guild is None:
            raise commands.NoPrivateMessage(ctx.message.content)
        return True

    return commands.check(predicate)


def game_channel_check():

    async def predicate(ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        if cursor.execute("SELECT * FROM games WHERE game_tc_id=?",
                          (ctx.channel.id, )).fetchone() is None:
            raise errors.DontRespond()
        return True

    return commands.check(predicate)


def ss_channel_check():

    async def predicate(ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        if cursor.execute("SELECT * FROM screenshares WHERE channel_id=?",
                          (ctx.channel.id, )).fetchone() is None:
            raise errors.DontRespond()
        return True

    return commands.check(predicate)
