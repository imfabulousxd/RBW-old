import asyncio
import datetime
import functools
import glob
import io
import math
import sqlite3
import traceback
import typing
import zoneinfo

import discord
from discord import File, Embed, AllowedMentions, WebhookMessage
from discord.abc import Snowflake
from discord.ext import commands
import aiohttp
from discord.ui import View
from discord.webhook.async_ import MISSING

import classes
import dpyfuncs
from Checks import checks

import errors
from typing import Optional, Any, AnyStr, Union, Literal, NoReturn, Never, Iterable, Sequence

import config
import re
from contextlib import AsyncContextDecorator


def list_to_str(
        original_list: typing.Iterable,
        split_by: str
):
    returned_str = ""

    for item in original_list:
        returned_str += f"{item}{split_by}"

    if len(split_by) != 0:
        returned_str = returned_str[:-(len(split_by))]

    return returned_str


def database(guild_id: int) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    db = sqlite3.connect(f"Guilds/{guild_id}/{guild_id}.sqlite", isolation_level=None)
    cursor = db.cursor()

    return db, cursor


# noinspection SpellCheckingInspection
def create_default_database(guild: discord.Guild) -> None:
    db, cursor = database(guild.id)

    try:
        cursor.execute("CREATE TABLE commands_roles (command_name TEXT, command_roles TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "CREATE TABLE screenshares (channel_id INT, target INT, requested_by INT, screensharer INT, reason TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE picking (game_id INT, team_turn INT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE toggleprefixusers (member_id INT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE webhooks (webhook_name TEXT, webhook_channel_id INT, webhook_url TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE info (info_name TEXT, info_value)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE temp_mvps (game_id INT, mvps TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE roles (role_name TEXT, role_id INT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE channels (channel_name TEXT, channel_id INT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE voided_games (game_id INT, voided_by INT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE queues "
                       "(queue_vc_id INT, "
                       "queue_player_count INT, "
                       "queue_automatic INT, "
                       "queue_ranked INT, "
                       "queue_min_elo INT, "
                       "queue_max_elo INT, "
                       "queue_extras TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE queues_players (queue_vc_id INT, players_ids TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE strikes (member_id INT, strikes INT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "CREATE TABLE games(game_id INT, team1_players_ids TEXT, team2_players_ids TEXT, remaining_players_ids TEXT, queue_vc_id INT, game_tc_id INT, game_vc_id INT, team1_vc_id INT, team2_vc_id INT, automatic INT, ranked INT, status TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE game_count (game_count INT)")
        db.commit()
        cursor.execute("INSERT INTO game_count VALUES (0)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE game_screenshots (game_id INT, screenshot_url TEXT, submitted_by INT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE nicks (member_id INT, nick TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE bans (member_id INT, banned_by INT, unbanned_at INT, state TEXT, reason TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE mutes (member_id INT, muted_by INT, unmuted_at INT, state TEXT, reason TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE maps (map TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    cursor.execute("CREATE TABLE IF NOT EXISTS parties (leader_id INT, members_ids TEXT, created INT, last_queued INT, autowarp INT, party_limit INT)")
    db.commit()

    cursor.execute("CREATE TABLE IF NOT EXISTS party_ignore_lists (member_id INT, ignoredlist TEXT)")
    db.commit()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS party_invites (leader_id INT, invited_member_id INT, expires_at INT)")
    db.commit()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS party_members (leader_id INT, member_id INT)")
    db.commit()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS party_games (player_id INT, games_count INT)")
    db.commit()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS blacklisted_igns (ign TEXT)")
    db.commit()

    try:
        cursor.execute(
            "CREATE TABLE voicemutes (member_id INT, voicemuted_by INT, voiceunmuted_at INT, state TEXT, reason TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE closing_channels (channel_id INT, close_timestamp INT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE cardusers (member_id INT, card_name TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE weekly ("
                       "id INT,"
                       "elo INT,"
                       "wins INT,"
                       "losses INT,"
                       "mvps INT,"
                       "games_played INT"
                       ")")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE daily ("
                       "id INT,"
                       "elo INT,"
                       "wins INT,"
                       "losses INT,"
                       "mvps INT,"
                       "games_played INT"
                       ")")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE cards ("
                       "card_name TEXT,"
                       "card_file_name TEXT,"
                       "discord_name TEXT,"
                       "ign TEXT,"
                       "elo TEXT,"
                       "daily_elo,"
                       "wins TEXT,"
                       "losses TEXT,"
                       "streak TEXT,"
                       "mvps TEXT,"
                       "games_played TEXT,"
                       "wlr TEXT,"
                       "winrate TEXT,"
                       "games TEXT,"
                       "rank TEXT,"
                       "rank_icon TEXT,"
                       "skin TEXT"
                       ")")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE scored_games ("
                       "game_id INT,"
                       "winner INT,"
                       "team1 TEXT,"
                       "team2 TEXT,"
                       "mvps TEXT,"
                       "scored_by INT"
                       ")")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE ranks (role_id INT, "
                       "starting_elo INT, "
                       "ending_elo INT, "
                       "win_elo INT, "
                       "lose_elo INT, "
                       "mvp_elo INT, "
                       "role_color INT)")
        db.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("CREATE TABLE players "
                       "(id INT, "
                       "ign TEXT, "
                       "elo INT, "
                       "peak_elo INT, "
                       "wins INT, "
                       "winstreak INT, "
                       "peak_winstreak INT, "
                       "losses INT, "
                       "losestreak INT, "
                       "peak_losestreak INT, "
                       "mvps INT, "
                       "games_played INT, "
                       "games_ids TEXT)")
        db.commit()
    except sqlite3.OperationalError:
        pass


async def fetch_webhook(channel: discord.TextChannel,
                        client: discord.Client,
                        *, webhook_name: Optional[str] = None) -> discord.Webhook:

    guild = channel.guild

    db, cursor = database(guild.id)

    if webhook_name is None:
        webhook_name = get_info_value("WEBHOOKNAME", guild)

    webhook_url_tuple = cursor.execute("SELECT webhook_url FROM webhooks WHERE webhook_name=? AND webhook_channel_id=?",
                                       (webhook_name, getattr(channel, 'parent', channel).id)).fetchone()
    webhook = None

    if webhook_url_tuple is None:
        webhook_avatar_url = get_info_value("WEBHOOKIMAGEURL", guild)
        webhook_avatar_bytes, _ = await get_image_bytes_from_url(webhook_avatar_url)

        msg = await channel.send(
            embed=embed(
                channel.guild,
                "",
                "Loading...",
                embed_color=0
            )
        )

        webhook = await (getattr(channel, 'parent', None) or channel).create_webhook(name=webhook_name,
                                               avatar=webhook_avatar_bytes)

        cursor.execute("INSERT INTO webhooks VALUES (?, ?, ?)",
                       (webhook.name, webhook.channel.id, webhook.url))
        db.commit()

        await msg.delete()
    else:
        webhook = discord.Webhook.from_url(url=webhook_url_tuple[0], client=client)

    if isinstance(channel, discord.Thread):
        class KindaWebhook(discord.Webhook):
            async def send(self, *args, **kwargs):
                kwargs.update({'thread': channel})
                return await super().send(*args, **kwargs)

        webhook = KindaWebhook.from_url(webhook.url, client=client)

    return webhook


def get_info_value(
        info_name: config.ALL_INFO_NAMES_LITERAL,
        guild: Union[discord.Guild, int]
) -> typing.Any:
    db, cursor = database(guild.id if isinstance(guild, discord.Guild) else guild)

    if info_name == "WEBHOOKIMAGEURL":
        webhook_image_url_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                                 ('WEBHOOKIMAGEURL',)).fetchone()
        if webhook_image_url_tuple is None:
            return guild.icon.url
        else:
            return webhook_image_url_tuple[0]
    elif info_name == "WEBHOOKNAME":
        webhook_name_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                            ('WEBHOOKNAME',)).fetchone()

        if webhook_name_tuple is None:
            return guild.name
        else:
            return webhook_name_tuple[0]
    elif info_name == "EMBEDCOLOR":
        embed_color_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                           ('EMBEDCOLOR',)).fetchone()
        if embed_color_tuple is None:
            return 0xffffff
        else:
            return embed_color_tuple[0]
    elif info_name == "ALTERNATIVEEMBEDCOLOR":
        embed_color_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                           ('ALTERNATIVEEMBEDCOLOR',)).fetchone()
        if embed_color_tuple is None:
            embed_color_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                               ('EMBEDCOLOR',)).fetchone()
            if embed_color_tuple is None:
                return 0xffffff
            else:
                return embed_color_tuple[0]
        else:
            return embed_color_tuple[0]
    elif info_name == "EMBEDFOOTERTEXT":
        embed_footer_text_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                                 ('EMBEDFOOTERTEXT',)).fetchone()
        if embed_footer_text_tuple is None:
            return guild.name
        else:
            return embed_footer_text_tuple[0]
    elif info_name == "EMBEDFOOTERICONURL":
        embed_footer_icon_url_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                                     ('EMBEDFOOTERICONURL',)).fetchone()
        if embed_footer_icon_url_tuple is None:
            return guild.icon.url
        else:
            return embed_footer_icon_url_tuple[0]
    elif info_name == "EMBEDIMAGEURL":
        embed_image_url_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                               ("EMBEDIMAGEURL",)).fetchone()
        if embed_image_url_tuple is None:
            return guild.icon.url
        else:
            return embed_image_url_tuple[0]
    elif info_name == "EMBEDTHUMBNAILURL":
        embed_thumbnail_url_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                                   ("EMBEDTHUMBNAILURL",)).fetchone()
        if embed_thumbnail_url_tuple is None:
            return guild.icon.url
        else:
            return embed_thumbnail_url_tuple[0]
    elif info_name == "EMBEDERRORCOLOR":
        embed_error_color_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                                 ("EMBEDERRORCOLOR",)).fetchone()
        if embed_error_color_tuple is None:
            return config.ERROR_COLOR
        else:
            return embed_error_color_tuple[0]
    elif info_name == "CHANNELNAMEPREFIX":
        channel_name_prefix_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                                   ("CHANNELNAMEPREFIX",)).fetchone()
        if channel_name_prefix_tuple is None:
            return ""
        else:
            return channel_name_prefix_tuple[0]
    elif info_name == "DEFAULTVCREGION":
        default_vc_region_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                                 ("DEFAULTVCREGION",)).fetchone()
        if default_vc_region_tuple is None:
            return "russia"
        else:
            return default_vc_region_tuple[0]
    elif info_name == "GAMESTARTEDEMBEDTITLE":
        game_started_embed_title_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                                        ("GAMESTARTEDEMBEDTITLE",)).fetchone()
        if game_started_embed_title_tuple is None:
            return "Game#{game_id}"
        else:
            return game_started_embed_title_tuple[0]
    elif info_name == "GAMESTARTEDEMBEDDESCRIPTION":
        game_started_embed_description_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                                              ("GAMESTARTEDEMBEDDESCRIPTION",)).fetchone()
        if game_started_embed_description_tuple is None:
            return "Game#{game_id} has been started."
        else:
            return game_started_embed_description_tuple[0]
    elif info_name == "DEFAULTCARDNAME":
        default_card_name_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                                 ("DEFAULTCARDNAME",)).fetchone()

        if default_card_name_tuple is None:
            return "card0"
        else:
            return default_card_name_tuple[0]
    elif info_name == "WEEKLYLBRESET":

        now = datetime.datetime.now()
        weekly_reset_at = datetime.datetime(now.year, now.month, now.day, 0, 0)
        weekly_reset_at += datetime.timedelta(days=5 - weekly_reset_at.weekday())

        if now > weekly_reset_at:
            weekly_reset_at += datetime.timedelta(weeks=1)

        return weekly_reset_at
    elif info_name == "DAILYLBRESET":

        now = datetime.datetime.now()
        daily_reset_at = datetime.datetime(now.year, now.month, now.day, 0, 0)

        if now > daily_reset_at:
            daily_reset_at += datetime.timedelta(days=1)

        return daily_reset_at
    elif info_name == "RULES":
        rules_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                     ("RULES",)).fetchone()
        if rules_tuple is None:
            return "No Rules"
        else:
            return rules_tuple[0]
    elif info_name in ["2MEMBERPARTYLIMITROLESIDS", "3MEMBERPARTYLIMITROLESIDS", "4MEMBERPARTYLIMITROLESIDS"]:
        party_limit_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                           (info_name, )).fetchone()
        if party_limit_tuple is None:
            return []
        else:
            return [int(t) for t in party_limit_tuple[0].split(',')] if party_limit_tuple[0] != '' else []
    elif info_name == "PERMENANTPARTYROLESIDS":
        roles_ids_tuple = cursor.execute("SELECT info_value FROM info WHERE info_name=?",
                                     ("PERMENANTPARTYROLESIDS",)).fetchone()
        if roles_ids_tuple is None:
            return []
        else:
            return [int(t) for t in roles_ids_tuple[0].split(',')]


