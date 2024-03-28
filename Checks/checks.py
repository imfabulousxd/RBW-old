import glob
import sqlite3
from multipledispatch import dispatch
from typing import overload, Optional

import discord
from discord.ext import commands

import classes
from Functions import functions


def check_cmd_permission(member: discord.Member, cmd: str, bot: commands.Bot):
    if member.id == member.guild.owner.id:
        return True

    if member.id in bot.full_perm_users:
        return True

    if member.id in bot.owner_ids:
        return True

    command_roles, _ = functions.get_command_roles(cmd.lower(), member.guild, bot)

    for role in member.roles:
        if role.id in command_roles:
            return True
    return False


def check_ign_validation(ign: str) -> bool:
    valid_chars = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r",
                   "s", "t", "u", "v", "w", "x", "y", "z", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                   "_"]

    for char in ign.lower():
        if char not in valid_chars:
            return False

    if not 3 <= len(ign) <= 16:
        return False

    return True


@dispatch(discord.Member)
def check_registered(member: discord.Member) -> bool:
    db, cursor = functions.database(member.guild.id)

    if cursor.execute("SELECT id FROM players WHERE id=?",
                      (member.id,)).fetchone() is None:
        return False

    return True


@dispatch(int, int)
def check_registered(member_id: int, guild_id: int) -> bool:
    db, cursor = functions.database(guild_id)

    if cursor.execute("SELECT id FROM players WHERE id=?",
                      (member_id,)).fetchone() is None:
        return False

    return True


def check_if_member_can_queue(member: discord.Member, queue: classes.Queue) -> bool:
    if check_registered(member) is False:
        return False

    db, cursor = functions.database(member.guild.id)

    player_stats = classes.NewPlayer.from_tuple(cursor.execute("SELECT * FROM players WHERE id=?",
                                                               (member.id,)).fetchone(), member.guild)

    if check_if_banned(member.id, member.guild.id):
        return False

    # Check ELO range
    if not (queue.min_elo <= player_stats.elo <= queue.max_elo):
        return False

    return True


def check_if_banned(target_id: int, guild_id: int):
    db, cursor = functions.database(guild_id)

    if cursor.execute("SELECT * FROM bans WHERE member_id=? AND state=?",
                      (target_id, "BANNED")).fetchone() is None:
        return False
    else:
        return True


def check_if_muted(target_id: int, guild_id: int):
    db, cursor = functions.database(guild_id)

    if cursor.execute("SELECT * FROM mutes WHERE member_id=? AND state=?",
                      (target_id, "MUTED")).fetchone() is None:
        return False
    else:
        return True


def check_if_voice_muted(target_id: int, guild_id: int):
    db, cursor = functions.database(guild_id)

    if cursor.execute("SELECT * FROM voicemutes WHERE member_id=? AND state=?",
                      (target_id, "VOICEMUTED")).fetchone() is None:
        return False
    else:
        return True


def check_if_in_party(member_id: int, guild: discord.Guild) -> Optional[classes.Party]:
    db, cursor = functions.database(guild.id)

    p_leader_id_tuple = cursor.execute("SELECT leader_id FROM party_members WHERE member_id=?",
                                       (member_id, )).fetchone()
    if p_leader_id_tuple is None:
        return None

    p_tuple = cursor.execute("SELECT * FROM parties WHERE leader_id=?",
                             (p_leader_id_tuple[0], )).fetchone()
    return classes.Party.from_tuple(p_tuple, guild)


def check_party_ignored(party_leader_id: int, invited_user_id: int, guild: discord.Guild):
    db, cursor = functions.database(guild.id)

    party_ignore_list_tuple = cursor.execute("SELECT ignoredlist FROM party_ignore_lists WHERE member_id=?",
                                             (invited_user_id, )).fetchone()
    party_ignore_list = []
    if party_ignore_list_tuple is not None and party_ignore_list_tuple[0] != '':
        party_ignore_list = [int(t) for t in party_ignore_list_tuple[0].split(',')]

    if party_leader_id in party_ignore_list:
        return True
    else:
        return False
