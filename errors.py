import typing

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from Functions import functions


class DefaultError(commands.CommandError, app_commands.CommandInvokeError):
    def __init__(self, embed_title: str,
                 embed_description: str):
        self.embed_title = embed_title
        self.embed_description = embed_description


class ModerationError(DefaultError):
    def __init__(self, error_message: str):
        self.embed_title = "Moderation System"
        self.embed_description = error_message


class UnexpectedError(DefaultError):
    def __init__(self, error_message: str):
        self.embed_title = "Commands System"
        self.embed_description = error_message


class CommandsError(DefaultError):
    def __init__(self, error_message: str):
        self.embed_title = "Commands System"
        self.embed_description = error_message


class RoleNotFoundError(DefaultError):
    def __init__(self, role_data: str):
        self.embed_title = "Roles System"
        self.embed_description = f"Role({role_data}) not found."


class ChannelNotFoundError(DefaultError):
    def __init__(self, channel_data: str):
        self.embed_title = "Channels System"
        self.embed_description = f"Channel({channel_data}) not found."


class QueueError(DefaultError):
    def __init__(self, error_message: str):
        self.embed_title = "Queue System"
        self.embed_description = error_message


class InvalidSyntax(DefaultError):
    def __init__(self, syntax: str):
        self.embed_title = "Invalid Syntax"
        self.embed_description = syntax


class MemberNotFound(DefaultError):
    def __init__(self, member_data: str):
        self.embed_title = "Commands System"
        self.embed_description = f"Member({member_data}) not found."


class NoImageAttached(DefaultError):
    def __init__(self):
        self.embed_title = "Commands System"
        self.embed_description = f"No image attached."


class PlayerManagementError(DefaultError):
    def __init__(self, msg: str):
        self.embed_title = "Player Management System"
        self.embed_description = f"{msg}"


class DontRespond(DefaultError):
    def __init__(self):
        pass


class ScoringError(DefaultError):
    def __init__(self, err: str):
        self.embed_title = "Scoring System"
        self.embed_description = err


class RanksError(DefaultError):
    def __init__(self, err: str):
        self.embed_title = "Ranks System"
        self.embed_description = err


class MatchmakingError(DefaultError):
    def __init__(self, err: str):
        self.embed_title = "Matchmaking System"
        self.embed_description = err


class LeaderboardsError(DefaultError):
    def __init__(self, err: str):
        self.embed_title = "Leaderboards System"
        self.embed_description = err


class NoCommandPermission(DefaultError):
    def __init__(self, ctx: commands.Context):
        self.embed_title = "Commands System"

        new_cmd_name = ctx.command.name if ctx.invoked_subcommand is None else ctx.command.name + ' ' + ctx.invoked_subcommand.name

        self.embed_description = (f"{ctx.author.mention}, You are missing atleast one of these roles:\n"
                                  + "\n".join([f"<@&{t}>" for t in functions.get_command_roles(new_cmd_name, ctx.guild, ctx.bot)[0]]))


class MemberNotRegistered(DefaultError):
    def __init__(self, member_id: int):
        self.embed_title = "Registration System"
        self.embed_description = f"Member(<@{member_id}>) is not registered."


class GameDoesNotExist(DefaultError):
    def __init__(self, game_id: int):
        self.embed_title = "Queue System"
        self.embed_description = f"Game#{game_id} does not exist."


class PartyError(DefaultError):
    def __init__(self, err: str):
        self.embed_title = "Party System"
        self.embed_description = err