async def get_image_bytes_from_url(url: str) -> tuple[bytes, str]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            file_type = response.content_type.split("/")[0]

            if file_type.lower() != "image":
                raise errors.CommandsError(f"URL({url}) is not of `image` type!")

            image_bytes = await response.read()

            return image_bytes, response.content_type.split("/")[1]


def fetch_role(role_data: Union[str, int, config.ROLES_NAMES_LITERAL], guild: discord.Guild) -> discord.Role:
    role_id = 0

    role = dpyfuncs.fetch_role(role_data, guild)

    if role is None:
        db, cursor = database(guild.id)

        role_id_tuple = cursor.execute("SELECT role_id FROM roles WHERE role_name LIKE ?",
                                       (role_data,)).fetchone()

        if role_id_tuple is None:
            raise errors.RoleNotFoundError(role_data)

        role_id = role_id_tuple[0]

        role = dpyfuncs.fetch_role(role_id, guild)

        if role is None:
            raise errors.RoleNotFoundError(role_data)

    if role is None:
        discord.utils.find(lambda r: role_data.__str__().lower() in r.name, guild.roles)

    return role


async def fetch_channel(channel_data: Union[str, int, config.CHANNELS_NAMES_LITERAL],
                        guild: discord.Guild) -> Union[
    discord.VoiceChannel,
    discord.TextChannel,
    discord.CategoryChannel,
    discord.ForumChannel,
    discord.StageChannel,
    discord.Thread,
    discord.abc.GuildChannel
]:
    channel = await dpyfuncs.fetch_channel(channel_data, guild)

    if channel is None:
        db, cursor = database(guild.id)
        channel_id_tuple = cursor.execute("SELECT channel_id FROM channels WHERE channel_name LIKE ?",
                                          (channel_data,)).fetchone()

        if channel_id_tuple is None:
            raise errors.ChannelNotFoundError(channel_data)

        channel_id = channel_id_tuple[0]

        channel = await dpyfuncs.fetch_channel(channel_id, guild)

        if channel is None:
            raise errors.ChannelNotFoundError(channel_data)

    return channel


