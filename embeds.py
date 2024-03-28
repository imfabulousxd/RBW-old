import discord
from typing import Union
from Functions import functions


def moderation_embed(author: Union[discord.User, discord.Member],
                     embed_description: str) -> discord.Embed:
    return functions.embed(
        author.guild,
        "Moderation System",
        embed_description,
        embed_footer_text=f"Invoked by {author.name}",
        embed_footer_icon_url=True,
        embed_timestamp=True
    )
