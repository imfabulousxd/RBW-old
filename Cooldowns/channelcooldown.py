import discord
from discord.ext import commands

SEC30 = commands.cooldown(1, 30, commands.BucketType.channel)