async def fetch_member(member_data: Union[str, int],
                       guild: discord.Guild) -> Union[discord.Member, Never]:
    member = await dpyfuncs.fetch_member(member_data, guild)

    if member is None:
        db, cursor = database(guild.id)

        member_id_tuple = cursor.execute("SELECT id FROM players WHERE ign LIKE ?",
                                         (member_data,)).fetchone()

        if member_id_tuple is None:
            raise errors.MemberNotFound(member_data)

        member_id = member_id_tuple[0]

        member = await dpyfuncs.fetch_member(member_id, guild)

        if member is None:
            raise errors.MemberNotFound(member_data)

    return member


def embed(guild: discord.Guild, /,
          embed_title: Optional[str] = None,
          embed_description: Optional[str] = None,
          embed_author_name: Optional[str] = None,
          embed_author_icon_url: Optional[str] = None,
          embed_author_url: Optional[str] = None,
          embed_color: Optional[Union[int, bool, Literal["MAIN", "ALTERNATIVE", "ERROR"]]] = None,
          embed_fields: list[list[str or str or bool]] = [],
          embed_footer_text: Optional[Union[str, bool]] = None,
          embed_footer_icon_url: Optional[Union[str, bool]] = None,
          embed_image_url: Optional[Union[str, bool]] = None,
          embed_thumbnail_url: Optional[Union[str, bool]] = None,
          embed_timestamp: Optional[Union[datetime.datetime, bool]] = None) -> discord.Embed or NoReturn:
    returned_embed = discord.Embed(
        title=embed_title,
        description=embed_description
    )

    # Embed Author
    if embed_author_name is not None:
        returned_embed.set_author(name=embed_author_name,
                                  url=embed_author_url,
                                  icon_url=embed_author_icon_url)

    # Embed color
    if embed_color is None:
        returned_embed.colour = get_info_value("EMBEDCOLOR", guild)
    elif embed_color is True:
        returned_embed.colour = get_info_value("EMBEDCOLOR", guild)
    elif embed_color == "MAIN":
        returned_embed.colour = get_info_value("EMBEDCOLOR", guild)
    elif embed_color == "ALTERNATIVE":
        returned_embed.colour = get_info_value("ALTERNATIVEEMBEDCOLOR", guild)
    elif embed_color == "ERROR":
        returned_embed.colour = get_info_value("EMBEDERRORCOLOR", guild)

    # Embed fields
    for embed_field in embed_fields:
        returned_embed.add_field(name=embed_field[0],
                                 value=embed_field[1],
                                 inline=embed_field[2])

    # Embed footer
    if embed_footer_text is True:
        embed_footer_text = get_info_value("EMBEDFOOTERTEXT", guild)

    if embed_footer_icon_url is True:
        embed_footer_icon_url = get_info_value("EMBEDFOOTERICONURL", guild)

    returned_embed.set_footer(text=embed_footer_text,
                              icon_url=embed_footer_icon_url)

    # Embed image
    if embed_image_url is True:
        embed_image_url = get_info_value("EMBEDIMAGEURL", guild)

    returned_embed.set_image(url=embed_image_url)

    # Embed thumbnail
    if embed_thumbnail_url is True:
        embed_thumbnail_url = get_info_value("EMBEDTHUMBNAILURL", guild)

    returned_embed.set_thumbnail(url=embed_thumbnail_url)

    # Embed timestamp
    if embed_timestamp is True:
        embed_timestamp = datetime.datetime.now()

    returned_embed.timestamp = embed_timestamp

    return returned_embed


