import datetime
import traceback
from typing import Union

import discord
from discord.ext import commands

import dpyfuncs
import errors
from Functions import functions


async def close_request(closed_by: discord.Member, channel: discord.TextChannel, bot: commands.Bot, reason: str):
    db, cursor = functions.database(channel.guild.id)

    ss_info_tuple = cursor.execute("SELECT * FROM screenshares WHERE channel_id=?",
                             (channel.id, )).fetchone()
    _, target_id, requested_by_id, screensharer_id, ssed_reason = ss_info_tuple

    await functions.close_channel(channel, bot, datetime.datetime.now() + datetime.timedelta(seconds=30),
                                  closed_by, reason)


async def freeze(member: discord.Member, frozen_by: discord.Member):
    frozen_role = functions.fetch_role("FROZEN", member.guild)

    try:
        await member.add_roles(frozen_role, atomic=True, reason=f"by {frozen_by.name} | {frozen_by.id}")
    except discord.HTTPException:
        pass


async def unfreeze(member: discord.Member, unfrozen_by: discord.Member):
    frozen_role = functions.fetch_role("FROZEN", member.guild)

    try:
        await member.remove_roles(frozen_role, atomic=True, reason=f"by {unfrozen_by.name} | {unfrozen_by.id}")
    except discord.HTTPException:
        pass


async def ban(target: discord.User, seconds: int, banned_by: discord.User, reason: str,
              guild: discord.Guild, bot: commands.Bot):

    unbanned_at = int((datetime.datetime.now() + datetime.timedelta(seconds=seconds)).timestamp())

    db, cursor = functions.database(guild.id)

    cursor.execute("INSERT INTO bans VALUES (?, ?, ?, ?, ?)",
                   (target.id, banned_by.id, unbanned_at, "BANNED", reason))
    db.commit()

    await functions.fix(target, guild=guild, ban_check=True)

    ranked_bans_channel = await functions.fetch_channel('RANKEDBANS', guild)

    ranked_banned_embed_fields = [
        ["User", target.mention, True],
        ["Moderator", banned_by.mention, True],
        ["Duration", functions.seconds_to_readable_duration(seconds), True],
        ["Expiry", f"<t:{unbanned_at}:D> ( <t:{unbanned_at}:R> )", True],
        ["Reason", f"`{reason}`", True]
    ]

    webhook = await functions.fetch_webhook(ranked_bans_channel, bot)

    ranked_banned_message = await webhook.send(
        content=target.mention,
        embed=functions.embed(
            guild,
            "Moderation System",
            f"You have been ranked banned for breaking server rules",
            embed_fields=ranked_banned_embed_fields,
            embed_footer_text=True,
            embed_timestamp=True,
            embed_thumbnail_url=True,
            embed_color=0
        ), wait=True
    )

    return ranked_banned_message


async def unban(target: discord.User, unbanned_by: discord.User, reason: str,
              guild: discord.Guild, bot: commands.Bot):

    db, cursor = functions.database(guild.id)

    if unbanned_by.id == bot.user.id:
        cursor.execute("UPDATE bans SET state=? WHERE member_id=? AND state=?",
                       ("UNBANNED", target.id, "BANNED"))
        db.commit()
    else:
        cursor.execute("DELETE FROM bans WHERE member_id=? AND state=?",
                       (target.id, "BANNED"))
        db.commit()

    await functions.fix(target, guild=guild, ban_check=True)

    ranked_bans_channel = await functions.fetch_channel('RANKEDBANS', guild)

    ranked_unbanned_embed_fields = [
        ["User", target.mention, True],
        ["Moderator", unbanned_by.mention, True],
        ["Reason", f"`{reason}`", True]
    ]

    webhook = await functions.fetch_webhook(ranked_bans_channel, bot)

    ranked_unbanned_message = await webhook.send(
        content=target.mention,
        embed=functions.embed(
            guild,
            "Moderation System",
            f"You have been unbanned, Feel free to play now!",
            embed_fields=ranked_unbanned_embed_fields,
            embed_footer_text=True,
            embed_timestamp=True,
            embed_thumbnail_url=True,
            embed_color=0
        ), wait=True
    )

    return ranked_unbanned_message


