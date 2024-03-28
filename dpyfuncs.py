import discord
from typing import Union
import re


async def fetch_member(
        member_data: Union[str, int],
        guild: discord.Guild
) -> Union[discord.Member, None]:
    member_id = None
    member_data_temp = member_data

    try:
        member_id = int(member_data_temp)
    except ValueError:
        pass

    if member_id is None:
        member_data_temp = member_data_temp.replace("<@", "")
        member_data_temp = member_data_temp.replace("!", "")
        member_data_temp = member_data_temp.replace(">", "")
        try:
            member_id = int(member_data_temp)
        except ValueError:
            pass

    if member_id is None:
        return None

    member = guild.get_member(member_id)

    if member is None:
        try:
            member = await guild.fetch_member(member_id)
        except discord.HTTPException:
            pass

    return member


async def fetch_channel(
        channel_data: Union[str, int],
        guild: discord.Guild
) -> Union[discord.abc.GuildChannel, None]:
    channel_id = None
    channel_data_temp = channel_data

    try:
        channel_id = int(channel_data_temp)
    except ValueError:
        pass

    if channel_id is not None:
        pass
    elif channel_data_temp.startswith("<#") and channel_data_temp.endswith(">"):
        channel_data_temp = channel_data_temp.replace("<#", "")
        channel_data_temp = channel_data_temp.replace(">", "")
        try:
            channel_id = int(channel_data_temp)
        except ValueError:
            pass
    elif (channel_data_temp.startswith(f"https://discord.com/channels/{guild.id}") or
          channel_data_temp.startswith(f"http://discord.com/channels/{guild.id}")):

        channel_data_temp = channel_data_temp.replace(f"https://discord.com/channels/{guild.id}/", "")
        channel_data_temp = channel_data_temp.replace(f"http://discord.com/channels/{guild.id}/", "")

        try:
            channel_id = int(channel_data_temp)
        except ValueError:
            pass

    if channel_id is None:
        return None

    channel = guild.get_channel(channel_id)

    if channel is None:
        try:
            channel = await guild.fetch_channel(channel_id)
        except discord.HTTPException:
            return None

    return channel


def fetch_role(
        role_data: Union[str, int],
        guild: discord.Guild
) -> Union[discord.Role, None]:

    role_id = None
    role_data_temp = role_data

    try:
        role_id = int(role_data_temp)
    except ValueError:
        pass
    
    if role_id is not None:
        pass
    elif role_data_temp.startswith("<@&") and role_data_temp.endswith(">"):
        role_data_temp = role_data_temp.replace("<@&", "")
        role_data_temp = role_data_temp.replace(">", "")

        try:
            role_id = int(role_data_temp)
        except ValueError:
            pass
    else:
        try:
            role_id = int(role_data_temp)
        except ValueError:
            pass

    if role_id is None:
        return None

    role = guild.get_role(role_id)

    return role


async def fetch_user(user_data: Union[str, int], client: discord.Client):
    user_id = None
    if isinstance(user_data, int):
        user_id = user_data
    else:
        user_id_pattern = re.compile(r'(<@(\d+)>|<@!(\d+)>|(^\d+$))')
        user_id_groups = user_id_pattern.fullmatch(user_data).group(2,3,4)
        user_id = int(user_id_groups[0] or user_id_groups[1] or user_id_groups[2])

    try:
        user = await client.fetch_user(user_id)
        return user
    except discord.HTTPException:
        return None
