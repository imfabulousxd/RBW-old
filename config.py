from typing import Literal

import discord

ALL_INFO_NAMES_DICT = {
    "WEBHOOKIMAGEURL": [str],
    "WEBHOOKNAME": [str],
    "EMBEDCOLOR": [int, 16],
    "ALTERNATIVEEMBEDCOLOR": [int, 16],
    "EMBEDERRORCOLOR": [int, 16],
    "EMBEDFOOTERTEXT": [str],
    "EMBEDFOOTERICONURL": [str],
    "EMBEDIMAGEURL": [str],
    "EMBEDTHUMBNAILURL": [str],
    "CHANNELNAMEPREFIX": [str],
    "DEFAULTVCREGION": [str],
    "GAMESTARTEDEMBEDTITLE": [str],
    "GAMESTARTEDEMBEDDESCRIPTION": [str],
    "DEFAULTCARDNAME": [str],
    "WEEKLYLBRESET": [str],
    "DAILYLBRESET": [str],
    "RULES": [str],
    "2MEMBERPARTYLIMITROLESIDS": [str],
    "3MEMBERPARTYLIMITROLESIDS": [str],
    "4MEMBERPARTYLIMITROLESIDS": [str],
    "PERMENANTPARTYROLESIDS": [str],
}

ALL_INFO_NAMES_TUPLE = [INFO_NAME for INFO_NAME in ALL_INFO_NAMES_DICT]

ALL_INFO_NAMES_LITERAL = Literal[ALL_INFO_NAMES_TUPLE]

ERROR_COLOR = 0xe74d3c

ROLE_NAMES_TUPLE = (
    "REGISTERED",
    "SCREENSHARER",
    "SCORER",
    "FROZEN",
    "RANKEDBANNED",
    "MUTED",
    "VOICEMUTED"
)

ROLES_NAMES_LITERAL = Literal[ROLE_NAMES_TUPLE]

CHANNELS_NAMES_DICT = {
    "WAITINGROOM": [discord.VoiceChannel],
    "SCREENSHAREREQUESTSCATEGORY": [discord.CategoryChannel],
    "TEAMVCSCATEGORY": [discord.CategoryChannel],
    "GAMECHANNELSCATEGORY": [discord.CategoryChannel],
    "SCORING": [discord.TextChannel],
    "GAMETRANSCRIPTS": [discord.TextChannel],
    "SCORINGREPORTS": [discord.TextChannel],
    "RANKEDBANS": [discord.TextChannel],
    "MUTES": [discord.TextChannel],
    "VOICEMUTES": [discord.TextChannel],
    "STRIKES": [discord.TextChannel],
    "PARTYALERTS": [discord.TextChannel],
    "LOGS": [discord.TextChannel]
}

CHANNELS_NAMES_TUPLE = (CHANNEL_NAME for CHANNEL_NAME in CHANNELS_NAMES_DICT)

CHANNELS_NAMES_LITERAL = Literal[CHANNELS_NAMES_TUPLE]

STATS = [
    "elo",
    "peak_elo",
    "wins",
    "winstreak",
    "peak_winstreak",
    "losses",
    "losestreak",
    "peak_losestreak",
    "mvps",
    "games_played"]

DEV_ID = 0  # TODO: set this urselfs id to get the errors
USER_AGENT = ""  # TODO: user-agent for requests to the website that i get the skins from