def add_command_role(
        command_name_or_command_aliase: str,
        role: discord.Role,
        bot: commands.Bot
) -> str:
    all_commands = {}
    for command in bot.commands:
        if not isinstance(command, commands.Group):
            all_commands.update({command.name: command.name})
            for aliase in command.aliases:
                all_commands.update({aliase: command.name})
        else:
            for group_cmd in command.commands:
                all_commands.update({command.name + ' ' + group_cmd.name: command.name + ' ' + group_cmd.name})
                for aliase in group_cmd.aliases:
                    all_commands.update({command.name + ' ' + aliase: command.name + ' ' + group_cmd.name})

    for app_command in bot.tree.get_commands():
        all_commands.update({app_command.name: app_command.name})

    if command_name_or_command_aliase.lower() in all_commands:
        command_name_or_command_aliase = all_commands[command_name_or_command_aliase.lower()]
    else:
        raise errors.ModerationError(f"Command({command_name_or_command_aliase.lower()}) doesn't exist.")

    guild = role.guild
    db, cursor = database(guild.id)

    command_roles_tuple: tuple[str] or None = (
        cursor.execute("SELECT command_roles FROM commands_roles WHERE command_name LIKE ?",
                       (command_name_or_command_aliase,)).fetchone())

    if command_roles_tuple is None:
        cursor.execute("INSERT INTO commands_roles VALUES (?, ?)",
                       (command_name_or_command_aliase.lower(), role.id.__str__()))
        db.commit()
        return command_name_or_command_aliase

    command_roles = command_roles_tuple[0].split(",") if command_roles_tuple[0] != '' else []

    if role.id.__str__() in command_roles:
        raise errors.ModerationError(
            f"Role({role.mention}) already has access to the command({command_name_or_command_aliase.lower()}).")

    command_roles.append(role.id.__str__())

    command_roles_list = []

    for role_id_str in command_roles:
        c_role = fetch_role(role_id_str, guild)
        command_roles_list.append(c_role)

    command_roles_list.sort(reverse=True, key=lambda t: t.position)

    command_roles_str = ",".join([t.id.__str__() for t in command_roles_list])

    cursor.execute("UPDATE commands_roles SET command_roles=? WHERE command_name LIKE ?",
                   (command_roles_str, command_name_or_command_aliase))
    db.commit()

    return command_name_or_command_aliase


