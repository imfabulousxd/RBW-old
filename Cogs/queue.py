import asyncio
import datetime
import glob
import io
import traceback
from typing import Union, Optional, Any

import discord
from discord import Interaction
from discord._types import ClientT
from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord.ext.commands._types import BotT
from discord.ui import Item

import errors
import parameters
from Cooldowns import usercooldown, channelcooldown
from Functions import functions, gamefunctions

from Checks import checks, discordchecks
import classes


class Queue(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "Queue"
        self.emoji = "▶️"
        self.description = "Queue Commands."

    @commands.command(
        name="screenshot",
        aliases=['score', 'save', 'store', 'submit'],
        description="Submits a screenshot of the winning screen",
        extras={"group": "QUEUE"}
    )
    @discordchecks.check_command_permission()
    @discordchecks.game_channel_check()
    @discordchecks.guild_command_check()
    @commands.core.cooldown(1, 30, commands.BucketType.channel)
    async def screenshot(self, ctx: commands.Context, *, image: str = parameters.ATTACHMENT):
        ctx.message = await ctx.channel.fetch_message(ctx.message.id)

        if len(ctx.message.embeds) + len(ctx.message.attachments) == 0:
            ctx.command.reset_cooldown(ctx)
            raise errors.NoImageAttached()
        elif len(ctx.message.embeds) + len(ctx.message.attachments) > 1:
            ctx.command.reset_cooldown(ctx)
            raise errors.CommandsError("You cannot attach more than one image.")

        game = classes.Game.from_game_tc(ctx.channel, ctx.bot)

        if game.can_be_submitted() is False:
            ctx.command.reset_cooldown(ctx)
            raise errors.QueueError("You cannot submit this game in its' current state.")

        image_url = ctx.message.embeds[0].url if len(ctx.message.embeds) > 0 else \
            ctx.message.attachments[0].url

        # image_bytes, image_type = await functions.get_image_bytes_from_url(image_url)
        # image_file = discord.File(fp=io.BytesIO(image_bytes), filename=f"game-{game.game_id}.{image_type}")

        webhook = await game.fetch_webhook()

        confirming_message = await webhook.send(
            content=f"{ctx.author.mention}, \n"
                    f"After making sure this is the right screenshot "
                    f"type `c` to confirm.\n\n"
                    f"URL: {image_url}",
            wait=True
        )

        def check_if_confirmed(message: discord.Message):
            return (message.author.id == ctx.author.id and
                    message.content == "c" and
                    message.channel.id == ctx.channel.id)

        try:
            await ctx.bot.wait_for('message', check=check_if_confirmed, timeout=30)

            db, cursor = functions.database(ctx.guild.id)

            cursor.execute("INSERT INTO game_screenshots VALUES (?, ?, ?)",
                           (game.game_id, image_url, ctx.author.id))
            db.commit()

            game.status = "SUBMITTED"

            game.update_db()

            await game.sequence_cleaner()

        except asyncio.TimeoutError:
            ctx.command.reset_cooldown(ctx)

    @commands.command(name="queue", aliases=["q"], description="Displays the current state of a Queue")
    @discordchecks.check_command_permission()
    @discordchecks.game_channel_check()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def queue(self, ctx: commands.Context):
        game = classes.Game.from_game_tc(ctx.channel, ctx.bot)

        await game.fetch_webhook()

        await game.webhook.send(
            embed=game.game_embed()
        )

    @commands.command(name="queuestats", aliases=["qs"], description="Displays the Queue players' stats")
    @discordchecks.check_command_permission()
    @discordchecks.game_channel_check()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def queuestats(self, ctx: commands.Context):
        game = classes.Game.from_game_tc(ctx.channel, ctx.bot)

        players_stats = []
        for player_id in game.team1_players_ids + game.team2_players_ids + game.remaining_players_ids:
            player = classes.NewPlayer.from_player_id(player_id, ctx.guild)
            players_stats.append(
                # f"`{player.wins:<3} Wins` "
                # f"`{player.losses:<3} Losses` "
                # f"`{player.mvps:<3} MVPs` "
                # f"`{player.wins / (player.losses if player.losses != 0 else 1):<6.2f} WLR` "
                # f"<@{player.player_id}>"
                "`{:<8}` `{:<10}` `{:<8}` `{:<10}` <@{}>".format(
                    f"{player.wins} Wins",
                    f"{player.losses} Losses",
                    f"{player.mvps} MVPs",
                    f"{player.wlr:.2f} WLR",
                    player.player_id
                )
            )

        await game.fetch_webhook()

        await game.webhook.send(
            embed=functions.embed(
                ctx.guild,
                embed_description='\n'.join(players_stats)
            )
        )

    @commands.command(name="void", aliases=["v"], description="Makes a void requset for a game")
    @discordchecks.check_command_permission()
    @discordchecks.game_channel_check()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    @channelcooldown.SEC30
    async def void(self, ctx: commands.Context):
        game = classes.Game.from_game_tc(ctx.channel, ctx.bot)

        if game.status not in ["PLAYING", "PICKING"]:
            raise errors.QueueError("You cannot void this game in its' current state")

        await game.fetch_webhook()

        void_message = await game.webhook.send(
            embed=functions.embed(
                ctx.guild,
                "",
                "React 🟩 to void this game."
            ),
            wait=True
        )

        await void_message.add_reaction('🟩')

        try:
            while 1:
                reaction, user = await ctx.bot.wait_for('reaction_add', timeout=30)

                if reaction.message.id != void_message.id:
                    continue

                if reaction.emoji.__str__() != '🟩':
                    continue

                if user.id in game.players_ids:
                    pass
                else:
                    await reaction.remove(user)
                    continue

                if (reaction.count - 1) > len(game.players_ids) / 2:
                    break
                else:
                    continue

        except asyncio.TimeoutError:
            await void_message.edit(
                embed=functions.embed(
                    ctx.guild,
                    "",
                    f"Voiding the game has been cancelled.",
                    embed_color='ERROR'
                ))
            await void_message.clear_reactions()
            return

        await game.void_game(ctx.author, "Game Voiding")

    @commands.command(name="forcevoid", aliases=["fv"], description="Forcefully void the game")
    @discordchecks.check_command_permission()
    @discordchecks.game_channel_check()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def forcevoid(self, ctx: commands.Context, *, reason: str = parameters.REASON):
        game = classes.Game.from_game_tc(ctx.channel, ctx.bot)

        await game.void_game(ctx.author, reason)

    @commands.command(name="pick", aliases=["p"], description="Picks a Player, Only used By Team Captains")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def pick(self, ctx: commands.Context, *, members_data: str = parameters.PLAYER_DATA):
        db, cursor = functions.database(ctx.guild.id)

        if cursor.execute("SELECT * FROM games WHERE game_tc_id=?",
                          (ctx.channel.id,)).fetchone() is None:
            if ctx.invoked_with == 'p':
                ctx.message.content = ctx.message.content.replace("p", "party", 1)
                await ctx.bot.process_commands(ctx.message)
                return
            else:
                raise errors.DontRespond()

        game = classes.Game.from_game_tc(ctx.channel, ctx.bot)

        if game.status != "PICKING" and ctx.invoked_with == 'p':
            ctx.message.content = ctx.message.content.replace("p", "party", 1)
            await ctx.bot.process_commands(ctx.message)
            return


        if game.status != "PICKING":
            raise errors.QueueError(f"You cannot pick players in the games' current state.")

        picking_team = 0

        if ctx.author.id == game.team1_players_ids[0]:
            picking_team = 1
        elif ctx.author.id == game.team2_players_ids[0]:
            picking_team = 2
        else:
            raise errors.QueueError(f"{ctx.author.mention}, You are not a captain.")

        pick_turn = game.pick_turn()

        if picking_team != pick_turn:
            raise errors.QueueError(f"{ctx.author.mention}, its not your turn to pick.")

        picked_members_ids = []

        members_data_split = members_data.split(" ")

        picks_count_allowed = abs(len(game.team1_players_ids) - len(game.team2_players_ids)) + 1

        if len(members_data_split) > picks_count_allowed:
            raise errors.QueueError(f"{ctx.author.mention}, You picked more than you were supposed to.")

        for member_data in members_data_split:
            picked_member = await functions.fetch_member(member_data, ctx.guild)
            if picked_member.id not in game.players_ids:
                raise errors.QueueError(f"{ctx.author.mention}, you cannot pick {picked_member.mention}"
                                        f" since hes not even in this queue.")
            elif picked_member.id not in game.remaining_players_ids:
                raise errors.QueueError(f"{ctx.author.mention}, you cannot pick {picked_member.mention}"
                                        f" since hes already in a team")
            picked_members_ids.append(picked_member.id)

        if picking_team == 1:
            game.team1_players_ids.extend(picked_members_ids)
            for picked_member_id in picked_members_ids:
                game.remaining_players_ids.remove(picked_member_id)
        else:
            game.team2_players_ids.extend(picked_members_ids)
            for picked_member_id in picked_members_ids:
                game.remaining_players_ids.remove(picked_member_id)

        game.update_db()

        game.update_pick_turn()

        await game.fetch_webhook()

        if len(game.team1_players_ids) == game.queue.player_count/2 or len(game.team2_players_ids) == game.queue.player_count/2:
            # Start self
            if len(game.team1_players_ids) == game.queue.player_count/2:
                game.team2_players_ids.extend(game.remaining_players_ids)
                game.remaining_players_ids.clear()
            else:
                game.team1_players_ids.extend(game.remaining_players_ids)
                game.remaining_players_ids.clear()

            game.update_db()

            await gamefunctions.start_game(game)

            if not game.ranked:
                await game.void_game(ctx.bot.user, "Casual game", duration=45 * 60)
        else:
            await game.webhook.send(
                embed=game.game_embed()
            )

            await game.webhook.send(
                embed=functions.embed(
                    ctx.guild,
                    "",
                    f"{ctx.author.mention}, You have {picks_count_allowed - len(picked_members_ids)} "
                    f"pick{'s' if picks_count_allowed - len(picked_members_ids) != 1 else ''} left."
                )
            )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        # Check if member left a queue
        if before.channel is not None:
            db, cursor = functions.database(member.guild.id)

            queue_tuple = cursor.execute("SELECT * FROM queues WHERE queue_vc_id=?",
                                         (before.channel.id,)).fetchone()

            if queue_tuple is not None:
                queue = classes.Queue.from_tuple(queue_tuple, member.guild)

                queue.remove_queue_player(member.id)

        # Check if member joined a queue
        if after.channel is not None:
            db, cursor = functions.database(member.guild.id)

            queue_tuple = cursor.execute("SELECT * FROM queues WHERE queue_vc_id=?",
                                         (after.channel.id,)).fetchone()

            if queue_tuple is not None:
                queue = classes.Queue.from_tuple(queue_tuple, member.guild)

                if checks.check_if_member_can_queue(member, queue):
                    queue.add_queue_player(member.id)

                # Check self can start
                await gamefunctions.start_game_if_possible(queue, self.bot)

    @tasks.loop(count=1)
    async def load_queue_players_after_restart(self):
        for guild in self.bot.guilds:
            try:
                db, cursor = functions.database(guild.id)
                for queue_tuple in cursor.execute("SELECT * FROM queues").fetchall():
                    queue = classes.Queue.from_tuple(queue_tuple, guild)
                    queue_vc = await guild.fetch_channel(queue.vc_id)

                    for queue_player_id in queue.queue_players_ids():
                        if queue_player_id not in [t.id for t in queue_vc.members]:
                            queue.remove_queue_player(queue_player_id)

                    queue_players_ids = queue.queue_players_ids()

                    for queue_player in queue_vc.members:
                        if checks.check_if_member_can_queue(queue_player, queue) and queue_player.id not in queue_players_ids:
                            queue.add_queue_player(queue_player.id)

                    await gamefunctions.start_game_if_possible(queue, self.bot)

            except:
                pass

    @load_queue_players_after_restart.before_loop
    async def before_load_queue_players_after_restart(self):
        await self.bot.wait_until_ready()

    async def cog_load(self) -> None:
        self.load_queue_players_after_restart.start()
    
    async def cog_unload(self) -> None:
        pass

    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        await functions.error_handler(ctx, error, traceback.format_exc(), game_channel=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Queue(bot))
