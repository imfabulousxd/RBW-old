import asyncio
import datetime
import traceback
from typing import Optional

import discord.ext.commands
from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord.ext.commands._types import BotT

import classes
import converters
import errors
import parameters
from Checks import discordchecks, checks
from Cooldowns import usercooldown
from Functions import functions
import asqlite


class Party(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "Party"
        self.emoji = "👥"
        self.description = "Party System"

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        if member.guild is None:
            return

        if before.channel == after.channel or after.channel is None:
            return

        db, cursor = functions.database(member.guild.id)

        party_leader_id_tuple = cursor.execute("SELECT leader_id FROM party_members WHERE member_id=?",
                                               (member.id,)).fetchone()
        if party_leader_id_tuple is None:
            return

        party_tuple = cursor.execute("SELECT * FROM parties WHERE leader_id=?",
                                     (party_leader_id_tuple[0],)).fetchone()

        party = classes.Party.from_tuple(party_tuple, member.guild)

        if (party.autowarp and
                member.id == party.leader_id):
            await party.warp(after.channel)

    @commands.command(name='modifypartygames')
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_1P5_COOLDOWN
    async def modifypartygames(self, ctx: commands.Context, player: converters.PlayerConverter = parameters.PLAYER_DATA, amount: int = parameters.parameter(displayed_name='Amount',)):
        db, cursor = functions.database(ctx.guild.id)
        player: discord.Member

        player_party_count_data = cursor.execute("SELECT * FROM party_games WHERE player_id=?",
                                                 (player.id, )).fetchone()
        if player_party_count_data is None:
            player_party_count_data = player.id, 0
            cursor.execute("INSERT INTO party_games VALUES (?, ?)",
                           player_party_count_data)
            db.commit()

        if player_party_count_data[1] + amount < 0:
            amount = -player_party_count_data[1]

        old_party_games_amount = player_party_count_data[1]
        new_party_games_amout = player_party_count_data[1] + amount

        cursor.execute("UPDATE party_games SET games_count=? WHERE player_id=?",
                       (new_party_games_amout, player.id))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                '',
                f'Updated {player.mention}\'s party games\n'
                f'{old_party_games_amount} ➜ {new_party_games_amout}'
            )
        )


    @commands.group(name="party")
    async def party(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            if not checks.check_cmd_permission(ctx.author, 'party invite', ctx.bot):
                raise errors.NoCommandPermission(ctx)
            
            ctx.message.content = ctx.message.content.replace('party', 'party invite', 1)

            await ctx.bot.process_commands(ctx.message)
        else:
            if not checks.check_cmd_permission(ctx.author, 'party ' + ctx.invoked_subcommand.name, ctx.bot):
                raise errors.NoCommandPermission(ctx)

    @party.command(name="invite", description="Invites a player to a party")
    async def party_invite(self, ctx: commands.Context,
                           invited_member: converters.PlayerConverter = parameters.PLAYER_DATA):
        p_limit = functions.party_limit_for(ctx.author)

        if p_limit == -1:
            raise errors.PartyError("Parties are disabled.")

        db, cursor = functions.database(ctx.guild.id)

        party_leader_id_tuple = cursor.execute("SELECT leader_id FROM party_members WHERE member_id=?",
                                               (ctx.author.id,)).fetchone()
        party = None

        if party_leader_id_tuple is None:
            party_tuple = (
                ctx.author.id,
                '',
                datetime.datetime.now().timestamp().__int__(),
                datetime.datetime.now().timestamp().__int__(),
                0,
                p_limit
            )
            cursor.execute("INSERT INTO parties VALUES (?, ?, ?, ?, ?, ?)",
                           party_tuple)
            db.commit()
            cursor.execute("INSERT INTO party_members VALUES (?, ?)",
                           (ctx.author.id, ctx.author.id))
            db.commit()
            party = classes.Party.from_tuple(party_tuple, ctx.guild)
        else:
            party = classes.Party.from_leader_id(party_leader_id_tuple[0], ctx.guild)

        if ctx.author.id != party.leader_id:
            raise errors.PartyError("You are not The Party Leader!")

        if invited_member.id == ctx.author.id:
            raise errors.PartyError("You cannot invite yourself.")

        if checks.check_if_in_party(invited_member.id, ctx.guild):
            raise errors.PartyError(f"{invited_member.mention} is already in a party.")

        if party.party_limit == len(party):
            raise errors.PartyError(f"<@{ctx.author.id}>, \n"
                                    f"You cannot invite more players since you already have the maximum amount "
                                    f"of people in your party.")

        if checks.check_party_ignored(ctx.author.id, invited_member.id, ctx.guild):
            raise errors.PartyError(f"{ctx.author.mention}, \n"
                                    f"You have been party ignored by {invited_member.mention}. "
                                    f"Hence you cannot invite them.")
        if not [t.id for t in ctx.author.roles if t.id in functions.get_info_value("PERMENANTPARTYROLESIDS", ctx.guild)] and functions.party_games_left(ctx.author.id, ctx.guild) <= 0:
            raise errors.PartyError("You don't have party games anymore")

        invited_member_tuple = (ctx.author.id,
                                invited_member.id,
                                (datetime.datetime.now() + datetime.timedelta(seconds=60)).timestamp().__int__())

        cursor.execute("INSERT INTO party_invites VALUES (?, ?, ?)",
                       invited_member_tuple)
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        invited_message = await webhook.send(
            content=invited_member.mention,
            embed=functions.embed(
                ctx.guild,
                "Party Invitation",
                f"{ctx.author.mention} invited you to their party, you have **60 Seconds** to accept.",
                embed_timestamp=True
            ), wait=True
        )

        await invited_message.add_reaction('🟩')
        await invited_message.add_reaction('🟥')

        def reaction_check(__r: discord.Reaction, __u: discord.User):
            if __r.message.id != invited_message.id:
                return False
            if __u.id != invited_member.id:
                return False
            if __r.emoji.__str__() != '🟩' and __r.emoji.__str__() != '🟥':
                return False

            asyncio.create_task(__r.remove(__u))

            return True

        try:
            reaction, user = await ctx.bot.wait_for('reaction_add', timeout=60, check=reaction_check)

            if reaction.emoji.__str__() == '🟥':
                await invited_message.edit(embed=functions.embed(
                    ctx.guild,
                    "Party Invitation",
                    f"{invited_member.mention} denied party invitation from {ctx.author.mention}.",
                    embed_timestamp=True,
                    embed_color='ERROR'
                ))
                cursor.execute("DELETE FROM party_invites WHERE leader_id=? AND invited_member_id=? AND expires_at=?",
                               invited_member_tuple)
                db.commit()
                await party.disband_if_possible(ctx.bot)
                await invited_message.clear_reactions()
                return

            await party.add_party_member(invited_member.id, ctx.bot)

            await invited_message.edit(
                embed=functions.embed(
                    ctx.guild,
                    "Party System",
                    f"You've joined {ctx.author.mention}s' team!",
                    embed_timestamp=True,
                    embed_color="ALTERNATIVE"
                )
            )
            cursor.execute("DELETE FROM party_invites WHERE leader_id=? AND invited_member_id=? AND expires_at=?",
                           invited_member_tuple)
            db.commit()
            await invited_message.clear_reactions()

        except asyncio.TimeoutError:

            await invited_message.edit(embed=functions.embed(
                ctx.guild,
                "Party Invitation",
                f"The party invitation from {ctx.author.mention} has expired!\n\n"
                f"You may run `=party ignore {ctx.author.name}` to ignore future invites from {ctx.author.mention}.",
                embed_timestamp=True,
                embed_color='ERROR'
            ))

            cursor.execute("DELETE FROM party_invites WHERE leader_id=? AND invited_member_id=? AND expires_at=?",
                           invited_member_tuple)
            db.commit()

            await party.disband_if_possible(ctx.bot)

            await invited_message.clear_reactions()
            return

    @party.command(name="leave", description="Leaves The Party you are in")
    async def party_leave(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        party_leader_id_tuple = cursor.execute("SELECT leader_id FROM party_members WHERE member_id=?",
                                               (ctx.author.id,)).fetchone()
        if party_leader_id_tuple is None:
            raise errors.PartyError(f"You are not in a party.")

        party_tuple = cursor.execute("SELECT * FROM parties WHERE leader_id=?",
                                     (party_leader_id_tuple[0],)).fetchone()

        party = classes.Party.from_tuple(party_tuple, ctx.guild)

        await party.remove_party_member(ctx.author.id, ctx.bot)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(ctx.guild,
                                  "Party System",
                                  f"You left <@{party_leader_id_tuple[0]}>s' party.")
        )

    @party.command(name="list", description="Shows Your/Someone 's party")
    async def party_list(self, ctx: commands.Context, member: converters.PlayerConverter = parameters.PLAYER_DATA_OPTIONAL):
        player = member or ctx.author

        db, cursor = functions.database(ctx.guild.id)

        party_leader_id_tuple = cursor.execute("SELECT leader_id FROM party_members WHERE member_id=?",
                                               (player.id,)).fetchone()
        if party_leader_id_tuple is None:
            raise errors.PartyError(f"{player.mention} is not in a party.")

        party_tuple = cursor.execute("SELECT * FROM parties WHERE leader_id=?",
                                     (party_leader_id_tuple[0],)).fetchone()

        party = classes.Party.from_tuple(party_tuple, ctx.guild)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=self.party_embed(party)
        )

    @party.command(name="accept", description="Accepts A Party Invite")
    async def party_accept(self, ctx: commands.Context, leader: converters.PlayerConverter = parameters.PLAYER_DATA):
        db, cursor = functions.database(ctx.guild.id)

        if cursor.execute("SELECT * FROM party_invites WHERE leader_id=? AND invited_member_id=?",
                                            (leader.id, ctx.author.id)).fetchone() is None:
            raise errors.PartyError("You have no pending invite from {0.mention}.".format(
                leader
            ))

        party = classes.Party.from_leader_id(leader.id, ctx.guild)

        await party.add_party_member(ctx.author.id)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Party System",
                f"You've joined {ctx.author.mention}s' team!",
                embed_timestamp=True,
                embed_color="ALTERNATIVE"
            )
        )

    @party.command(name="disband", description="Disbands Your Party (Must Be a Leader)")
    async def party_disband(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        party_leader_id_tuple = cursor.execute("SELECT leader_id FROM party_members WHERE member_id=?",
                                               (ctx.author.id,)).fetchone()
        if party_leader_id_tuple is None:
            raise errors.PartyError(f"You are not in a party.")

        party_tuple = cursor.execute("SELECT * FROM parties WHERE leader_id=?",
                                     (party_leader_id_tuple[0],)).fetchone()

        party = classes.Party.from_tuple(party_tuple, ctx.guild)

        if party.leader_id != ctx.author.id:
            raise errors.PartyError("You are not The Party Leader!")

        await party.disband(ctx.bot)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Party System",
                "You have successfully disbanded the party."
            )
        )

    @party.command(name="autowarp", description='Toggles autowarping to VCs, must be a party leader')
    async def party_autowarp(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        party_leader_id_tuple = cursor.execute("SELECT leader_id FROM party_members WHERE member_id=?",
                                               (ctx.author.id,)).fetchone()
        if party_leader_id_tuple is None:
            raise errors.PartyError(f"You are not in a party.")

        party_tuple = cursor.execute("SELECT * FROM parties WHERE leader_id=?",
                                     (party_leader_id_tuple[0],)).fetchone()

        party = classes.Party.from_tuple(party_tuple, ctx.guild)

        if party.leader_id != ctx.author.id:
            raise errors.PartyError("You are not The Party Leader!")

        party.autowarp = True if not party.autowarp else False

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "",
                "Party autowarping is now `{}`".format('ON' if party.autowarp else 'OFF')
            )
        )

    @party.command(name="warp", description="Warps Party Members")
    async def party_warp(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        party_leader_id_tuple = cursor.execute("SELECT leader_id FROM party_members WHERE member_id=?",
                                               (ctx.author.id,)).fetchone()
        if party_leader_id_tuple is None:
            raise errors.PartyError(f"You are not in a party.")

        party_tuple = cursor.execute("SELECT * FROM parties WHERE leader_id=?",
                                     (party_leader_id_tuple[0],)).fetchone()

        party = classes.Party.from_tuple(party_tuple, ctx.guild)

        if party.leader_id != ctx.author.id:
            raise errors.PartyError("You are not The Party Leader!")

        if ctx.author.voice is None:
            raise errors.PartyError("You are not in a VoiceChannel.")

        await party.warp(ctx.author.voice.channel)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "",
                "You've warped your party to {}".format(ctx.author.voice.channel.jump_url)
            )
        )

    @party.command(name="kick", description="Kicks A Player From Your Party(Must Be a Leader)")
    async def party_kick(self, ctx: commands.Context,
                         kicked_member: converters.PlayerConverter = parameters.PLAYER_DATA):
        db, cursor = functions.database(ctx.guild.id)

        party_leader_id_tuple = cursor.execute("SELECT leader_id FROM party_members WHERE member_id=?",
                                               (ctx.author.id,)).fetchone()
        if party_leader_id_tuple is None:
            raise errors.PartyError(f"You are not in a party.")

        party_tuple = cursor.execute("SELECT * FROM parties WHERE leader_id=?",
                                     (party_leader_id_tuple[0],)).fetchone()

        party = classes.Party.from_tuple(party_tuple, ctx.guild)

        if party.leader_id != ctx.author.id:
            raise errors.PartyError("You are not The Party Leader!")

        await party.remove_party_member(kicked_member.id, ctx.bot)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "",
                "You have kicked {0.mention} from your party.".format(kicked_member)
            )
        )

    @party.command(name="ignore", description="Ignores Player's Invites")
    async def party_ignore(self, ctx: commands.Context,
                           ignored_member: converters.MemberUserConverter = parameters.PLAYER_DATA):
        db, cursor = functions.database(ctx.guild.id)

        party_ignore_list_tuple = cursor.execute("SELECT ignoredlist FROM party_ignore_lists WHERE member_id=?",
                                                 (ctx.author.id,)).fetchone()
        party_ignore_list = []

        if party_ignore_list_tuple is None:
            cursor.execute("INSERT INTO party_ignore_lists VALUES (?, ?)",
                           (ctx.author.id, ''))
            db.commit()
        else:
            party_ignore_list = [int(t) for t in party_ignore_list_tuple[0].split(",")] if \
                party_ignore_list_tuple[0] != '' else []

        if ignored_member.id in party_ignore_list:
            raise errors.PartyError(f'{ignored_member.mention} is already in your ignore list.')

        party_ignore_list.append(ignored_member.id)

        cursor.execute("UPDATE party_ignore_lists SET ignoredlist=? WHERE member_id=?",
                       (','.join([str(t) for t in party_ignore_list]), ctx.author.id))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "",
                f"Added {ignored_member.mention} to your ignore list."
            )
        )

    @party.command(name="unignore", description="Unignores Player's Invites")
    async def party_unignore(self, ctx: commands.Context,
                             unignored_member: converters.MemberUserConverter = parameters.PLAYER_DATA):
        db, cursor = functions.database(ctx.guild.id)

        party_ignore_list_tuple = cursor.execute("SELECT ignoredlist FROM party_ignore_lists WHERE member_id=?",
                                                 (ctx.author.id,)).fetchone()
        party_ignore_list = []

        if party_ignore_list_tuple is None:
            cursor.execute("INSERT INTO party_ignore_lists VALUES (?, ?)",
                           (ctx.author.id, ''))
            db.commit()
        else:
            party_ignore_list = [int(t) for t in party_ignore_list_tuple[0].split(",")] if \
                party_ignore_list_tuple[0] != '' else []

        if unignored_member.id not in party_ignore_list:
            raise errors.PartyError(f'{unignored_member.mention} is not in your ignore list.')

        party_ignore_list.remove(unignored_member.id)

        cursor.execute("UPDATE party_ignore_lists SET ignoredlist=? WHERE member_id=?",
                       (','.join([str(t) for t in party_ignore_list]), ctx.author.id))
        db.commit()

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "",
                f"Removed {unignored_member.mention} from your ignore list."
            )
        )

    @party.command(name="ignorelist", aliases=['ignored', 'il'], description="Shows your party ignore list")
    async def party_ignorelist(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        party_ignore_list_tuple = cursor.execute("SELECT ignoredlist FROM party_ignore_lists WHERE member_id=?",
                                                 (ctx.author.id,)).fetchone()
        party_ignore_list = []

        if party_ignore_list_tuple is None:
            cursor.execute("INSERT INTO party_ignore_lists VALUES (?, ?)",
                           (ctx.author.id, ''))
            db.commit()
        else:
            party_ignore_list = [int(t) for t in party_ignore_list_tuple[0].split(",")] if \
                party_ignore_list_tuple[0] != '' else []

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                f"{ctx.author.name}s' ignore list",
                "No one" if party_ignore_list == [] else \
                "\n".join(f'- <@{t}>' for t in party_ignore_list)
            )
        )

    @party.command(name="invites", description="Displays Incoming and Outgoing Invites")
    async def party_invites(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        pending_incoming_party_invites_tuple_list = cursor.execute(
            "SELECT * FROM party_invites WHERE invited_member_id=?",
            (ctx.author.id,)).fetchall()

        embed_description = "**Incoming Invites**\n"
        if pending_incoming_party_invites_tuple_list == []:
            embed_description += "No Invites\n\n"
        else:
            for leader_id, *_ in pending_incoming_party_invites_tuple_list:
                embed_description += "- <@{}>\n".format(leader_id)
            embed_description += "\n"

        pending_outgoing_party_invites_tuple_list = cursor.execute("SELECT * FROM party_invites WHERE leader_id=?",
                                                                   (ctx.author.id,)).fetchall()

        embed_description += "**Outgoing Invites**\n"
        if pending_outgoing_party_invites_tuple_list == []:
            embed_description += "No Invites"
        else:
            for _, invited_member_id, _ in pending_outgoing_party_invites_tuple_list:
                embed_description += "- <@{}>\n".format(invited_member_id)

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Party System",
                embed_description
            )
        )

    @commands.command(name="partylist", aliases=["pl"], description="Shows Your/Someone 's party")
    @discordchecks.check_command_permission('party')
    async def partylist(self, ctx: commands.Context, member: converters.PlayerConverter = parameters.PLAYER_DATA_OPTIONAL):
        ctx.message.content = ctx.message.content.replace('partylist', 'party list')
        ctx.message.content = ctx.message.content.replace('pl', 'party list')
        await ctx.bot.process_commands(ctx.message)

    @staticmethod
    def party_embed(party: classes.Party):
        return functions.embed(
            party.guild,
            "Party System",
            f"**Created:** {functions.approximate_duration(datetime.datetime.now().timestamp() - party.created_at)} ago\n"
            f"**Idle time:** {functions.approximate_duration(datetime.datetime.now().timestamp() - party.lastqueued)}\n"
            f"**Auto Warp:** {'On' if party.autowarp else 'Off'}\n"
            f"**Members** [`{len(party)}`/`{party.party_limit}`]:\n"
            f"* <@{party.leader_id}>\n" +
            '\n'.join([f'  - <@{t}>' for t in party.members_ids])
        )

    @tasks.loop(minutes=1)
    async def check_parties(self):
        for guild in self.bot.guilds:
            db, cursor = functions.database(guild.id)
            for party_tuple in cursor.execute("SELECT * FROM parties").fetchall():
                party = classes.Party.from_tuple(party_tuple, guild)
                await party.disband_if_possible(self.bot)

    @check_parties.before_loop
    async def before_check_parties(self):
        await self.bot.wait_until_ready()

    async def check_party_invites(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            db, cursor = functions.database(guild.id)
            cursor.execute("DELETE FROM party_invites")
            db.commit()

    async def cog_load(self) -> None:
        self.check_parties.start()
        asyncio.create_task(self.check_party_invites())

    async def cog_unload(self) -> None:
        pass

    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        await functions.error_handler(ctx, error, traceback.format_exc())


async def setup(bot: commands.Bot):
    await bot.add_cog(Party(bot))