async def mute(target: discord.User, seconds: int, muted_by: discord.User, reason: str,
              guild: discord.Guild, bot: commands.Bot):

    unmuted_at = int((datetime.datetime.now() + datetime.timedelta(seconds=seconds)).timestamp())

    db, cursor = functions.database(guild.id)

    cursor.execute("INSERT INTO mutes VALUES (?, ?, ?, ?, ?)",
                   (target.id, muted_by.id, unmuted_at, "MUTED", reason))
    db.commit()

    await functions.fix(target, guild=guild, mute_check=True)

    mutes_channel = await functions.fetch_channel('MUTES', guild)

    muted_embed_fields = [
        ["User", target.mention, True],
        ["Moderator", muted_by.mention, True],
        ["Duration", functions.seconds_to_readable_duration(seconds), True],
        ["Expiry", f"<t:{unmuted_at}:D> ( <t:{unmuted_at}:R> )", True],
        ["Reason", f"`{reason}`", True]
    ]

    webhook = await functions.fetch_webhook(mutes_channel, bot)

    muted_message = await webhook.send(
        content=target.mention,
        embed=functions.embed(
            guild,
            "Moderation System",
            f"You have been muted for breaking server rules",
            embed_fields=muted_embed_fields,
            embed_footer_text=True,
            embed_timestamp=True,
            embed_thumbnail_url=True,
            embed_color=0
        ), wait=True
    )

    return muted_message


async def unmute(target: discord.User, unmuted_by: discord.User, reason: str,
              guild: discord.Guild, bot: commands.Bot):

    db, cursor = functions.database(guild.id)

    if unmuted_by.id == bot.user.id:
        cursor.execute("UPDATE mutes SET state=? WHERE member_id=? AND state=?",
                       ("UNMUTED", target.id, "MUTED"))
        db.commit()
    else:
        cursor.execute("DELETE FROM mutes WHERE member_id=? AND state=?",
                       (target.id, "MUTED"))
        db.commit()

    await functions.fix(target, guild=guild, mute_check=True)

    mutes_channel = await functions.fetch_channel('MUTES', guild)

    unmuted_embed_fields = [
        ["User", target.mention, True],
        ["Moderator", unmuted_by.mention, True],
        ["Reason", f"`{reason}`", True]
    ]

    webhook = await functions.fetch_webhook(mutes_channel, bot)

    unmuted_message = await webhook.send(
        content=target.mention,
        embed=functions.embed(
            guild,
            "Moderation System",
            f"Your mute has been exipred, You are free to go!",
            embed_fields=unmuted_embed_fields,
            embed_footer_text=True,
            embed_timestamp=True,
            embed_thumbnail_url=True,
            embed_color=0
        ), wait=True
    )

    return unmuted_message


async def voice_mute(target: discord.User, seconds: int, voice_muted_by: discord.User, reason: str,
              guild: discord.Guild, bot: commands.Bot):

    voice_unmuted_at = int((datetime.datetime.now() + datetime.timedelta(seconds=seconds)).timestamp())

    db, cursor = functions.database(guild.id)

    cursor.execute("INSERT INTO voicemutes VALUES (?, ?, ?, ?, ?)",
                   (target.id, voice_muted_by.id, voice_unmuted_at, "VOICEMUTED", reason))
    db.commit()

    await functions.fix(target, guild=guild, voice_mute_check=True)

    voice_mutes_channel = await functions.fetch_channel('VOICEMUTES', guild)

    voice_muted_embed_fields = [
        ["User", target.mention, True],
        ["Moderator", voice_muted_by.mention, True],
        ["Duration", functions.seconds_to_readable_duration(seconds), True],
        ["Expiry", f"<t:{voice_unmuted_at}:D> ( <t:{voice_unmuted_at}:R> )", True],
        ["Reason", f"`{reason}`", True]
    ]

    webhook = await functions.fetch_webhook(voice_mutes_channel, bot)

    voice_muted_message = await webhook.send(
        content=target.mention,
        embed=functions.embed(
            guild,
            "Moderation System",
            f"You have been muted for breaking server rules",
            embed_fields=voice_muted_embed_fields,
            embed_footer_text=True,
            embed_timestamp=True,
            embed_thumbnail_url=True,
            embed_color=0
        ), wait=True
    )

    return voice_muted_message


async def voice_unmute(target: discord.User, voice_unmuted_by: discord.User, reason: str,
              guild: discord.Guild, bot: commands.Bot):

    db, cursor = functions.database(guild.id)

    cursor.execute("UPDATE voicemutes SET state=? WHERE member_id=? AND state=?",
                   ("VOICEUNMUTED", target.id, "VOICEMUTED"))
    db.commit()

    await functions.fix(target, guild=guild, voice_mute_check=True)

    voice_mutes_channel = await functions.fetch_channel('VOICEMUTES', guild)

    voice_unmuted_embed_fields = [
        ["User", target.mention, True],
        ["Moderator", voice_unmuted_by.mention, True],
        ["Reason", f"`{reason}`", True]
    ]

    webhook = await functions.fetch_webhook(voice_mutes_channel, bot)

    voice_unmuted_message = await webhook.send(
        content=target.mention,
        embed=functions.embed(
            guild,
            "Moderation System",
            f"Your mute has been exipred, You are free to go!",
            embed_fields=voice_unmuted_embed_fields,
            embed_footer_text=True,
            embed_timestamp=True,
            embed_thumbnail_url=True,
            embed_color=0
        ), wait=True
    )

    return voice_unmuted_message


