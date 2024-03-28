import asyncio
import functools
import json
import logging
import sys
import traceback

import aiohttp
from discord import app_commands
from discord.ext import commands, tasks
import discord
from discord.ext.commands import Context

from Checks import appcommand_checks
from Functions import functions

logger = logging.getLogger(__name__)


class Voting(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.show_help = False

    @app_commands.command(name="voting")
    @app_commands.guild_only
    @appcommand_checks.check_command_permission()
    @app_commands.describe(member="Member",
                           group_name="Group name")
    @app_commands.choices(
        group_name=[
            app_commands.Choice(name="PUPs", value="PUPs"),
            app_commands.Choice(name="PUGs", value="PUGs"),
            app_commands.Choice(name="Premium", value="Premium")
        ]
    )
    async def voting(self, interaction: discord.Interaction,
                     group_name: str,
                     member: discord.Member):
        interaction.response: discord.InteractionResponse
        await interaction.response.defer(thinking=True, ephemeral=True)

        await interaction.edit_original_response(
            embed=functions.embed(
                interaction.guild,
                embed_description="Fetching webhook..."
            )
        )

        webhook = await functions.fetch_webhook(interaction.channel, interaction.client, webhook_name=group_name)

        await interaction.edit_original_response(
            embed=functions.embed(
                interaction.guild,
                embed_description="Sending the message..."
            )
        )

        voting_message = await webhook.send(
            embed=functions.embed(
                interaction.guild,
                embed_description=f"{group_name} Voting for {member.mention} has started.",
                embed_author_name=member.name,
                embed_author_icon_url=member.display_avatar.url
            ),
            wait=True
        )

        await interaction.edit_original_response(
            embed=functions.embed(
                interaction.guild,
                embed_description="Adding reactions..."
            )
        )

        await voting_message.add_reaction('🟩')
        await voting_message.add_reaction('🟥')

        await interaction.edit_original_response(
            embed=functions.embed(
                interaction.guild,
                embed_description="Done!"
            )
        )

    async def cog_load(self) -> None:
        pass

    async def cog_unload(self) -> None:
        pass

    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        await functions.error_handler(ctx, error, traceback.format_exc())


async def setup(bot: commands.Bot):
    await bot.add_cog(Voting(bot))
