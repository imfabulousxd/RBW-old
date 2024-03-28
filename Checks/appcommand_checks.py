import asqlite
import discord
from discord import app_commands


def check_command_permission():

    async def predicate(interaction: discord.Interaction):
        interaction.client
        if interaction.user.id in interaction.client.full_perm_users:
            return True

        if interaction.user.id == interaction.guild.id:
            return True

        if interaction.user.guild_permissions.administrator:
            return True

        async with interaction.client.pool.acquire() as conn:
            app_command_roles_ids_tuple = await (await conn.execute(
                'SELECT app_command_roles_ids FROM app_commands_permissions WHERE app_command_name=? AND guild_id=?',
                (interaction.command.name, interaction.guild.id))).fetchone()
            if app_command_roles_ids_tuple is None:
                return False
            else:
                app_command_roles_ids = app_command_roles_ids_tuple[0].split(",")
                for role in interaction.user.roles:
                    if role.id.__str__() in app_command_roles_ids:
                        return True
                return False

    return app_commands.check(predicate)
