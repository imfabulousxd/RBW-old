import re

import discord
from discord.ext.commands import Context

import classes
import dpyfuncs
import errors
from Functions import functions
from discord.ext import commands

MEMBER_ID_PATTERN = re.compile(r'([0-9]+)$')
MEMBER_MENTION_PATTERN = re.compile(r'<@!?([0-9]+)>$')


class PlayerConverter(commands.Converter[discord.Member]):

    async def convert(self, ctx: commands.Context, argument: str):
        return await functions.fetch_member(argument, ctx.guild)


class NewPlayerConverter(commands.Converter):

    async def convert(self, ctx: commands.Context, argument: str):
        player = None
        member_id = MEMBER_ID_PATTERN.match(argument)
        member_id = member_id or MEMBER_MENTION_PATTERN.match(argument)

        if member_id is not None:
            member_id = int(member_id.group(1))

        db, cursor = functions.database(ctx.guild.id)

        if member_id is None:
            member_id = cursor.execute("SELECT id FROM players WHERE ign LIKE ?",
                                       (argument, )).fetchone()
            if member_id is not None:
                member_id = member_id[0]
            else:
                try:
                    member_id = cursor.execute("SELECT id FROM players WHERE id=?",
                                               (int(argument), ))
                except ValueError:
                    ...

        member_id = member_id or discord.utils.get(ctx.guild.members, name=argument)

        if member_id is None:
            raise errors.MemberNotFound(argument)

        if isinstance(member_id, discord.Member):
            member_id = member_id.id

        player_tuple = cursor.execute("SELECT * FROM players WHERE id=?",
                                      (member_id, )).fetchone()
        if player_tuple is None:
            raise errors.MemberNotRegistered(member_id)

        return classes.NewPlayer.from_tuple(player_tuple, ctx.guild)


class MemberUserConverter(commands.Converter[discord.User]):

    async def convert(self, ctx: commands.Context, argument: str):
        try:
            member = await functions.fetch_member(argument, ctx.guild)
            return member
        except:
            user = await dpyfuncs.fetch_user(argument, ctx.bot)
            if user is None:
                raise errors.MemberNotFound(argument)
            else:
                return user