def remove_command_role(
        command_name_or_command_aliase: str,
        role: discord.Role,
        bot: commands.Bot
) -> str:
    all_commands = {}
    for command in bot.commands:
        if not isinstance(command, commands.Group):
            all_commands.update({command.name: command.name})
            for aliase in command.aliases:
                all_commands.update({aliase: command.name})
        else:
            for group_cmd in command.commands:
                all_commands.update({command.name + ' ' + group_cmd.name: command.name + ' ' + group_cmd.name})
                for aliase in group_cmd.aliases:
                    all_commands.update({command.name + ' ' + aliase: command.name + ' ' + group_cmd.name})

    for app_command in bot.tree.get_commands():
        all_commands.update({app_command.name: app_command.name})

    if command_name_or_command_aliase.lower() in all_commands:
        command_name_or_command_aliase = all_commands[command_name_or_command_aliase.lower()]
    else:
        raise errors.ModerationError(f"Command({command_name_or_command_aliase.lower()}) doesn't exist.")

    guild = role.guild
    db, cursor = database(guild.id)

    command_roles_tuple: tuple[str] or None = (
        cursor.execute("SELECT command_roles FROM commands_roles WHERE command_name LIKE ?",
                       (command_name_or_command_aliase,)).fetchone())

    command_roles = command_roles_tuple[0].split(",") if command_roles_tuple is not None else []

    if role.id.__str__() not in command_roles:
        raise errors.ModerationError(f"Role({role.mention}) doesn't have access "
                                     f"to the command({command_name_or_command_aliase.lower()}).")

    command_roles.remove(role.id.__str__())

    command_roles_str = list_to_str(command_roles, ",")

    cursor.execute("UPDATE commands_roles SET command_roles=? WHERE command_name LIKE ?",
                   (command_roles_str, command_name_or_command_aliase))
    db.commit()

    return command_name_or_command_aliase


def get_command_roles(
        command_name_or_command_aliase: str,
        guild: discord.Guild,
        bot: commands.Bot
) -> tuple[list[int], str]:
    all_commands = {}
    for command in bot.commands:
        if not isinstance(command, commands.Group):
            all_commands.update({command.name: command.name})
            for aliase in command.aliases:
                all_commands.update({aliase: command.name})
        else:
            for group_cmd in command.commands:
                all_commands.update({command.name + ' ' + group_cmd.name: command.name + ' ' + group_cmd.name})
                for aliase in group_cmd.aliases:
                    all_commands.update({command.name + ' ' + aliase: command.name + ' ' + group_cmd.name})

    for app_command in bot.tree.get_commands():
        all_commands.update({app_command.name: app_command.name})

    if command_name_or_command_aliase.lower() in all_commands:
        command_name = all_commands[command_name_or_command_aliase.lower()]
    else:
        raise errors.ModerationError(f"Command({command_name_or_command_aliase.lower()}) doesn't exist.")
    db, cursor = database(guild.id)

    command_roles_tuple = cursor.execute("SELECT command_roles FROM commands_roles WHERE command_name LIKE ?",
                                         (command_name,)).fetchone()

    if command_roles_tuple is None:
        command_roles_list_int = []
    else:
        command_roles_str = command_roles_tuple[0]
        command_roles_list_int = [int(command_role_id_str) for command_role_id_str in
                                  command_roles_str.split(",")] if command_roles_str != "" else []

    return command_roles_list_int, command_name


async def error_handler(ctx: commands.Context,
                        exception: Exception, /,
                        tb: Optional[str] = None, *,
                        game_channel: bool = False) -> None:
    # Guild Errors
    if ctx.guild is not None:

        # No response errors
        if isinstance(exception, errors.DontRespond):
            return None

        if game_channel is False:
            webhook = await fetch_webhook(ctx.channel, ctx.bot)
        else:
            game = classes.Game.from_game_tc(ctx.channel, ctx.bot)
            webhook = await game.fetch_webhook()
        if isinstance(exception, errors.DefaultError):
            await webhook.send(
                embed=embed(
                    ctx.guild,
                    exception.embed_title,
                    exception.embed_description,
                    embed_color="ERROR"
                )
            )
        elif isinstance(exception, commands.BadLiteralArgument):
            await webhook.send(
                embed=embed(
                    ctx.guild,
                    "Commands System",
                    f"Parameter({exception.param.displayed_name}) can only be one of these: ```py\n"
                    f"{', '.join([str(l) for l in exception.literals])}```\n"
                    f"**Help:**\n"
                    f"> `{ctx.command.usage}`",
                    embed_color="ERROR",
                    embed_footer_text=True,
                    embed_footer_icon_url=True
                )
            )
        elif isinstance(exception, commands.CommandOnCooldown):
            await webhook.send(
                embed=embed(
                    ctx.guild,
                    "Commands System",
                    exception.__str__(),
                    embed_color="ERROR",
                    embed_footer_text=True,
                    embed_footer_icon_url=True
                )
            )
        elif isinstance(exception, commands.MissingRequiredArgument):
            await webhook.send(
                embed=embed(
                    ctx.guild,
                    "Commands System",
                    f"Hey {ctx.author.mention},\n"
                    f"You missed a Parameter({exception.param.displayed_name}) which is required.\n"
                    f"**Help:**\n"
                    f"> `{ctx.command.usage}`",
                    embed_color="ERROR",
                    embed_footer_text=True,
                    embed_footer_icon_url=True
                )
            )
        elif isinstance(exception, commands.MissingRequiredAttachment):
            await webhook.send(
                embed=embed(
                    ctx.guild,
                    "Commands System",
                    f"Hey {ctx.author.mention},\n"
                    f"You have to send {exception.param.displayed_name}.",
                    embed_color="ERROR",
                    embed_footer_text=True,
                    embed_footer_icon_url=True
                )
            )
        else:
            await webhook.send(
                embed=embed(
                    ctx.guild,
                    "Commands System",
                    "Something unexpected happened.",
                    embed_color="ERROR",
                    embed_footer_text=True,
                    embed_footer_icon_url=True
                )
            )

            dev = await ctx.bot.fetch_user(config.DEV_ID)

            unexpected_error_embed = discord.Embed(
                description=f"**Guild({ctx.guild.name} | {ctx.guild.id})**\n\n"
                            f"**Message Content:** {fr'{ctx.message.content}'}\n"
                            f"**Message:** {ctx.message.jump_url}\n\n"
                            f"**Cog:** {ctx.command.cog_name}\n\n"
                            f"**Command:** `{ctx.command.name}`\n"
                            f"**Command ARGs:** ```py\n"
                            f"{ctx.args}```\n"
                            f"**Command KWARGS:** ```py\n"
                            f"{ctx.kwargs}```\n\n"
                            f"**Exception:** ```py\n"
                            f"{exception}```\n"
                            f"**Exception ARGs:** ```py\n"
                            f"{exception.args}```\n\n"
                            # f"**Traceback:** ```py\n"
                            # f"{tb or traceback.format_tb(exception.__traceback__)}```\n\n"
                            f"**Invoked by:** {ctx.author.mention} | {ctx.author.id}"
            )

            await dev.send(
                embed=unexpected_error_embed,
                file=discord.File(fp=io.BytesIO((tb or traceback.format_tb(exception.__traceback__)).encode('utf-8')), filename='traceback.txt')
            )
    else:
        if isinstance(exception, commands.NoPrivateMessage):
            no_private_message_error_embed = discord.Embed(
                color=0xffffff,
                title=ctx.bot.user.name,
                description=f"You cannot use the command({ctx.command.name}) in private messages.",
                timestamp=datetime.datetime.now()
            )

            no_private_message_error_embed.set_footer(icon_url=ctx.bot.user.avatar.url)

            await ctx.send(
                embed=no_private_message_error_embed
            )


