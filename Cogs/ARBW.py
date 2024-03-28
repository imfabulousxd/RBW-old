import traceback

from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands._types import BotT

import classes
import errors
from Checks import discordchecks
from Cooldowns import usercooldown
from Functions import functions


class Custom(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "Custom"
        self.emoji = "⛄"
        self.description = "Custom commands"

    @commands.command(name="claimelo")
    @discordchecks.check_command_permission()
    @discordchecks.guild_command_check()
    @usercooldown.USER_5P10_COOLDOWN
    async def claimelo(self, ctx: commands.Context):
        # TODO: do this urself if u want it
        ...

    async def cog_load(self) -> None:
        pass

    async def cog_unload(self) -> None:
        pass

    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        await functions.error_handler(ctx, error, traceback.format_exc())


async def setup(bot: commands.Bot):
    await bot.add_cog(Custom(bot))
