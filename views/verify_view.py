import discord
from utils import create_or_get_leader_role, create_or_get_player_role, create_or_get_player_channel, original_nicknames

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Ведущий", style=discord.ButtonStyle.primary)
    async def leader(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        role = await create_or_get_leader_role(guild)
        await interaction.user.add_roles(role)
        original_nicknames[interaction.user.id] = interaction.user.nick
        await interaction.user.edit(nick="Ведущий")
        await interaction.response.send_message("Вам выдана роль ведущего и установлен анонимный ник!", ephemeral=True)

    @discord.ui.button(label="Игрок", style=discord.ButtonStyle.primary)
    async def player(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        leader_role = await create_or_get_leader_role(guild)
        player_role, next_num = await create_or_get_player_role(guild)
        await member.add_roles(player_role)
        channel = await create_or_get_player_channel(guild, player_role, leader_role, next_num)
        await member.edit(nick=f"Игрок {next_num}")
        try:
            await member.move_to(channel)
        except Exception:
            pass
        await interaction.response.send_message(
            f"Ты теперь игрок. Твоя комната: **{channel.name}**",
            ephemeral=True
        )

 