async def clear_deleted_webhooks(client: discord.Client):
    for guild in client.guilds:
        guild_id = guild.id

        db, cursor = database(guild_id)

        all_webhooks_list_tuple: list[tuple[str, int, str]] = (
            cursor.execute("SELECT * FROM webhooks").fetchall()
        )

        for webhook_tuple in all_webhooks_list_tuple:
            webhook = discord.Webhook.from_url(webhook_tuple[2], client=client)
            try:
                await webhook.fetch()
            except discord.errors.NotFound:
                cursor.execute("DELETE FROM webhooks WHERE webhook_url=?",
                               (webhook_tuple[2],))
                db.commit()


async def fix(member: Union[discord.Member, discord.User], *,
              guild: discord.Guild = None,
              full_check: Optional[bool] = None,
              registered_role_check: Optional[bool] = None,
              nick_check: Optional[bool] = None,
              rank_check: Optional[bool] = None,
              ban_check: Optional[bool] = None,
              mute_check: Optional[bool] = None,
              voice_mute_check: Optional[bool] = None,
              streak_check: Optional[bool] = None):
    if full_check is True:
        registered_role_check = True
        nick_check = True
        rank_check = True
        ban_check = True
        mute_check = True
        voice_mute_check = True
        streak_check = True

    fix_log = ""

    guild = guild or getattr(member, 'guild', None)

    if isinstance(member, discord.User):
        try:
            member = await guild.fetch_member(member.id)
        except discord.HTTPException:
            return

    db, cursor = database(guild.id)

    player = classes.NewPlayer.from_player_id(member.id, guild)

    if registered_role_check is True:
        registered_role = fetch_role('REGISTERED', guild)

        member_registered_bool = checks.check_registered(member)

        if member_registered_bool and registered_role not in member.roles:
            try:
                await member.add_roles(registered_role, atomic=True)
                fix_log += f"Added role({registered_role.mention})\n"
            except discord.HTTPException:
                pass
        elif member_registered_bool is False and registered_role in member.roles:
            try:
                await member.remove_roles(registered_role, atomic=True)
                fix_log += f"Removed role({registered_role.mention})\n"
            except discord.HTTPException:
                pass

    if rank_check is True and player is not None:
        rank = None
        for rank_tuple in cursor.execute("SELECT * FROM ranks").fetchall():
            temp_rank = classes.Rank.from_tuple(rank_tuple, guild)
            if temp_rank.starting_elo <= player.elo <= temp_rank.ending_elo:
                rank = temp_rank
            else:
                if temp_rank.role_id in [role.id for role in member.roles]:
                    temp_rank_role = fetch_role(temp_rank.role_id, guild)
                    try:
                        await member.remove_roles(temp_rank_role)
                    except discord.HTTPException:
                        pass

        if rank is not None:
            rank_role = fetch_role(rank.role_id, guild)
            if rank_role not in member.roles:
                try:
                    await member.add_roles(rank_role)
                except discord.HTTPException:
                    pass

    if ban_check is True:
        try:
            ranked_banned_role = fetch_role('RANKEDBANNED', guild)
            if (
                    ranked_banned_role.id not in [role.id for role in member.roles] and
                    checks.check_if_banned(member.id, guild.id)
            ):
                await member.add_roles(ranked_banned_role, atomic=True)
            elif (
                    ranked_banned_role.id in [role.id for role in member.roles] and
                    not checks.check_if_muted(member.id, guild.id)
            ):
                await member.remove_roles(ranked_banned_role, atomic=True)
        except discord.HTTPException:
            pass

    if mute_check is True:
        try:
            muted_role = fetch_role('MUTED', guild)
            if (
                    muted_role.id not in [role.id for role in member.roles] and
                    checks.check_if_muted(member.id, guild.id)
            ):
                await member.add_roles(muted_role)
            elif (
                    muted_role.id in [role.id for role in member.roles] and
                    not checks.check_if_muted(member.id, guild.id)
            ):
                await member.remove_roles(muted_role)
        except discord.HTTPException:
            pass

    if voice_mute_check is True:
        try:
            voice_muted_role = fetch_role('VOICEMUTED', guild)
            if (
                    voice_muted_role.id not in [role.id for role in member.roles] and
                    checks.check_if_voice_muted(member.id, guild.id)
            ):
                await member.add_roles(voice_muted_role)
            elif (
                    voice_muted_role.id in [role.id for role in member.roles] and
                    not checks.check_if_voice_muted(member.id, guild.id)
            ):
                await member.remove_roles(voice_muted_role)
        except discord.HTTPException:
            pass

    if streak_check is True and player is not None:
        player.fix_streak()

    if nick_check is True and player is not None:
        new_nick = ""
        if cursor.execute("SELECT * FROM toggleprefixusers WHERE member_id=?",
                          (member.id,)).fetchone() is None:
            new_nick = f"[{player.elo}] {get_ign_nick(member.id, guild)}"[:32]
        else:
            new_nick = f"{get_ign_nick(member.id, guild)}"[:32]
        if not member.display_name == new_nick:
            try:
                await member.edit(nick=new_nick)
            except discord.HTTPException:
                pass

