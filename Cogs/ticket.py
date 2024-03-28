import asyncio
import datetime
import re
from typing import Type, Any, Optional

from discord._types import ClientT
from discord.ui import Item
from typing_extensions import Self

import discord.app_commands
from discord.ext import commands

from Checks import appcommand_checks

from discord import app_commands, Interaction

import asqlite

from Functions import functions


class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.show_help = False

    async def cog_load(self) -> None:
        self.bot.pool: asqlite.Pool
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS ticket_starters (ticket_message_id INT, category_name TEXT, category_emoji TEXT, category_channel_id INT, roles_ids TEXT, embed_title TEXT, embed_description TEXT, guild_id INT)")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS tickets (ticket_thread_id INT, ticket_requester_id INT, guild_id INT)")
        self.add_dynamic_items()

    async def cog_unload(self) -> None:
        ...

    def add_dynamic_items(self):
        self.bot.add_dynamic_items(CategoryDropdown)

    @app_commands.command(name='sendticketmessage', description="sends the starter of tickets in a channel")
    @app_commands.describe(in_channel='The Channel to send the ticket starter message in')
    @appcommand_checks.check_command_permission()
    async def sendticketmessage(self, interaction: discord.Interaction, in_channel: discord.TextChannel):
        interaction.response: discord.InteractionResponse
        await interaction.response.send_message("Please send the category names and "
                                                "emojis in this particular format.\n"
                                                "(Category Name 1)::(Category Emoji 1)::(Roles IDs To Give Access To The Ticket Seperated by `,` 1)::(Embed Title 1)::(Embed description 1)---"
                                                "(Category Name 2)::(Category Emoji 2)::(Roles IDs To Give Access To The Ticket Seperated by `,` 2)::(Embed Title 2)::(Embed description 2)---...")

        def msg_check(msg: discord.Message):
            return msg.author.id == interaction.user.id and msg.channel.id == interaction.channel.id

        category_data_message = None

        try:
            category_data_message = \
                await interaction.client.wait_for(
                    'message',
                    check=msg_check,
                    timeout=5 * 60
                )
        except asyncio.TimeoutError:
            await interaction.response.edit_message(
                content='Times up!'
            )
            return

        ticket_starter_embed = discord.Embed(
            title='Create a Ticket',
            description='Please be prepared with your issue when opening a support ticket.',
            colour=0
        )
        ticket_starter_embed.set_thumbnail(url=interaction.guild.icon.url)

        ticket_starter_message = await in_channel.send(
            embed=ticket_starter_embed
        )

        the_messages_view = TicketStarterView()
        dropdown_options = []

        ticket_categories = category_data_message.content.split('---')

        for category in ticket_categories:
            category_name, category_emoji, category_roles_ids, embed_title, embed_description = category.split(
                "::")

            self.bot.pool: asqlite.Pool
            async with self.bot.pool.acquire() as conn:
                await conn.execute('INSERT INTO ticket_starters VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                   (ticket_starter_message.id,
                                    category_name,
                                    category_emoji,
                                    int(in_channel.id),
                                    category_roles_ids,
                                    embed_title,
                                    embed_description,
                                    interaction.guild.id))

            dropdown_options.append(
                discord.SelectOption(label=category_name,
                                     emoji=category_emoji)
            )

        categories_select = CategoryDropdown(dropdown_options)

        the_messages_view.add_item(categories_select)

        await ticket_starter_message.edit(
            view=the_messages_view
        )

    @app_commands.command(name='close', description='Closes the ticket')
    @appcommand_checks.check_command_permission()
    async def close(self, interaction: discord.Interaction):
        async with self.bot.pool.acquire() as conn:
            cursor = await conn.execute('SELECT * FROM tickets WHERE ticket_thread_id=? AND guild_id=?',
                                        (interaction.channel.id, interaction.guild.id))
            if await cursor.fetchone() is None:
                return

            await conn.execute("DELETE FROM tickets WHERE ticket_thread_id=? AND guild_id=?",
                               (interaction.channel.id, interaction.guild.id))

        interaction.channel: discord.Thread

        await interaction.response.send_message(content="Ticket closed.", ephemeral=True)

        webhook = await functions.fetch_webhook(interaction.channel, interaction.client)

        await webhook.send(
            embed=functions.embed(
                interaction.guild,
                "",
                "Ticket closed by <@{}> at <t:{}>".format(interaction.user.id,
                                                        datetime.datetime.now().timestamp().__int__())
            )
        )

        await interaction.channel.edit(archived=True, locked=True,
                                       reason='by {0.name} | {0.id}'.format(interaction.user))