async def strike(target_data: str,
                 guild: discord.Guild,
                 striked_by: discord.Member,
                 reason: str,
                 bot: commands.Bot):
    target = await dpyfuncs.fetch_user(target_data, bot)

    if target is None:
        raise errors.CommandsError(f"User({target_data})")

    db, cursor = functions.database(guild.id)

    strikes_tuple = cursor.execute("SELECT strikes FROM strikes WHERE member_id=?",
                                   (target.id, )).fetchone()
    strikes = 1
    if strikes_tuple is None:
        cursor.execute("INSERT INTO strikes VALUES (?, ?)",
                       (target.id, strikes))
        db.commit()
    else:
        strikes = strikes_tuple[0] + 1
        cursor.execute("UPDATE strikes SET strikes=? WHERE member_id=?",
                       (strikes, target.id))
        db.commit()

    ban_tuple = None
    ban_info = ""

    if strikes == 2:
        ban_tuple = (target, 6*3600, striked_by, f"{strikes} strikes reached", guild, bot)
    elif strikes == 3:
        ban_tuple = (target, 12 * 3600, striked_by, f"{strikes} strikes reached", guild, bot)
    elif strikes == 4:
        ban_tuple = (target, 48 * 3600, striked_by, f"{strikes} strikes reached", guild, bot)
    elif strikes == 5:
        ban_tuple = (target, 3 * 24 * 3600, striked_by, f"{strikes} strikes reached", guild, bot)
    elif strikes == 6:
        ban_tuple = (target, 7 * 24 * 3600, striked_by, f"{strikes} strikes reached", guild, bot)
    elif strikes == 7:
        ban_tuple = (target, 14 * 24 * 3600, striked_by, f"{strikes} strikes reached", guild, bot)
    elif strikes == 8:
        ban_tuple = (target, 30 * 24 * 3600, striked_by, f"{strikes} strikes reached", guild, bot)

    if ban_tuple is not None:
        try:
            ban_message = await ban(*ban_tuple)
            ban_info = f"\n\n**Banned: **{functions.seconds_to_readable_duration(ban_tuple[1])}"
        except Exception as e:
            print(traceback.format_exc())

    strikes_channel = await functions.fetch_channel('STRIKES', guild)
    webhook = await functions.fetch_webhook(strikes_channel, bot)

    striked_message = await webhook.send(
        content=target.mention,
        embed=functions.embed(
            guild,
            "Moderation System",
            "Issued by: {}\n"
            "On: {}{}".format(striked_by.mention, target.mention, ban_info),
            embed_fields=[
                ["Reason", f"`{reason}`", True],
                ["Total Strikes", f"{strikes}", True]
            ],
            embed_footer_text=True,
            embed_thumbnail_url=True,
            embed_color=0
        ),
        wait=True
    )

    return striked_message


async def unstrike(target_data: str,
                 guild: discord.Guild,
                 unstriked_by: discord.Member,
                 reason: str,
                 bot: commands.Bot):
    target = await dpyfuncs.fetch_user(target_data, bot)

    if target is None:
        raise errors.CommandsError(f"User({target_data})")

    db, cursor = functions.database(guild.id)

    strikes_tuple = cursor.execute("SELECT strikes FROM strikes WHERE member_id=?",
                                   (target.id, )).fetchone()
    strikes = 1
    if strikes_tuple is None or strikes_tuple[0] == 0:
        raise errors.ModerationError(f"User({target.mention}) has no strikes.")
    else:
        strikes = strikes_tuple[0] - 1
        cursor.execute("UPDATE strikes SET strikes=? WHERE member_id=?",
                       (strikes, target.id))
        db.commit()

    strikes_channel = await functions.fetch_channel('STRIKES', guild)
    webhook = await functions.fetch_webhook(strikes_channel, bot)

    unstriked_message = await webhook.send(
        embed=functions.embed(
            guild,
            "Moderation System",
            "Issued by: {}\n"
            "On: {}\n\n"
            "**Warning: **Player might be banned, `=unstrike` **DOES NOT** undo bans.".format(unstriked_by.mention, target.mention),
            embed_fields=[
                ["Reason", f"`{reason}`", True],
                ["Total Strikes", f"{strikes}", True]
            ],
            embed_footer_text=True,
            embed_thumbnail_url=True,
            embed_color=0
        ),
        wait=True
    )

    return unstriked_message

