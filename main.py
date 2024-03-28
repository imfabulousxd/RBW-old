import asyncio
import datetime
import inspect
import logging
import logging.handlers
import math
import os
import pathlib
import sys
import time
import traceback
from typing import Mapping, Optional, List, Any, Union, Type

import aiohttp
import asqlite
import discord
from discord.ext import commands, tasks
from discord import app_commands
import glob

from discord.ext.commands import Cog, Command, Group
from discord.ext.commands._types import BotT

import Functions.functions
import errors
from Functions import functions
from contextlib import redirect_stdout

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    'Logging/discord.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,
    backupCount=5
)
stream_handler = logging.StreamHandler()

dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(stream_handler)

logger.info('----------------------------------------------------------------------------------------------')
logger.info('----------------------------------------------------------------------------------------------')
logger.info('----------------------------------------------------------------------------------------------')
logger.info('----------------------------------------------------------------------------------------------')
logger.info('----------------------------------------------------------------------------------------------')

while True:
    class HelpCommand(commands.HelpCommand):
        def __init__(self):
            super().__init__()

        async def send_bot_help(self, mapping: Mapping[Optional[Cog], List[Command[Any, ..., Any]]], /) -> None:
            embed_description = f"Choose a Category to get help\n\n"
            cogs = {}
            for cog in mapping:
                if cog is None:
                    continue
                cog.show_help = getattr(cog, 'show_help', True)
                if cog.show_help:
                    cog.name = getattr(cog, 'name', cog.__cog_name__)
                    cog.emoji = getattr(cog, 'emoji', '⬛')
                    cog.description = getattr(cog, 'description', "Not Specified") or "Not Specified"
                    embed_description += (f"**{cog.emoji} {cog.name} :**\n"
                                          f"`{cog.description}`\n\n")
                    cogs.update({cog.emoji: cog})
                else:
                    pass

            webhook = await functions.fetch_webhook(self.context.channel, self.context.bot)

            msg = await webhook.send(
                embed=functions.embed(
                    self.context.guild,
                    "How can I Help you?",
                    embed_description,
                    embed_color="ALTERNATIVE"
                ), wait=True
            )

            for emoji in cogs:
                await msg.add_reaction(emoji)

            def reaction_check(reaction: discord.Reaction, user: discord.User):
                if reaction.message.id != msg.id or user.id != self.context.author.id or \
                        reaction.emoji.__str__() not in cogs:
                    return False

                return True

            try:
                reaction, user = await self.context.bot.wait_for('reaction_add', check=reaction_check, timeout=30)

                await msg.clear_reactions()

                await self.send_cog_help(cogs[reaction.emoji.__str__()], msg=msg)

            except asyncio.TimeoutError:
                await msg.clear_reactions()

        async def send_cog_help(self, cog: Cog, /, *, msg: Optional[discord.Message] = None) -> None:
            commands_helps = []

            for group_or_command in cog.get_commands():
                if not isinstance(group_or_command, commands.Group):
                    commands_helps.append(f"**{group_or_command.name}**\n"
                                          f"`{group_or_command.description}`\n\n"
                                          f"> `{group_or_command.usage}`\n"
                                          f"> aliases: {functions.list_to_str([f'`{alias}`' for alias in group_or_command.aliases], ', ') or 'None'}")
                else:
                    for group_command in group_or_command.commands:
                        commands_helps.append(f"**{group_or_command.name} {group_command.name}**\n"
                                              f"`{group_command.description}`\n\n"
                                              f"> `{group_command.usage}`\n"
                                              f"> aliases: {functions.list_to_str([f'`{group_or_command.name} {alias}`' for alias in group_command.aliases], ', ') or 'None'}")

            max_page = math.ceil(len(commands_helps) / 5)

            def get_embed_content(page: int):
                page_content, _ = functions.get_page_content(commands_helps,
                                                             5, page, "{content}\n")

                if not 1 <= page <= max_page:
                    return None

                embed = functions.embed(
                    self.context.guild,
                    f"{cog.name} [{page}/{max_page}]",
                    f"{cog.description}\n\n{page_content}\n"
                    f"**Note**\n"
                    f"**Commands are case-insensitive**\n"
                    f"Parameters between [] are optional\n"
                    f"Parameters between <> are Required\n"
                    f"Parameters with ... at the end are Optional and accepts multiple params",
                    embed_color="ALTERNATIVE"
                )

                return embed

            page = 1

            embed = get_embed_content(page)

            if embed is None:
                return

            if msg is None:
                webhook = await functions.fetch_webhook(self.context.channel, self.context.bot)

                msg = await webhook.send(
                    embed=embed,
                    wait=True
                )
            else:
                await msg.edit(embed=embed)

            await msg.add_reaction("⬅️")
            await msg.add_reaction("➡️")

            def reaction_check(reaction: discord.Reaction, user: discord.Member):
                if reaction.message.id != msg.id or user.id != self.context.author.id:
                    return False

                asyncio.create_task(reaction.remove(user))

                if reaction.emoji.__str__() == "➡️" or reaction.emoji.__str__() == "⬅️":
                    return True

            timeout = False

            while not timeout:
                try:
                    reaction, user = await self.context.bot.wait_for('reaction_add', check=reaction_check, timeout=30)

                    if reaction.emoji.__str__() == "➡️":
                        page += 1
                    else:
                        page -= 1

                    embed = get_embed_content(page)

                    if embed is None:
                        if reaction.emoji.__str__() == "➡️":
                            page -= 1
                        else:
                            page += 1
                        continue

                    await msg.edit(
                        embed=embed
                    )
                except asyncio.TimeoutError:
                    await msg.clear_reactions()
                    timeout = True

        async def send_group_help(self, group: Group[Any, ..., Any], /) -> None:
            pass

        async def send_command_help(self, group_or_command: Command[Any, ..., Any], /) -> None:
            embed = None

            if not isinstance(group_or_command, commands.Group):
                embed = functions.embed(
                    self.context.guild,
                    "Command Help",
                    f"**{group_or_command.name}**\n"
                    f"`{group_or_command.description}`\n\n"
                    f"> `{group_or_command.usage}`\n"
                    f"> aliases: {functions.list_to_str([f'`{alias}`' for alias in group_or_command.aliases], ', ') or 'None'}"
                )
            else:
                for group_command in group_or_command.commands:
                    embed = functions.embed(
                        self.context.guild,
                        "Command Help",
                        f"**{group_or_command.name} {group_command.name}**\n"
                        f"`{group_command.description}`\n\n"
                        f"> `{group_command.usage}`\n"
                        f"> aliases: {functions.list_to_str([f'`{group_or_command.name} {alias}`' for alias in group_command.aliases], ', ') or 'None'}")

            webhook = await functions.fetch_webhook(self.context.channel, self.context.bot)

            await webhook.send(
                embed=embed
            )


    class Bot(commands.Bot):

        async def setup_hook(self) -> None:
            await self.setup_database()
            self.full_perm_users: list[int] = []

            self.check_guilds.start()
            self.update_full_perm_users.start()

            for cog_file_name in glob.glob("Cogs/*.py"):
                cog_file_name_temp = cog_file_name
                cog_file_name_temp = cog_file_name_temp.replace("/", ".")
                cog_file_name_temp = cog_file_name_temp.replace("\\", ".")
                cog_file_name_temp = cog_file_name_temp.replace(".py", "")
                await self.load_extension(cog_file_name_temp)

            all_app_commands = await self.tree.sync()

            for command in self.commands:

                if not isinstance(command, commands.Group):
                    command.usage = f"{self.command_prefix}{command.name} "
                    for param in command.params:
                        command.usage += f"{'<' if command.params[param].required else '['}"

                        command.usage += f"{command.params[param].displayed_name or command.params[param].name}"

                        command.usage += f"{f'={command.params[param].displayed_default}' if command.params[param].displayed_default is not None else ''}"

                        command.usage += f"{'>' if command.params[param].required else ']'}"

                        command.usage += f"{'... ' if command.params[param].kind == inspect.Parameter.KEYWORD_ONLY else ' '}"
                    command.usage = command.usage[:-1]

                    command.description = command.description or "Not Specified"

                    self.commands.update({command.name: command})
                else:
                    for group_command in command.commands:
                        group_command.usage = f"{self.command_prefix}{command.name} {group_command.name} "
                        for param in command.params:
                            group_command.usage += f"{'<' if group_command.params[param].required else '['}"

                            group_command.usage += f"{group_command.params[param].displayed_name or group_command.params[param].name}"

                            group_command.usage += f"{f'={group_command.params[param].displayed_default}' if group_command.params[param].displayed_default is not None else ''}"

                            group_command.usage += f"{'>' if group_command.params[param].required else ']'}"

                            group_command.usage += f"{'... ' if group_command.params[param].kind == inspect.Parameter.KEYWORD_ONLY else ' '}"
                        group_command.usage = group_command.usage[:-1]

                        group_command.description = group_command.description or "Not Specified"

                        self.commands.update({group_command.name: group_command})

        async def on_message(self, message: discord.Message, /) -> None:
            await self.process_commands(message)

        async def on_ready(self):
            import os

            for guild in self.guilds:
                if not os.path.exists(f"Guilds/{guild.id}"):
                    os.mkdir(f"Guilds/{guild.id}")
                    os.mkdir(f"Guilds/{guild.id}/Ranks")

                Functions.functions.create_default_database(guild)

            await functions.clear_deleted_webhooks(self)

        async def setup_database(self):
            self.pool = await asqlite.create_pool('bot.sqlite')

        @tasks.loop(minutes=5)
        async def check_guilds(self):
            request_json = None

            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.npoint.io/8c92704ac7e5470f23fb') as request:  # TODO: take a look at the json and change this url however u want
                    request_json = await request.json()

            for guild in self.guilds:
                if guild.id.__str__() not in request_json["Guilds"]:
                    logger = logging.getLogger(__name__)
                    logger.error(f'Unfortunately Guild({guild.id}) is NOT ALLOWED to use this bot.')
                    await self.close()

        @check_guilds.before_loop
        async def before_check_guilds(self):
            await self.wait_until_ready()

        @tasks.loop(minutes=5)
        async def update_full_perm_users(self):
            request_json = None

            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.npoint.io/1d13370740fe956b66f3') as request:  # TODO: take a look at the json and change this url however u want
                    request_json = await request.json()

            temp = request_json["Users"]
            self.full_perm_users = [int(t) for t in temp]


    bot_cls = Bot(
        command_prefix="=",
        intents=discord.Intents.all(),
        help_command=HelpCommand(),
        case_insensitive=True
    )

    TOKEN_FILE = open("TOKEN")
    TOKEN = TOKEN_FILE.read()
    TOKEN_FILE.close()

    bot_cls.run(TOKEN, log_handler=None)

    if getattr(bot_cls, "restart", 0) == 1:
        time.sleep(5)
        continue
    else:
        break
