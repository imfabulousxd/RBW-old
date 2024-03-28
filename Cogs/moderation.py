import asyncio
import copy
import datetime
import glob
import io
import re
import traceback

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord.ext.commands._types import BotT

import Checks.discordchecks
import Functions.moderationfunctions
import classes
import config
import converters
import dpyfuncs
import embeds
import errors
import parameters
from typing import Required, Optional, Literal
from Functions import functions
from Checks import discordchecks, appcommand_checks
from Cooldowns import usercooldown
import os

from Checks import checks


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "Moderation"
        self.emoji = "💼"
        self.description = "Moderation Commands to keep the community clean."

    @commands.command(
        name="addcommandrole",
        description="Gives access to a specific role to use that command",
        extras={"group": "MODERATION"},
        aliases=["addcr"]
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def addcommandrole(self, ctx: commands.Context,
                             role_data: str = parameters.ROLE_DATA,
                             *, command_name_or_aliase: str = commands.parameter(
                displayed_name="Command name | Command aliase")):
        role = functions.fetch_role(role_data, ctx.guild)

        command_name = functions.add_command_role(
            command_name_or_aliase,
            role,
            ctx.bot
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=embeds.moderation_embed(
                ctx.author,
                f"Gave role({role.mention}) access to the command({command_name})."
            )
        )

    @commands.command(
        name="addroletoallcommands",
        aliases=[],
        description="Gives a specific role access to use all commands",
        extras={"group": "MODERATION"}
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def addroletoallcommands(self, ctx: commands.Context,
                                   role_data: str = parameters.ROLE_DATA):
        role = functions.fetch_role(role_data, ctx.guild)

        for command in ctx.bot.all_commands.keys():
            try:
                functions.add_command_role(command.name, role, ctx.bot)
            except:
                pass

        for app_command in ctx.bot.tree.get_commands():
            try:
                functions.add_command_role(app_command.name, role, ctx.bot)
            except:
                pass

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=embeds.moderation_embed(
                ctx.author,
                f"Added Role({role.mention}) to all commands."
            )
        )

    @commands.command(
        name="removecommandrole",
        description="Removes access of a role from using that command",
        extras={"group": "MODERATION"},
        aliases=["removecr"]
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def removecommandrole(self, ctx: commands.Context,
                                role_data: str = parameters.ROLE_DATA,
                                *, command_name_or_aliase: str = commands.parameter(
                displayed_name="Command name | Command aliase")):
        role = functions.fetch_role(role_data, ctx.guild)

        command_name = functions.remove_command_role(
            command_name_or_aliase,
            role,
            ctx.bot
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=embeds.moderation_embed(
                ctx.author,
                f"Removed role({role.mention}) access to use the command({command_name})."
            )
        )

    @commands.command(
        name="removerolefromallcommands",
        aliases=[],
        description="Removes a specific roles' access from using any commands",
        extras={"group": "MODERATION"}
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def removerolefromallcommands(self, ctx: commands.Context,
                                        role_data: str = parameters.ROLE_DATA):
        role = functions.fetch_role(role_data, ctx.guild)

        for command in ctx.bot.all_commands.keys():
            try:
                functions.remove_command_role(command.name, role, ctx.bot)
            except:
                pass

        for app_command in ctx.bot.tree.get_commands():
            try:
                functions.remove_command_role(app_command.name, role, ctx.bot)
            except:
                pass

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=embeds.moderation_embed(
                ctx.author,
                f"Removed Role({role.mention}) from all commands."
            )
        )

    @commands.command(
        name="commandroles",
        aliases=["crs"],
        description="Displays all the roles that have access to use this command",
        extras={"group": "MODERATION"}
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def command_roles(self, ctx: commands.Context,
                            *, command_name_or_aliase: str = parameters.parameter(
                displayed_name="Command name | Command aliase")):
        command_roles_list, command_name = functions.get_command_roles(command_name_or_aliase, ctx.guild,
                                                                       ctx.bot)

        command_roles_list_mention = [f"<@&{command_role_id}>" for command_role_id in command_roles_list]

        command_roles_str = functions.list_to_str(command_roles_list_mention, "\n")

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                f"{command_name} roles",
                command_roles_str,
                embed_footer_text=True,
                embed_footer_icon_url=True
            )
        )

    @commands.command(
        name="setinfo",
        aliases=[],
        description="Sets info (For staff)",
        extras={"group": "MODERATION"}
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def setinfo(self, ctx: commands.Context,
                      info_name: str = parameters.parameter(displayed_name="Info name"),
                      *, info_value: str = parameters.parameter(displayed_name="Info value", default='')):
        info_name = info_name.upper()

        if info_name not in config.ALL_INFO_NAMES_DICT:
            raise errors.ModerationError(f"Info({info_name}) doesn't exist. Info names: ```py\n"
                                         f"{functions.list_to_str(config.ALL_INFO_NAMES_DICT, ', ')}```")

        # converting the value given
        if config.ALL_INFO_NAMES_DICT[info_name][0] == int:
            info_value = info_value.replace("#", "")
            try:
                info_value = int(info_value, config.ALL_INFO_NAMES_DICT[info_name][1])
            except ValueError:
                raise errors.ModerationError(f"Converting value({info_value}) to integer failed.")
        elif config.ALL_INFO_NAMES_DICT[info_name][0] == str:
            info_value = str(info_value)

        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("DELETE FROM info WHERE info_name=?",
                       (info_name,))
        db.commit()

        cursor.execute("INSERT INTO info VALUES (?, ?)",
                       (info_name, info_value))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=embeds.moderation_embed(
                ctx.author,
                f"Successfully set {info_name}: `{info_value}`"
            )
        )

    @commands.command(
        name="setrole",
        aliases=[],
        description="Sets roles (For staff)",
        extras={"group": "MODERATION"}
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def setrole(self, ctx: commands.Context,
                      role_name: str = parameters.parameter(displayed_name="Role Name"),
                      role_data: str = parameters.ROLE_DATA):

        role_name = role_name.upper()

        if role_name not in config.ROLE_NAMES_TUPLE:
            raise errors.ModerationError(f"RoleName({role_name}) does not exist. Role names: ```py\n"
                                         f"{functions.list_to_str(config.ROLE_NAMES_TUPLE, ', ')}```")

        role = functions.fetch_role(role_data, ctx.guild)

        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("DELETE FROM roles WHERE role_name=?",
                       (role_name,))
        db.commit()

        cursor.execute("INSERT INTO roles VALUES (?, ?)",
                       (role_name, role.id))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=embeds.moderation_embed(
                ctx.author,
                f"Successfully set RoleName({role_name}): {role.mention}."
            )
        )

    @commands.command(
        name="setchannel",
        aliases=[],
        description="Sets channels (For staff)",
        extras={"group": "MODERATION"}
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def setchannel(self, ctx: commands.Context,
                         channel_name: str = parameters.parameter(displayed_name="Channel Name"),
                         channel_data: str = parameters.CHANNEL_DATA):
        channel_name = channel_name.upper()

        if channel_name not in config.CHANNELS_NAMES_DICT:
            raise errors.ModerationError(f"ChannelName({channel_name}) does not exist. Channel names: ```py\n"
                                         f"{functions.list_to_str(config.CHANNELS_NAMES_DICT, ', ')}```")

        channel = await functions.fetch_channel(channel_data, ctx.guild)

        if not isinstance(channel, config.CHANNELS_NAMES_DICT[channel_name][0]):
            raise errors.ModerationError(f"Channel({channel.jump_url}) is not a "
                                         f"`{config.CHANNELS_NAMES_DICT[channel_name][0].__name__}`")

        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("DELETE FROM channels WHERE channel_name=?",
                       (channel_name,))
        db.commit()

        cursor.execute("INSERT INTO channels VALUES (?, ?)",
                       (channel_name, channel.id))

        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=embeds.moderation_embed(
                ctx.author,
                f"Successfully set ChannelName({channel_name}): {channel.jump_url}"
            )
        )

    @commands.command(
        name="addqueue",
        aliases=['addq'],
        description="Adds a Queue (For staff)",
        extras={"group": "MODERATION"}
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def addqueue(self, ctx: commands.Context,
                       queue_vc_data: str = parameters.CHANNEL_DATA,
                       queue_player_count: int = parameters.parameter(displayed_name="Player Count"),
                       queue_automatic_or_picking: str = parameters.parameter(displayed_name="AUTOMATIC | PICKING"),
                       queue_ranked_or_casual: str = parameters.parameter(displayed_name="RANKED | CASUAL"),
                       queue_min_elo: int = parameters.parameter(displayed_name="Minimum ELO"),
                       queue_max_elo: int = parameters.parameter(displayed_name="Maximum ELO")):

        queue_automatic_or_picking = queue_automatic_or_picking.upper()
        queue_ranked_or_casual = queue_ranked_or_casual.upper()

        if queue_player_count % 2 == 1:
            raise errors.QueueError("Player count cannot be an odd number.")

        if queue_automatic_or_picking not in ["AUTOMATIC", "PICKING"]:
            raise errors.InvalidSyntax(self.addqueue.usage)

        if queue_ranked_or_casual not in ["RANKED", "CASUAL"]:
            raise errors.InvalidSyntax(self.addqueue.usage)

        if queue_min_elo > queue_max_elo:
            raise errors.QueueError("Minimum ELO cannot be greater than Maximum ELO.")

        queue_vc = await functions.fetch_channel(queue_vc_data, ctx.guild)

        if not isinstance(queue_vc, discord.VoiceChannel):
            raise errors.QueueError(f"{queue_vc} is not a `{discord.VoiceChannel.__name__}`.")

        db, cursor = functions.database(ctx.guild.id)

        if cursor.execute("SELECT * FROM queues WHERE queue_vc_id=?",
                          (queue_vc.id,)).fetchone() is not None:
            raise errors.QueueError(f"{queue_vc.mention} is already a queue.")

        cursor.execute("INSERT INTO queues VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (
                           queue_vc.id,
                           queue_player_count,
                           1 if queue_automatic_or_picking == "AUTOMATIC" else 0,
                           1 if queue_ranked_or_casual == "RANKED" else 0,
                           queue_min_elo,
                           queue_max_elo,
                           ""
                       ))
        db.commit()

        cursor.execute(f"INSERT INTO queues_players VALUES (?, ?)",
                       (queue_vc.id, ""))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Queue System",
                f"Successfully added Queue({queue_vc.jump_url}).",
                embed_footer_text=f"Invoked by {ctx.author.id}",
                embed_footer_icon_url=True,
                embed_timestamp=True
            )
        )

    @commands.command(
        name="removequeue",
        aliases=["removeq"],
        description="Removes a Queue (For staff)",
        extras={"group": "MODERATION"}
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def removequeue(self, ctx: commands.Context,
                          queue_vc_data: str = parameters.CHANNEL_DATA):
        queue_vc = await functions.fetch_channel(queue_vc_data, ctx.guild)

        if not isinstance(queue_vc, discord.VoiceChannel):
            raise errors.QueueError(f"Channel({queue_vc.mention}) is not a {discord.VoiceChannel.__name__}")

        db, cursor = functions.database(ctx.guild.id)

        if cursor.execute("SELECT * FROM queues WHERE queue_vc_id=?", (queue_vc.id,)).fetchone() \
                is None:
            raise errors.QueueError(f"VoiceChannel({queue_vc.mention}) is not in the queues.")

        cursor.execute("DELETE FROM queues WHERE queue_vc_id=?",
                       (queue_vc.id,))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Queue System",
                f"Successfully removed Queue({queue_vc.jump_url}).",
                embed_footer_text=f"Invoked by {ctx.author.id}",
                embed_footer_icon_url=True,
                embed_timestamp=True
            )
        )

    @commands.command(name="addrank",
                      description="Adds a new Rank (For staff)")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def addrank(self, ctx: commands.Context, role_data: str = parameters.ROLE_DATA,
                      starting_elo: int = parameters.parameter(displayed_name="Starting ELO"),
                      ending_elo: int = parameters.parameter(displayed_name="Ending ELO"),
                      win_elo: int = parameters.parameter(displayed_name="Win ELO"),
                      lose_elo: int = parameters.parameter(displayed_name="Lose ELO"),
                      mvp_elo: int = parameters.parameter(displayed_name="MVP ELO"),
                      role_icon: str = parameters.parameter(displayed_name="Icon URL | Icon Attachment", default=None)):
        if starting_elo >= ending_elo:
            raise errors.RanksError(f"Starting ELO cannot be greater or equal to Ending ELO.")

        db, cursor = functions.database(ctx.guild.id)

        role = functions.fetch_role(role_data, ctx.guild)

        if cursor.execute("SELECT * FROM ranks WHERE role_id=?",
                          (role.id,)).fetchone() is not None:
            raise errors.RanksError(f"Rank({role.mention}) already exists'.")

        role_icon_file, role_icon_url = await functions.fetch_image_from_message(message=ctx.message,
                                                                                 file_name=f"{role.id}",
                                                                                 return_type='file,url')

        with open(f"Guilds/{ctx.guild.id}/Ranks/{role_icon_file.filename}", 'wb') as f:
            f.write(role_icon_file.fp.read())

        role_color_int = role.color.value

        cursor.execute("INSERT INTO ranks VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (role.id,
                        starting_elo,
                        ending_elo,
                        win_elo,
                        lose_elo,
                        mvp_elo,
                        role_color_int))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Ranks System",
                f"Added Rank({role.mention}): **{starting_elo}-{ending_elo}** W:({f'+{win_elo}' if win_elo >= 0 else f'{win_elo}'}) "
                f"L:({f'+{lose_elo}' if lose_elo >= 0 else f'{lose_elo}'}) "
                f"MVP:({f'+{mvp_elo}' if mvp_elo >= 0 else f'{mvp_elo}'}) ",
                embed_footer_text=f"Invoked by {ctx.author.name}",
                embed_thumbnail_url=role_icon_url,
                embed_timestamp=True
            )
        )

    @commands.command(name="removerank",
                      description="Removes a Rank (For staff)")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def removerank(self, ctx: commands.Context,
                         role_data: str = parameters.ROLE_DATA):

        role = functions.fetch_role(role_data, ctx.guild)

        db, cursor = functions.database(ctx.guild.id)

        rank_tuple = cursor.execute("SELECT * FROM ranks WHERE role_id=?",
                                    (role.id,)).fetchone()

        if rank_tuple is None:
            raise errors.RanksError(f"Role({role.mention}) is not a rank.")

        cursor.execute("DELETE FROM ranks WHERE role_id=?",
                       (role.id,))
        db.commit()

        os.remove(glob.glob(f"Guilds/{ctx.guild.id}/Ranks/{role.id}.*")[0])

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Ranks System",
                f"Removed Rank({role.mention}) from ranks.",
                embed_footer_text=f"Invoked by {ctx.author.name}",
                embed_timestamp=True
            )
        )

    @commands.command(
        name="ranks",
        aliases=["rks"],
        description="Shows all Ranks"
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def ranks(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        ranks = []

        for rank_tuple in cursor.execute("SELECT * FROM ranks").fetchall():
            rank = classes.Rank.from_tuple(rank_tuple, ctx.guild)
            ranks.append(f"**{rank.starting_elo}** <@&{rank.role_id}> "
                         f"W:({f'+{rank.win_elo}' if rank.win_elo >= 0 else rank.win_elo}) "
                         f"L:({f'+{rank.lose_elo}' if rank.lose_elo >= 0 else rank.lose_elo}) "
                         f"MVP:({f'+{rank.mvp_elo}' if rank.mvp_elo >= 0 else rank.mvp_elo})")

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "ELO System",
                f"**Ranks:**\n\n" +
                "\n".join(ranks),
                embed_footer_text="Ranked Bedwars by imfabulousxd"
            )
        )

    @commands.command(
        name="screenshare",
        aliases=["ss"],
        description="Request a screenshare for the target that you think is cheating",
        extras={"group": "MODERATION"}
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_1P60_COOLDOWN
    async def screenshare(self, ctx: commands.Context,
                          member_data: str = parameters.PLAYER_DATA,
                          *, reason: Optional[str] = parameters.REASON,
                          attachment: Optional[str] = parameters.ATTACHMENT):
        target = await functions.fetch_member(member_data, ctx.guild)

        screenshare_message = await ctx.message.fetch()

        if len(screenshare_message.embeds + screenshare_message.attachments) == 0:
            raise commands.MissingRequiredAttachment(self.screenshare.params["attachment"])

        image_attachment_url = screenshare_message.attachments[0].url if \
            screenshare_message.attachments.__len__() != 0 else \
            screenshare_message.embeds[0].url

        image_attachment_bytes, image_attachment_type = await functions.get_image_bytes_from_url(image_attachment_url)
        image_attachment_file = discord.File(fp=io.BytesIO(image_attachment_bytes),
                                             filename=f"ss-{target.name}.{image_attachment_type}")

        screensharer_role = functions.fetch_role("SCREENSHARER", ctx.guild)

        # noinspection PyTypeChecker
        screenshare_channel = await ctx.guild.create_text_channel(
            f"{functions.get_info_value('CHANNELNAMEPREFIX', ctx.guild)}ss-{target.name}",
            category=await functions.fetch_channel("SCREENSHAREREQUESTSCATEGORY", ctx.guild),
            overwrites={
                ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                ctx.author: discord.PermissionOverwrite(view_channel=True,
                                                        send_messages=True,
                                                        read_message_history=True),
                target: discord.PermissionOverwrite(view_channel=True,
                                                    send_messages=True,
                                                    read_message_history=True),
                screensharer_role: discord.PermissionOverwrite(view_channel=True,
                                                               send_messages=True,
                                                               read_message_history=True)
            }
        )

        screenshare_channel_webhook = await functions.fetch_webhook(screenshare_channel, ctx.bot)

        screensharing_message = await screenshare_channel_webhook.send(
            content=screensharer_role.mention + target.mention,
            embed=functions.embed(
                ctx.guild,
                "Screensharing System",
                f"**Target:** {target.mention}\n"
                f"** Requested by:** {ctx.author.mention}\n"
                f"**Reason: **`{reason}`\n\n"
                f"{target.mention}, If no screensharer shows up after 15 minutes, You are free to log and queue."
            ),
            file=image_attachment_file,
            wait=True
        )

        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("INSERT INTO screenshares VALUES (?, ?, ?, ?, ?)",
                       (screenshare_channel.id, target.id, ctx.author.id, None, reason))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Screensharing System",
                f"The Screenshare request against {target.mention} has been created in {screenshare_channel.mention}.",
                embed_footer_text=f"Invoked by {ctx.author.name}",
                embed_footer_icon_url=True,
                embed_timestamp=True
            )
        )

        def ss_reaction_check(reaction: discord.Reaction, user: discord.Member):
            if reaction.message.id != screensharing_message.id:
                return False
            elif reaction.emoji.__str__() != "❄️" and reaction.emoji.__str__() != "🔒":
                return False

            import Checks.checks
            if not Checks.checks.check_cmd_permission(user, "freeze", ctx.bot):
                return False
            return True

        closed_reason = "No screensharer showed up"

        try:
            await screensharing_message.add_reaction('❄️')
            await screensharing_message.add_reaction('🔒')

            ss_reaction, ss_user = await ctx.bot.wait_for(
                'reaction_add', check=ss_reaction_check, timeout=15 * 60
            )
            await ss_reaction.remove(ss_user)

            if ss_reaction.emoji.__str__() == "🔒":
                closed_reason = f"Request denied by {ss_user.mention}"
                raise asyncio.TimeoutError()

            await Functions.moderationfunctions.freeze(target, ss_user)

            db, cursor = functions.database(ctx.guild.id)

            cursor.execute("UPDATE screenshares SET screensharer=? WHERE channel_id=?",
                           (ss_user.id, screenshare_channel.id))
            db.commit()

            await screenshare_channel_webhook.send(
                content=target.mention,
                embed=functions.embed(
                    ctx.guild,
                    "Moderation System",
                    f"{target.mention} **Is now frozen**\n\n"
                    f"**Tips** ```py\n"
                    f"1. Do not Log or turn off any Application\n"
                    f"2. Do not Plug/unplug any peripheral device such as mouse/keyboard\n"
                    f"3. Do not Rename\\Delete\\Modify Any File```",
                    embed_footer_text=f"Invoked by {ss_user.name}"
                )
            )

        except asyncio.TimeoutError:
            await Functions.moderationfunctions.close_request(
                ctx.bot.user,
                screenshare_channel,
                ctx.bot,
                closed_reason
            )

    @commands.command(
        name="closerequest",
        aliases=["closereq"],
        description="Closes a screenshare request channel ss-XXXX (For staff)",
        extras={"group": "MODERATION"}
    )
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @discordchecks.ss_channel_check()
    @usercooldown.USER_1P5_COOLDOWN
    async def closerequest(self, ctx: commands.Context, *, reason: str = parameters.REASON):
        await Functions.moderationfunctions.close_request(ctx.author, ctx.channel, ctx.bot, reason)

    @commands.command(name="rankedban",
                      aliases=["rb", "ban", "rankban"],
                      description="Bans Player for a specific time from Playing or Queuing")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def rankedban(self, ctx: commands.Context,
                        target_data: str = parameters.PLAYER_DATA,
                        period: str = parameters.PERIOD,
                        *, reason: str = parameters.REASON):
        member = await functions.fetch_member(target_data, ctx.guild)
        if member is None:
            member = await dpyfuncs.fetch_user(target_data, ctx.bot)

        seconds = functions.period_to_seconds(period)

        if checks.check_if_banned(member.id, ctx.guild.id):
            raise errors.ModerationError(f"User({member.mention}) is already banned.")

        ranked_banned_message = await Functions.moderationfunctions.ban(
            member,
            seconds,
            ctx.author,
            reason,
            ctx.guild,
            ctx.bot
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=ranked_banned_message.embeds[0]
        )

    @commands.command(name="rankedunban",
                      aliases=["unrb", "unban", "rankunban"],
                      description="Unbans Player from Playing or Queuing")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def rankedunban(self, ctx: commands.Context,
                          target_data: str = parameters.PLAYER_DATA,
                          *, reason: str = parameters.REASON):
        member = await functions.fetch_member(target_data, ctx.guild)
        if member is None:
            member = await dpyfuncs.fetch_user(target_data, ctx.bot)

        if not checks.check_if_banned(member.id, ctx.guild.id):
            raise errors.ModerationError(f"User({member.mention}) is not banned.")

        ranked_unbanned_message = await Functions.moderationfunctions.unban(
            member,
            ctx.author,
            reason,
            ctx.guild,
            ctx.bot
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=ranked_unbanned_message.embeds[0]
        )

    @commands.command(name="blacklist",
                      description="Blacklists this ign")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def blacklist(self, ctx: commands.Context, ign: str):
        if not checks.check_ign_validation(ign):
            raise errors.PlayerManagementError(f"`{ign}` is not a valid IGN.")

        db, cursor = functions.database(ctx.guild.id)

        if cursor.execute("SELECT * FROM blacklisted_igns WHERE ign LIKE ?",
                          (ign,)).fetchone() is not None:
            raise errors.ModerationError(f"{ign} is already blacklisted")

        cursor.execute("INSERT INTO blacklisted_igns VALUES (?)",
                       (ign,))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                '',
                f'Blacklisted `{ign}`.'
            )
        )

    @commands.command(name="unblacklist",
                      description="unBlacklists this ign")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def unblacklist(self, ctx: commands.Context, ign: str):
        if not checks.check_ign_validation(ign):
            raise errors.PlayerManagementError(f"`{ign}` is not a valid IGN.")

        db, cursor = functions.database(ctx.guild.id)

        if cursor.execute("SELECT * FROM blacklisted_igns WHERE ign LIKE ?",
                          (ign,)).fetchone() is None:
            raise errors.ModerationError(f"{ign} is not blacklisted")

        cursor.execute("DELETE FROM blacklisted_igns WHERE ign LIKE ?",
                       (ign,))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                '',
                f'UnBlacklisted `{ign}`.'
            )
        )

    @commands.command(name="mute",
                      description="Mutes Player for a specific time")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def mute(self, ctx: commands.Context,
                   target_data: str = parameters.PLAYER_DATA,
                   period: str = parameters.PERIOD,
                   *, reason: str = parameters.REASON):
        member = await functions.fetch_member(target_data, ctx.guild)
        if member is None:
            member = await dpyfuncs.fetch_user(target_data, ctx.bot)

        seconds = functions.period_to_seconds(period)

        if checks.check_if_muted(member.id, ctx.guild.id):
            raise errors.ModerationError(f"User({member.mention}) is already muted.")

        muted_message = await Functions.moderationfunctions.mute(
            member,
            seconds,
            ctx.author,
            reason,
            ctx.guild,
            ctx.bot
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=muted_message.embeds[0]
        )

    @commands.command(name="unmute",
                      description="Unmutes Player")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def unmute(self, ctx: commands.Context,
                     target_data: str = parameters.PLAYER_DATA,
                     *, reason: str = parameters.REASON):
        member = await functions.fetch_member(target_data, ctx.guild)
        if member is None:
            member = await dpyfuncs.fetch_user(target_data, ctx.bot)

        if not checks.check_if_muted(member.id, ctx.guild.id):
            raise errors.ModerationError(f"User({member.mention}) is not muted.")

        unmuted_message = await Functions.moderationfunctions.unmute(
            member,
            ctx.author,
            reason,
            ctx.guild,
            ctx.bot
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=unmuted_message.embeds[0]
        )

    @commands.command(name="voicemute",
                      description="Voice Mutes Player for a specific time")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def voicemute(self, ctx: commands.Context,
                        target_data: str = parameters.PLAYER_DATA,
                        period: str = parameters.PERIOD,
                        *, reason: str = parameters.REASON):
        member = await functions.fetch_member(target_data, ctx.guild)
        if member is None:
            member = await dpyfuncs.fetch_user(target_data, ctx.bot)

        seconds = functions.period_to_seconds(period)

        if checks.check_if_muted(member.id, ctx.guild.id):
            raise errors.ModerationError(f"User({member.mention}) is already voice muted.")

        voice_muted_message = await Functions.moderationfunctions.voice_mute(
            member,
            seconds,
            ctx.author,
            reason,
            ctx.guild,
            ctx.bot
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=voice_muted_message.embeds[0]
        )

    @commands.command(name="voiceunmute",
                      description="Voice Unmutes Player")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def voiceunmute(self, ctx: commands.Context,
                          target_data: str = parameters.PLAYER_DATA,
                          *, reason: str = parameters.REASON):
        member = await functions.fetch_member(target_data, ctx.guild)
        if member is None:
            member = await dpyfuncs.fetch_user(target_data, ctx.bot)

        if not checks.check_if_voice_muted(member.id, ctx.guild.id):
            raise errors.ModerationError(f"User({member.mention}) is not voice muted.")

        voice_unmuted_message = await Functions.moderationfunctions.voice_unmute(
            member,
            ctx.author,
            reason,
            ctx.guild,
            ctx.bot
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=voice_unmuted_message.embeds[0]
        )

    @commands.command(name="strike",
                      aliases=["st"],
                      description="Adds 1 Strike to Player")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def strike(self, ctx: commands.Context,
                     user_data: str = parameters.USER_DATA, *,
                     reason: str = parameters.REASON):
        striked_message = await Functions.moderationfunctions.strike(
            user_data,
            ctx.guild,
            ctx.author,
            reason,
            ctx.bot
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=striked_message.embeds[0]
        )

    @commands.command(name="unstrike",
                      aliases=["ust"],
                      description="Removes 1 Strike from Player")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def unstrike(self, ctx: commands.Context,
                       user_data: str = parameters.USER_DATA, *,
                       reason: str = parameters.REASON):
        unstriked_message = await Functions.moderationfunctions.unstrike(
            user_data,
            ctx.guild,
            ctx.author,
            reason,
            ctx.bot
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=unstriked_message.embeds[0]
        )

    @commands.command(name="freeze",
                      description="Freezes Player (For staff)")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def freeze(self, ctx: commands.Context,
                     member_data: str = parameters.PLAYER_DATA):
        member = await functions.fetch_member(member_data, ctx.guild)
        await Functions.moderationfunctions.freeze(
            member,
            ctx.author
        )
        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Moderation System",
                f"{member.mention} **Is now frozen**\n\n"
                f"**Tips** ```py\n"
                f"1. Do not Log or turn off any Application\n"
                f"2. Do not Plug/unplug any peripheral device such as mouse/keyboard\n"
                f"3. Do not Rename\\Delete\\Modify Any File```",
                embed_footer_text=f"Invoked by {ctx.author.name}"
            )
        )

    @commands.command(name="unfreeze",
                      description="Unfreezes Player (For staff)")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def unfreeze(self, ctx: commands.Context,
                       member_data: str = parameters.PLAYER_DATA):
        member = await functions.fetch_member(member_data, ctx.guild)
        await Functions.moderationfunctions.unfreeze(
            member,
            ctx.author
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Moderation System",
                f"{member.mention} is no longer frozen.",
                embed_footer_text=f"Invoked by {ctx.author.name}"
            )
        )

    @commands.command(name="update",
                      aliases=["modify"],
                      description="Updates Players' Specfic stats")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def update(self, ctx: commands.Context,
                     member_data: str = parameters.PLAYER_DATA,
                     statmode: Literal[
                         "elo",
                         "peak_elo",
                         "wins",
                         "winstreak",
                         "peak_winstreak",
                         "losses",
                         "losestreak",
                         "peak_losestreak",
                         "mvps",
                         "games_played"
                     ] = parameters.parameter(displayed_name="Statmode"),
                     value: int = parameters.parameter(displayed_name="Value")):
        member = await functions.fetch_member(member_data, ctx.guild)
        player = classes.NewPlayer.from_player_id(member.id, ctx.guild)

        if player is None:
            raise errors.CommandsError(f"Member({member.mention}) is not registered.")

        old_stat = getattr(player, statmode)

        new_stat = value + old_stat

        setattr(player, statmode, new_stat)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Moderation System",
                f"Successfully updated player({member.mention})s' {statmode}.\n"
                f"`{old_stat}` ➜ `{getattr(player, statmode)}`"
            )
        )

        await functions.fix(member,
                            rank_check=True,
                            nick_check=True)

    @commands.command(name="resetstats",
                      description="Resets ALL player's stats")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def resetstats(self, ctx: commands.Context,
                         member_data: str = parameters.PLAYER_DATA, ):
        member = await functions.fetch_member(member_data, ctx.guild)

        player = classes.NewPlayer.from_player_id(member.id, ctx.guild)

        if player is None:
            raise errors.CommandsError(f"Member({member.mention}) is not registered.")

        player.reset_stats()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Moderation System",
                f"Successfully reset Member({member.mention})s' stats."
            )
        )

    @commands.command(name="forceregister",
                      aliases=["freg", "verify"],
                      description="Force Registers Player")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def forceregister(self, ctx: commands.Context,
                            member_data: str = parameters.PLAYER_DATA,
                            ign: str = parameters.IGN):
        if not checks.check_ign_validation(ign):
            raise errors.CommandsError(f"IGN({ign}) is not valid.")

        member = await functions.fetch_member(member_data, ctx.guild)

        player = classes.NewPlayer.from_player_id(member.id, ctx.guild)

        db, cursor = functions.database(ctx.guild.id)

        if player is None:
            cursor.execute("INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (member.id, ign,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ''))
            db.commit()
        else:
            cursor.execute("UPDATE players SET ign=? WHERE id=?",
                           (ign, member.id))
            db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Moderation System",
                "Successfully registered Member({0.mention}) as {1}.".format(member, ign)
            )
        )

        await functions.fix(member, full_check=True)

    @commands.command(name="addmap",
                      description="Adds a map (For staff)")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def addmap(self, ctx: commands.Context,
                     *, map_name: str = parameters.parameter(displayed_name="Map Name")):
        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("INSERT INTO maps VALUES (?)",
                       (map_name,))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Queue System",
                f"Successfully added Map(`{map_name}`) to maps."
            )
        )

    @commands.command(name="removemap",
                      description="Removes a map (For staff)")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def removemap(self, ctx: commands.Context,
                        *, map_name: str = parameters.parameter(displayed_name="Map Name")):
        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("DELETE FROM maps WHERE map LIKE ?",
                       (map_name,))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Queue System",
                f"Successfully removed Map(`{map_name}`) to maps."
            )
        )

    @commands.command(name="maps",
                      description="displays a list of maps")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def maps(self, ctx: commands.Context, ):
        db, cursor = functions.database(ctx.guild.id)

        all_maps_tuple_list = cursor.execute("SELECT * FROM maps").fetchall()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Maps",
                '\n'.join([t[0] for t in all_maps_tuple_list])
            )
        )

    @commands.command(name="fix",
                      description="Refreshes given Players' roles, nickname (For staff)")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def fix(self, ctx: commands.Context,
                  member_data: str = parameters.PLAYER_DATA):
        member = await functions.fetch_member(member_data, ctx.guild)

        await functions.fix(member, full_check=True)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Moderation System",
                f"Fixed Member({member.mention}).",
                embed_footer_text=f"Invoked by {ctx.author.name}"
            )
        )

    @commands.command(name="setrules",
                      description="Sets the rules of the season (For staff)")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def setrules(self, ctx: commands.Context,
                       *, rules: str = parameters.parameter(displayed_name="Rules")):
        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("DELETE FROM info WHERE info_name='RULES'")
        db.commit()

        cursor.execute("INSERT INTO info VALUES (?, ?)",
                       ("RULES", rules))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Rules",
                f"Successfully set the rules."
            )
        )

    @commands.command(name="history",
                      description="Shows Ban history and Strikes count")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_1P5_COOLDOWN
    async def history(self, ctx: commands.Context, player: converters.NewPlayerConverter = parameters.PLAYER_DATA, ):
        player: classes.NewPlayer
        db, cursor = functions.database(ctx.guild.id)
        strikes_info = cursor.execute("SELECT strikes FROM strikes WHERE member_id=?",
                                      (player.player_id,)).fetchone()
        strikes_info = strikes_info or (0,)
        bans = cursor.execute("SELECT * FROM bans WHERE member_id=?",
                              (player.player_id,)).fetchall()
        bans = bans or []
        mutes = cursor.execute("SELECT * FROM mutes WHERE member_id=?",
                               (player.player_id,)).fetchall()
        mutes = mutes or []

        bans_paginator = commands.Paginator('**Bans**', '', max_size=4096, linesep='\n\n')
        for ban_tuple in bans:
            bans_paginator.add_line(f"> Banned by <@{ban_tuple[1]}>\n"
                                    f"> Reason: `{ban_tuple[4]}`" +
                                    (f"\n> Ends on <t:{ban_tuple[2]}:F> (<t:{ban_tuple[2]}:R>)" if ban_tuple[
                                                                                               3] != "UNBANNED" else
                                     f""))
        mutes_paginator = commands.Paginator('**Mutes**', '', max_size=4096, linesep='\n\n')
        for mute_tuple in mutes:
            mutes_paginator.add_line(f"> Muted by <@{mute_tuple[1]}>\n"
                                     f"> Reason: `{mute_tuple[4]}`" +
                                     (f"\n> Ends on <t:{mute_tuple[2]}:F> (<t:{mute_tuple[2]}:R>)" if mute_tuple[
                                                                                                 3] != "UNMUTED" else
                                      f""))

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)
        embeds = [
            functions.embed(
                ctx.guild,
                f"History for {player.ign}",
                f"**Strikes**: {strikes_info[0]}"
            )
        ]

        for ban_page in bans_paginator.pages:
            embeds.append(
                functions.embed(
                    ctx.guild,
                    f"History for {player.ign}",
                    ban_page
                )
            )

        for mute_page in mutes_paginator.pages:
            embeds.append(
                functions.embed(
                    ctx.guild,
                    f"History for {player.ign}",
                    mute_page
                )
            )

        await webhook.send(
            embeds=embeds
        )

    @commands.command(name="endseason",
                      description="Resets DB, players' stats, games (For staff)")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def endseason(self, ctx: commands.Context):
        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        confirmed_message = await webhook.send(wait=True,
                                               embed=functions.embed(
                                                   ctx.guild,
                                                   "Moderation System",
                                                   "Ending the season will result in all of players data being deleted.\n"
                                                   "Are you sure? (Confirm this by typing 'confirm')"

                                               ))

        def message_check(msg: discord.Message):
            if msg.author.id == ctx.author.id and msg.channel.id == ctx.channel.id and msg.content == 'confirm':
                return True
            return False

        try:
            await ctx.bot.wait_for('message', check=message_check, timeout=30)
        except asyncio.TimeoutError:
            await confirmed_message.delete()
            return

        db, cursor = functions.database(ctx.guild.id)

        cursor.execute("UPDATE game_count SET game_count=0")
        db.commit()

        cursor.execute("DELETE FROM game_screenshots")
        db.commit()

        cursor.execute("DELETE FROM games")
        db.commit()

        cursor.execute("UPDATE players SET elo=0,"
                       "peak_elo=0,"
                       "wins=0,"
                       "winstreak=0,"
                       "peak_winstreak=0,"
                       "losses=0,"
                       "losestreak=0,"
                       "peak_losestreak=0,"
                       "mvps=0,"
                       "games_played=0,"
                       "games_ids=''")
        db.commit()

        cursor.execute("DELETE FROM scored_games")
        db.commit()

        cursor.execute("UPDATE daily SET elo=0,"
                       "wins=0,"
                       "losses=0,"
                       "mvps=0,"
                       "games_played=0")
        db.commit()

        cursor.execute("UPDATE weekly SET elo=0,"
                       "wins=0,"
                       "losses=0,"
                       "mvps=0,"
                       "games_played=0")
        db.commit()

        cursor.execute("DELETE FROM temp_mvps")
        db.commit()

        cursor.execute("DELETE FROM picking")
        db.commit()

        players_list_tuple = cursor.execute("SELECT id FROM players").fetchall()

        ending_season_msg = await webhook.send("Ending the Season...\n\n"
                                               f"ET: <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=0.5 * len(players_list_tuple))).timestamp())}:R>",
                                               wait=True)

        for player_id_tuple in players_list_tuple:
            try:
                member = await functions.fetch_member(player_id_tuple[0], ctx.guild)
                await functions.fix(member, nick_check=True, rank_check=True)
            except:
                pass

        await ending_season_msg.edit(
            content="Season ended!"
        )

    @app_commands.command(name='addcommandrole')
    @appcommand_checks.check_command_permission()
    async def addcommandrole_app_command(self, interaction: discord.Interaction, role: discord.Role,
                                         app_command_name: str):
        if app_command_name not in [t.name.lower() for t in self.bot.tree.get_commands()]:
            await interaction.response.send_message(content='this command does not exist.', ephemeral=True)
            return
        async with self.bot.pool.acquire() as conn:
            roles_ids_tuple = await (await conn.execute("SELECT app_command_roles_ids FROM app_commands_permissions "
                                                        "WHERE app_command_name=? AND guild_id=?",
                                                        (app_command_name, interaction.guild.id))).fetchone()
            if roles_ids_tuple is None:
                await conn.execute("INSERT INTO app_commands_permissions VALUES (?, ?, ?)",
                                   (app_command_name, role.id.__str__(), interaction.guild.id))
                await interaction.response.send_message(embed=discord.Embed(
                    description='Successfully gave role({0.mention}) permission to use command({1}).'.format(role,
                                                                                                             app_command_name),
                    colour=0
                ))
            elif role.id.__str__() in roles_ids_tuple[0]:
                await interaction.response.send_message(
                    content='Role({0.mention}) already has permission to use command({1}).'.format(role,
                                                                                                   app_command_name),
                    ephemeral=True)
            else:
                await conn.execute(
                    "UPDATE app_commands_permissions SET app_command_roles_ids=? WHERE app_command_name=? AND guild_id=?",
                    (roles_ids_tuple[0] + "," + role.id.__str__(), app_command_name, interaction.guild.id))
                await interaction.response.send_message(embed=discord.Embed(
                    description='Successfully gave role({0.mention}) permission to use command({1}).'.format(role,
                                                                                                             app_command_name),
                    colour=0
                ))

    @addcommandrole_app_command.autocomplete('app_command_name')
    async def addcommandrole_app_command_name_ac(self, interaction: discord.Interaction, current: str) -> list[
        app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=t.name, value=t.name.lower())
            for t in self.bot.tree.get_commands()
        ] if current == '' or current is None else [
            app_commands.Choice(name=t.name, value=t.name.lower())
            for t in self.bot.tree.get_commands() if t.name.lower().startswith(current.lower())
        ]

    @app_commands.command(name='removecommandrole')
    @appcommand_checks.check_command_permission()
    async def removecommandrole_app_command(self, interaction: discord.Interaction, role: discord.Role,
                                            app_command_name: str):
        if app_command_name not in [t.name.lower() for t in self.bot.tree.get_commands()]:
            await interaction.response.send_message(content='this command does not exist.', ephemeral=True)
            return

        async with self.bot.pool.acquire() as conn:
            roles_ids_tuple = await (await conn.execute("SELECT app_command_roles_ids FROM app_commands_permissions "
                                                        "WHERE app_command_name=? AND guild_id=?",
                                                        (app_command_name, interaction.guild.id))).fetchone()
            if roles_ids_tuple is None or role.id.__str__() not in roles_ids_tuple[0]:
                await interaction.response.send_message(
                    content='role({0.mention}) does not have permission to use command({1})'.format(
                        role, app_command_name
                    ))
                return
            else:
                roles_ids = roles_ids_tuple[0].split(',')
                roles_ids.remove(role.id.__str__())
                if roles_ids == []:
                    await conn.execute("DELETE FROM app_commands_permissions WHERE app_command_name=? AND guild_id=?",
                                       (app_command_name, interaction.guild.id))
                else:
                    await conn.execute(
                        "UPDATE app_commands_permissions SET app_command_roles_ids=? WHERE app_command_name=? AND "
                        "guild_id=?",
                        (','.join(roles_ids), app_command_name, interaction.guild.id))
                await interaction.response.send_message(
                    content='successfully removed Role({0.mention})\'s permission to use command({1}).'.format(role,
                                                                                                               app_command_name),
                    ephemeral=True)

    @removecommandrole_app_command.autocomplete('app_command_name')
    async def removecommandrole_app_command_name_ac(self, interaction: discord.Interaction, current: str) -> list[
        app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=t.name, value=t.name.lower())
            for t in self.bot.tree.get_commands()
        ] if current == '' or current is None else [
            app_commands.Choice(name=t.name, value=t.name.lower())
            for t in self.bot.tree.get_commands() if t.name.lower().startswith(current.lower())
        ]

    @tasks.loop(seconds=30)
    async def check_bans(self):
        for guild in self.bot.guilds:
            db, cursor = functions.database(guild.id)

            for banned_user_tuple in cursor.execute("SElECT * FROM bans WHERE state=?",
                                                    ("BANNED",)).fetchall():
                (banned_user_id,
                 _,
                 unbanned_at,
                 state,
                 _) = banned_user_tuple

                if datetime.datetime.fromtimestamp(unbanned_at) - datetime.timedelta(
                        seconds=30) < datetime.datetime.now():
                    try:
                        member = await functions.fetch_member(banned_user_id, guild)
                        if member is None:
                            member = await dpyfuncs.fetch_user(banned_user_id, self.bot)
                        await Functions.moderationfunctions.unban(
                            member,
                            self.bot.user,
                            "Auto Unban",
                            guild,
                            self.bot
                        )
                    except:
                        pass

    @check_bans.before_loop
    async def before_check_bans(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=30)
    async def check_mutes(self):
        for guild in self.bot.guilds:
            db, cursor = functions.database(guild.id)

            for muted_user_tuple in cursor.execute("SElECT * FROM mutes WHERE state=?",
                                                   ("MUTED",)).fetchall():
                (muted_user_id,
                 _,
                 unmuted_at,
                 state,
                 _) = muted_user_tuple

                if datetime.datetime.fromtimestamp(unmuted_at) - datetime.timedelta(
                        seconds=30) < datetime.datetime.now():
                    try:
                        member = await functions.fetch_member(muted_user_id, guild)
                        if member is None:
                            member = await dpyfuncs.fetch_user(muted_user_id, self.bot)

                        await Functions.moderationfunctions.unmute(
                            member,
                            self.bot.user,
                            "Auto Unmute",
                            guild,
                            self.bot
                        )
                    except:
                        pass

    @check_mutes.before_loop
    async def before_check_mutes(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=30)
    async def check_voicemutes(self):
        for guild in self.bot.guilds:
            db, cursor = functions.database(guild.id)

            for voice_muted_user_tuple in cursor.execute("SElECT * FROM voicemutes WHERE state=?",
                                                         ("VOICEMUTED",)).fetchall():
                (voice_muted_user_id,
                 _,
                 voice_unmuted_at,
                 state,
                 _) = voice_muted_user_tuple

                if datetime.datetime.fromtimestamp(voice_unmuted_at) - datetime.timedelta(
                        seconds=30) < datetime.datetime.now():
                    try:
                        member = await functions.fetch_member(voice_muted_user_id, guild)
                        if member is None:
                            member = await dpyfuncs.fetch_user(voice_muted_user_id, self.bot)
                        await Functions.moderationfunctions.voice_unmute(
                            member,
                            self.bot.user,
                            "Auto Unmute",
                            guild,
                            self.bot
                        )
                    except:
                        pass

    @check_voicemutes.before_loop
    async def before_check_voice_mutes(self):
        await self.bot.wait_until_ready()

    async def cog_load(self) -> None:
        self.check_bans.start()
        self.check_mutes.start()
        self.check_voicemutes.start()
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS app_commands_permissions (app_command_name TEXT, app_command_roles_ids TEXT, guild_id INT)")

    async def cog_unload(self) -> None:
        pass

    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        await functions.error_handler(ctx, error, traceback.format_exc())


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
