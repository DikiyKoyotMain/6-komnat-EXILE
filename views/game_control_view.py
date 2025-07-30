import discord
from utils import LEADER_ROLE_NAME, VOICE_CATEGORY_NAME, PLAYER_ROLE_NAME, current_votes, create_or_get_leader_role, create_or_get_player_channel
from views.vote_view import VoteView
from views.eavesdrop_view import EavesdropChannelSelector

class GameControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Собрать всех", style=discord.ButtonStyle.primary)
    async def gather_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        common_channel = discord.utils.get(guild.voice_channels, name="Общий")
        if not common_channel:
            common_channel = await guild.create_voice_channel("Общий")
        for member in guild.members:
            for role in member.roles:
                if role.name.startswith("игрок_"):
                    if member.voice:
                        await member.move_to(common_channel)
        await interaction.response.send_message("Все игроки собраны в общем канале.", ephemeral=True)

    @discord.ui.button(label="Рассадить по каналам", style=discord.ButtonStyle.success)
    async def scatter(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        leader_role = await create_or_get_leader_role(guild)
        for member in guild.members:
            for role in member.roles:
                if role.name.startswith("игрок_"):
                    try:
                        num = int(role.name.split("_")[1])
                        channel = await create_or_get_player_channel(guild, role, leader_role, num)
                        if member.voice:
                            await member.move_to(channel)
                    except:
                        pass
        await interaction.response.send_message("Игроки рассажены по своим комнатам.", ephemeral=True)

    @discord.ui.button(label="Удалить приватные звонки", style=discord.ButtonStyle.danger)
    async def delete_calls(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        deleted = 0
        for channel in guild.voice_channels:
            if channel.name.startswith("Звонок "):
                await channel.delete()
                deleted += 1
        await interaction.response.send_message(f"Удалено {deleted} приватных звонков.", ephemeral=True)

    @discord.ui.button(label="Заглушить всех", style=discord.ButtonStyle.secondary)
    async def mute_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        for member in guild.members:
            for role in member.roles:
                if role.name.startswith("игрок_"):
                    try:
                        await member.edit(mute=True)
                    except:
                        pass
        await interaction.response.send_message("Все игроки заглушены.", ephemeral=True)

    @discord.ui.button(label="Включить микрофоны", style=discord.ButtonStyle.secondary)
    async def unmute_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        for member in guild.members:
            for role in member.roles:
                if role.name.startswith("игрок_"):
                    try:
                        await member.edit(mute=False)
                    except:
                        pass
        await interaction.response.send_message("Микрофоны всех игроков включены.", ephemeral=True)

    @discord.ui.button(label="Отключить наушники", style=discord.ButtonStyle.secondary)
    async def deafen_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        for member in guild.members:
            for role in member.roles:
                if role.name.startswith("игрок_"):
                    try:
                        await member.edit(deafen=True)
                    except:
                        pass
        await interaction.response.send_message("Всем игрокам отключён звук.", ephemeral=True)

    @discord.ui.button(label="Включить наушники", style=discord.ButtonStyle.secondary)
    async def undeafen_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        for member in guild.members:
            for role in member.roles:
                if role.name.startswith("игрок_"):
                    try:
                        await member.edit(deafen=False)
                    except:
                        pass
        await interaction.response.send_message("Всем игрокам включён звук.", ephemeral=True)

    @discord.ui.button(label="Подслушать звонок", style=discord.ButtonStyle.primary)
    async def eavesdrop(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        leader = interaction.user
        call_channels = [ch for ch in guild.voice_channels if ch.name.startswith("Звонок ")]
        if not call_channels:
            await interaction.response.send_message("Нет активных звонков.", ephemeral=True)
            return
        view = EavesdropChannelSelector(leader, call_channels)
        await interaction.response.send_message("Выберите звонок для подслушки:", view=view, ephemeral=True)

    @discord.ui.button(label="Начать голосование", style=discord.ButtonStyle.success)
    async def start_vote(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        player_members = [m for m in guild.members if any(r.name.startswith("игрок_") for r in m.roles)]
        if len(player_members) < 2:
            await interaction.response.send_message("Недостаточно игроков для голосования.", ephemeral=True)
            return
        vote_view = VoteView(player_members)
        for player in player_members:
            try:
                await player.send("Проголосуй за одного из игроков:", view=vote_view)
            except:
                pass
        current_votes.clear()
        await interaction.response.send_message("Голосование началось! Игрокам отправлены сообщения.", ephemeral=True)

    @discord.ui.button(label="Завершить голосование", style=discord.ButtonStyle.danger)
    async def end_vote(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not current_votes:
            await interaction.response.send_message("Голосов нет или голосование не проводилось.", ephemeral=True)
            return
        from collections import Counter
        vote_counts = Counter(current_votes.values())
        results = "\n".join([
            f"{interaction.guild.get_member(uid).display_name}: {count}" for uid, count in vote_counts.items()
        ])
        await interaction.response.send_message(f"Результаты голосования:\n{results}", ephemeral=False)

    @discord.ui.button(label="Завершить игру", style=discord.ButtonStyle.danger)
    async def end_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        deleted_channels = 0
        deleted_roles = 0
        for channel in list(guild.voice_channels):
            if channel.name.startswith("Комната "):
                try:
                    await channel.delete(reason="Завершение игры")
                    deleted_channels += 1
                except:
                    pass
        for role in list(guild.roles):
            if role.name.startswith("игрок_"):
                try:
                    await role.delete(reason="Завершение игры")
                    deleted_roles += 1
                except:
                    pass
        await interaction.response.send_message(
            f"Игра завершена! Удалено комнат: {deleted_channels}, удалено ролей: {deleted_roles}.",
            ephemeral=True
        ) 