def register(member: discord.Member, ign: str) -> Union[bool, Never]:
    if checks.check_ign_validation(ign) is False:
        raise errors.PlayerManagementError(f"`{ign}` is not a valid IGN.")

    db, cursor = database(member.guild.id)

    registered_as_selected_ign_id_tuple = cursor.execute("SELECT id FROM players WHERE ign LIKE ?",
                                                         (ign,)).fetchone()

    if registered_as_selected_ign_id_tuple is not None and registered_as_selected_ign_id_tuple[0] != member.id:
        raise errors.PlayerManagementError(f"Unfortunately, <@{registered_as_selected_ign_id_tuple[0]}> "
                                           f"is already registered as `{ign}`.")

    first_time = False

    if cursor.execute("SELECT * FROM players WHERE id=?",
                      (member.id,)).fetchone() is None:
        cursor.execute("INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (member.id, ign, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ''))
        db.commit()

        first_time = True
    else:
        cursor.execute("UPDATE players SET ign=? WHERE id=?",
                       (ign, member.id))
        db.commit()

    return first_time


def no_error_async(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            await func(*args, **kwargs)
        except:
            print(f"Error happened in function({func.__name__}):\n{traceback.format_exc()}")

    return wrapper


def get_page_content(the_list: list[str],
                     items_in_every_page: int,
                     current_page: int,
                     template: str) -> Union[tuple[str, int], tuple[None, int]]:
    max_page_count = math.ceil(len(the_list) / items_in_every_page)

    if current_page > max_page_count:
        return None, 0

    page_content = ""

    for page_item in the_list[(current_page - 1) * items_in_every_page:current_page * items_in_every_page]:
        page_content += f"{template.format(index=the_list.index(page_item) + 1, content=page_item)}\n"

    return page_content, max_page_count


async def fetch_image_from_message(message: discord.Message,
                                   *,
                                   file_name: Optional[str] = None,
                                   return_type: Literal['bytes', 'bytesio', 'file,url', 'url']) -> \
        Union[tuple[discord.File, str], io.BytesIO, bytes, str, None]:
    message = await message.fetch()

    if message.embeds + message.attachments == []:
        return None

    image_url = message.attachments[0].url if message.attachments != [] else message.embeds[0].url

    if return_type == 'url':
        return image_url
    else:
        image_bytes, file_type = await get_image_bytes_from_url(image_url)
        if return_type == 'bytes':
            return image_bytes
        elif return_type == 'bytesio':
            return io.BytesIO(image_bytes)
        else:
            return discord.File(fp=io.BytesIO(image_bytes), filename=f"{file_name}.{file_type}"), image_url


def get_10bit_from_16bit(string: str):
    pattern = re.compile(r"#?([0-9a-fA-F]+)")
    match = pattern.fullmatch(string)

    if match is None:
        raise errors.CommandsError(f"color({string}) is invalid.")

    return int(match.group(1), 16)


def get_ign_nick(member_id: int, guild: discord.Guild):
    db, cursor = database(guild.id)

    ign_tuple = cursor.execute("SELECT ign FROM players WHERE id=?",
                               (member_id,)).fetchone()

    if ign_tuple is None:
        return None

    ign = ign_tuple[0]

    nick_tuple = cursor.execute("SELECT nick FROM nicks WHERE member_id=?",
                                (member_id,)).fetchone()
    nick = nick_tuple[0] if nick_tuple is not None else None

    new_nick = f"{ign}{f' | {nick}' if nick is not None else ''}"

    return new_nick


async def close_channel(channel: discord.TextChannel,
                        bot: commands.Bot,
                        close_when: datetime.datetime,
                        closed_by: discord.Member,
                        reason: str = "Not Specified",
                        webhook: Optional[discord.Webhook] = None):
    webhook = webhook or await fetch_webhook(channel, bot)

    db, cursor = database(channel.guild.id)

    cursor.execute("INSERT INTO closing_channels VALUES (?, ?)",
                   (channel.id, int(close_when.timestamp())))
    db.commit()

    await webhook.send(
        embed=embed(
            channel.guild,
            "",
            f"Closing channel <t:{int(close_when.timestamp())}:R>\n\n"
            f"**Reason :** {reason}"
        )
    )

    await asyncio.sleep(int(close_when.timestamp() - datetime.datetime.now().timestamp()))

    await channel.delete(reason=f"{reason}\n"
                                f"By {closed_by.name} | {closed_by.id}")

    cursor.execute("DELETE FROM closing_channels WHERE channel_id=?",
                   (channel.id,))


async def send_leaderboard_message(channel: discord.abc.Messageable,
                                   bot: commands.Bot,
                                   the_list: list[Any],
                                   items_in_every_page: int,
                                   title: str,
                                   prefix: str,
                                   suffix: str,
                                   page: int,
                                   user_id: int):
    max_page = math.ceil(len(the_list) / items_in_every_page)

    def get_lb_page_content():
        page_content = prefix
        for item_str in the_list[(page - 1) * items_in_every_page:page * items_in_every_page]:
            page_content += f"{item_str}\n"
        page_content += suffix
        return page_content

    webhook = await fetch_webhook(channel,
                                  bot)

    lb_message = await webhook.send(
        embed=embed(
            channel.guild,
            title,
            get_lb_page_content(),
            embed_footer_text=f"{page}/{max_page}"
        ), wait=True
    )

    await lb_message.add_reaction('◀️')
    await lb_message.add_reaction('▶️')

    first_time = True

    def lb_reaction_check(reaction: discord.Reaction, user: discord.User):
        if reaction.message != lb_message or user.id != user_id or reaction.emoji.__str__() not in ["◀️", "▶️"]:
            return False
        asyncio.create_task(reaction.remove(user))
        if page == max_page and reaction.emoji.__str__() == "▶️":
            return False
        elif page == 1 and reaction.emoji.__str__() == "◀️":
            return False

        return True

    while 1:
        try:
            if first_time:
                first_time = False
            else:
                lb_message = await lb_message.edit(
                    embed=embed(
                        channel.guild,
                        title,
                        get_lb_page_content(),
                        embed_footer_text=f"{page}/{max_page}"
                    )
                )
            rct, usr = await bot.wait_for('reaction_add', check=lb_reaction_check, timeout=30)
            if rct.emoji.__str__() == "▶️":
                page += 1
            else:
                page -= 1
        except asyncio.TimeoutError:
            await lb_message.clear_reactions()
            return


def period_to_seconds(period_str: str):
    seconds = 0

    for days_match in re.compile(r'(?P<days>\d+)[dD]').finditer(period_str):
        seconds += 24 * 3600 * float(days_match["days"])

    for hours_match in re.compile(r'(?P<hours>\d+)[hH]').finditer(period_str):
        seconds += 3600 * float(hours_match["hours"])

    for minutes_match in re.compile(r'(?P<minutes>\d+)[mM]').finditer(period_str):
        seconds += 60 * float(minutes_match["minutes"])

    for seconds_match in re.compile(r'(?P<seconds>\d+)[sS]').finditer(period_str):
        seconds += float(seconds_match["seconds"])

    if seconds == 0:
        raise errors.CommandsError("Period is not written right. (ex. 30d2h30m10s)")

    return seconds


def seconds_to_readable_duration(total_seconds: float):
    days = math.floor(total_seconds / (3600 * 24))
    hours = math.floor(total_seconds / 3600 % 24)
    minutes = math.floor(total_seconds / 60 % 60)
    seconds = math.floor(total_seconds % 60)
    return "{}{}{}{}".format(
        f'{days} Day{"s" if days > 1 else ""} ' if days > 0 else '',
        f'{hours} Hour{"s" if hours > 1 else ""} ' if hours > 0 else '',
        f'{minutes} Minute{"s" if minutes > 1 else ""} ' if minutes > 0 else '',
        f'{seconds} Second{"s" if seconds > 1 else ""} ' if seconds > 0 else '',
    )


def approximate_duration(total_seconds: float):
    if total_seconds < 60:
        return "Less than a minute"
    elif 60 <= total_seconds < 120:
        return "1 Minute"
    elif 120 <= total_seconds < 3600:
        return "{} Minutes".format(int(total_seconds//60))
    elif 3600 <= total_seconds < 7200:
        return "1 Hour"
    elif 7200 <= total_seconds < 86400:
        return "{} Hours".format(int(total_seconds//3600))
    elif 86400 <= total_seconds < 172800:
        return "1 Day"
    else:
        return "{} Days".format(int(total_seconds//86400))


def party_limit_for(member: discord.Member):
    four_member_party_roles_ids = get_info_value('4MEMBERPARTYLIMITROLESIDS', member.guild)
    three_member_party_roles_ids = get_info_value('3MEMBERPARTYLIMITROLESIDS', member.guild)
    two_member_party_roles_ids = get_info_value('2MEMBERPARTYLIMITROLESIDS', member.guild)

    party_limit = -1

    for role in member.roles:
        if role.id in two_member_party_roles_ids:
            party_limit = 2 if party_limit < 2 else party_limit
        elif role.id in three_member_party_roles_ids:
            party_limit = 3 if party_limit < 3 else party_limit
        elif role.id in four_member_party_roles_ids:
            party_limit = 3 if party_limit < 3 else party_limit

    return party_limit


def party_games_left(user_id: int, guild: discord.Guild):
    db, cursor = database(guild.id)
    old_games_count = cursor.execute("SELECT games_count FROM party_games WHERE player_id=?",
                                     (user_id,)).fetchone()
    if old_games_count is None:
        return 0

    return old_games_count[0]
