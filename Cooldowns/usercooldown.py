import discord
from discord.ext import commands

USER_5P10_COOLDOWN = commands.cooldown(5, 10, commands.BucketType.user)

USER_1P5_COOLDOWN = commands.cooldown(1, 5, commands.BucketType.user)

USER_1P60_COOLDOWN = commands.cooldown(1, 60, commands.BucketType.user)
