import traceback

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands._types import BotT

import classes
import errors
import parameters
from Checks import discordchecks
from Cooldowns import usercooldown
from Functions import functions


class Matchmaking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "Matchmaking"
        self.emoji = "⚔️"
        self.description = "Matchmaking-related commands"

    @commands.command(name="call", aliases=["c"],description="Grants Player access to the team call belongs to the invoker")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def call(self, ctx: commands.Context, member_data: str = parameters.PLAYER_DATA):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            raise errors.MatchmakingError("You must be in a Voice channel in order to use this command.")

        db, cursor = functions.database(ctx.guild.id)

        team_vc_id_tuple = cursor.execute("SELECT * FROM games WHERE team1_vc_id=? OR team2_vc_id=?",
                                          (ctx.author.voice.channel.id, ctx.author.voice.channel.id)).fetchone()

        called_member = await functions.fetch_member(member_data, ctx.guild)

        if team_vc_id_tuple is None:
            raise errors.MatchmakingError("You must be in a Team VC in order to use this command.")

        await ctx.author.voice.channel.set_permissions(
            called_member, connect=True, speak=False
        )

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                '',
                f"Gave {called_member.mention} access to {ctx.author.voice.channel.mention}.",
                embed_footer_text=f"Invoked by {ctx.author.name}"
            )
        )

    @commands.command(name="callremove", aliases=["cr"], description="Removes Player access to the team call belongs to the invoker")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def callremove(self, ctx: commands.Context, member_data: str = parameters.PLAYER_DATA):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            raise errors.MatchmakingError("You must be in a Voice channel in order to use this command.")

        db, cursor = functions.database(ctx.guild.id)

        team_vc_id_tuple = cursor.execute("SELECT * FROM games WHERE team1_vc_id=? OR team2_vc_id=?",
                                          (ctx.author.voice.channel.id, ctx.author.voice.channel.id)).fetchone()

        called_member = await functions.fetch_member(member_data, ctx.guild)

        if team_vc_id_tuple is None:
            raise errors.MatchmakingError("You must be in a Team VC in order to use this command.")

        game = classes.Game.from_tuple(team_vc_id_tuple, ctx.guild, ctx.bot)

        if (
                ctx.author.id in game.team1_players_ids and called_member.id in game.team1_players_ids or
                ctx.author.id in game.team2_players_ids and called_member.id in game.team2_players_ids
        ):
            raise errors.MatchmakingError(f"You cannot remove {called_member.mention}s' access from this channel.")

        await ctx.author.voice.channel.set_permissions(
            called_member, connect=False
        )

        if called_member.voice is not None and called_member.voice.channel == ctx.author.voice.channel:
            try:
                await called_member.edit(
                    voice_channel=None
                )
            except discord.HTTPException:
                pass

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                '',
                f"Removed {called_member.mention}s' access to {ctx.author.voice.channel.mention}.",
                embed_footer_text=f"Invoked by {ctx.author.name}"
            )
        )

    @commands.command(name="queues", description="Shows all available queues")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def queues(self, ctx: commands.Context):
        db, cursor = functions.database(ctx.guild.id)

        queues_list_tuple = cursor.execute("SELECT * FROM queues").fetchall()
        queues = []
        for i, queue_tuple in enumerate(queues_list_tuple):
            queues.append(f"{i+1}. https://discord.com/channels/{ctx.guild.id}/{queue_tuple[0]} | "
                          f"Min ELO: {queue_tuple[4]} | Max ELO: {queue_tuple[5]}")

        webhook = await functions.fetch_webhook(ctx.channel, ctx.bot)

        await webhook.send(
            embed=functions.embed(
                ctx.guild,
                "Available Queues",
                "\n".join(queues)
            )
        )

    async def cog_load(self) -> None:
        pass

    async def cog_unload(self) -> None:
        pass

    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        await functions.error_handler(ctx, error, traceback.format_exc())


async def setup(bot: commands.Bot):
    await bot.add_cog(Matchmaking(bot))