async def setup(bot: commands.Bot):
    await bot.add_cog(Ticket(bot))


class TicketStarterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)


class CategoryDropdown(discord.ui.DynamicItem[discord.ui.Select], template='imfabulousxd:ticketstarter'):
    def __init__(self, select_options: Optional[list[discord.SelectOption]] = None):
        super().__init__(
            discord.ui.Select(
                options=select_options,
                custom_id='imfabulousxd:ticketstarter',
                min_values=1,
                max_values=1
            )
        )

    @classmethod
    async def from_custom_id(
            cls: Type[Self], interaction: Interaction, item: Item, match: re.Match[str], /
    ) -> Self:
        return cls()

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        async with interaction.client.pool.acquire() as conn:
            conn: asqlite.Connection
            async with conn.execute('SELECT * FROM tickets WHERE ticket_requester_id=? AND guild_id=?',
                                    (interaction.user.id, interaction.guild.id)) as cursor:
                category_data = await cursor.fetchone()
                if category_data is None:
                    return True
                else:
                    await interaction.response.send_message(ephemeral=True,
                                                            content=f"You cannot have more than 1 ticket!")
                    await interaction.message.edit()
                    return False

    async def callback(self, interaction: discord.Interaction) -> None:
        #  interaction.data keys ('values': list[str], 'custom_id': str, component_type: int)

        await interaction.response.defer(ephemeral=True, thinking=True)

        category_data = None

        async with interaction.client.pool.acquire() as conn:
            conn: asqlite.Connection
            async with conn.execute(
                    'SELECT * FROM ticket_starters WHERE category_name=? AND ticket_message_id=? AND guild_id=?',
                    (interaction.data.get('values')[0], interaction.message.id, interaction.guild.id)) as cursor:
                category_data = await cursor.fetchone()

        thread_channel = await create_ticket(interaction.user, category_data, interaction.client)

        await interaction.edit_original_response(content=thread_channel.jump_url)

        await interaction.message.edit()


async def create_ticket(member: discord.Member, category_data: tuple[int, str, str, int, str, str, str, int],
                        client):
    (ticket_message_Id,
     category_name,
     category_emoji,
     category_channel_id,
     roles_ids,
     embed_title,
     embed_description,
     _) = category_data

    roles_mentions = ['<@&{}>'.format(t) for t in roles_ids.split(',')]

    guild = member.guild

    ticket_channel: discord.TextChannel = await guild.fetch_channel(category_channel_id)

    ticket_thread = await ticket_channel.create_thread(
        name=f'{category_name}-{member.name}',
        message=None,
        invitable=False
    )

    ticket_started_embed = discord.Embed(
        title=embed_title,
        description=embed_description,
        colour=0
    )
    ticket_started_embed.set_footer(text='please wait for a staff member...')

    await ticket_thread.send(
        content="@silent "+''.join(roles_mentions) + member.mention,
        delete_after=3
    )

    await ticket_thread.send(
        embed=ticket_started_embed
    )

    async with client.pool.acquire() as conn:
        await conn.execute('INSERT INTO tickets VALUES (?, ?, ?)',
                           (ticket_thread.id, member.id, guild.id))

    return ticket_thread
