import asyncio
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')

try:
    with open('.env', 'r', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip() and '=' in line:
                key, value = line.strip().split('=', 1)
                key = key.replace('\ufeff', '')
                os.environ[key] = value
except Exception as e:
    print(f"Ошибка при загрузке .env: {e}")

from utils import (
    create_or_get_leader_role, create_or_get_player_role, create_or_get_player_channel, 
    create_temp_call_channel, create_or_get_pistol_role, LEADER_ROLE_NAME, PLAYER_ROLE_NAME,
    VOICE_CATEGORY_NAME, PISTOL_ROLE_NAME, delete_tasks, player_original_channels, 
    original_nicknames, current_votes, active_callers, active_callees
)
from views.call_confirm_view import CallConfirmView
from views.end_call_view import EndCallView
from views.vote_view import VoteView
from views.verify_view import VerifyView
from views.eavesdrop_view import EavesdropChannelSelector

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.tree.command(name="callto", description="Позвонить другому игроку")
async def callto(interaction: discord.Interaction):
    caller = interaction.user
    guild = interaction.guild
    if caller.id in active_callers:
        await interaction.response.send_message("Вы уже инициировали звонок. Дождитесь завершения предыдущего!", ephemeral=True)
        return
    player_members = [m for m in guild.members if any(r.name.startswith("игрок_") for r in m.roles) and m != caller and not m.bot and m.id not in active_callees]
    if not player_members:
        await interaction.response.send_message("Нет других игроков для звонка или все игроки уже заняты.", ephemeral=True)
        return
    view = CallToButtonsView(caller, player_members, guild, interaction)
    await interaction.response.send_message("Выберите, кому позвонить:", view=view, ephemeral=True)

@bot.tree.command(name="leadpanel", description="Панель управления для ведущего")
async def leadpanel(interaction: discord.Interaction):
    print(f"Команда leadpanel вызвана пользователем: {interaction.user.name}")
    user_roles = [role.name for role in interaction.user.roles]
    print(f"Роли пользователя: {user_roles}")
    if not any(role.name == LEADER_ROLE_NAME for role in interaction.user.roles):
        await interaction.response.send_message("Только ведущий может использовать эту команду!", ephemeral=True)
        return
    try:
        embed = discord.Embed(
            title="🎮 Панель управления ведущего",
            description="Используйте кнопки ниже для управления игрой",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(
            embed=embed,
            view=LeadPanelView(),
            ephemeral=True
        )
        print("Панель управления отправлена успешно")
    except Exception as e:
        print(f"Ошибка при отправке панели: {e}")
        await interaction.response.send_message(f"Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="verify", description="Выбери свою роль: ведущий или игрок")
async def verify(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Выберите свою роль:",
        view=VerifyView(),
        ephemeral=True
    )

@bot.event
async def on_ready():
    print(f"✅ Бот запущен как {bot.user}")
    try:
        await bot.tree.sync()
        print("Глобальная синхронизация команд выполнена!")
    except Exception as e:
        print(f"Ошибка глобальной синхронизации: {e}")
    guild = bot.guilds[0] if bot.guilds else None
    if guild:
        leader_role = await create_or_get_leader_role(guild)
        for member in guild.members:
            for role in member.roles:
                if role.name.startswith("игрок_"):
                    try:
                        num = int(role.name.split("_")[1])
                        await create_or_get_player_channel(guild, role, leader_role, num)
                    except:
                        pass

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and before.channel.id in delete_tasks:
        channel = before.channel
        if len([m for m in channel.members if not m.bot]) == 0:
            async def delete_channel_later():
                await asyncio.sleep(5)
                if len([m for m in channel.members if not m.bot]) == 0:
                    await channel.delete(reason="Все участники вышли из канала")
                    delete_tasks.pop(channel.id, None)
                    for uid, orig_channel_id in player_original_channels.items():
                        user = channel.guild.get_member(uid)
                        if user and orig_channel_id:
                            orig_channel = channel.guild.get_channel(orig_channel_id)
                            if orig_channel:
                                try:
                                    await user.move_to(orig_channel)
                                except:
                                    pass
                    player_original_channels.clear()
            delete_tasks[channel.id] = asyncio.create_task(delete_channel_later())
    if after.channel and after.channel.id in delete_tasks:
        task = delete_tasks[after.channel.id]
        if task is not None and not task.done():
            task.cancel()
            delete_tasks[after.channel.id] = None

class LeadPanelView(discord.ui.View):
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
        global current_votes
        current_votes = {}
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

    @discord.ui.button(label="Пистолет", style=discord.ButtonStyle.danger)
    async def give_pistol(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        player_members = [m for m in guild.members if any(r.name.startswith("игрок_") for r in m.roles)]
        if not player_members:
            await interaction.response.send_message("Нет игроков для выдачи пистолета.", ephemeral=True)
            return
        view = PistolPlayerSelector(guild)
        await interaction.response.send_message("Выберите игрока для выдачи пистолета:", view=view, ephemeral=True)

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

class PistolPlayerSelector(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=60)
        self.guild = guild
        self.add_item(PistolPlayerSelect(guild))

class PistolPlayerSelect(discord.ui.Select):
    def __init__(self, guild):
        player_members = [m for m in guild.members if any(r.name.startswith("игрок_") for r in m.roles)]
        options = [discord.SelectOption(label=player.display_name, value=str(player.id)) for player in player_members]
        super().__init__(placeholder="Выберите игрока для пистолета", options=options)
        self.guild = guild

    async def callback(self, interaction: discord.Interaction):
        player_id = int(self.values[0])
        player = self.guild.get_member(player_id)
        
        if not player:
            await interaction.response.send_message("Игрок не найден.", ephemeral=True)
            return
        
        pistol_role = await create_or_get_pistol_role(self.guild)
        await player.add_roles(pistol_role)
        
        category = discord.utils.get(self.guild.categories, name="Игровые комнаты")
        if category:
            for channel in category.voice_channels:
                if channel.name.startswith("Комната "):
                    await channel.set_permissions(player, view_channel=True, speak=True, connect=True)
        
        try:
            target_view = PistolTargetSelector(self.guild, player)
            await player.send("🔫 У вас есть пистолет! Выберите цель для выстрела:", view=target_view)
            await interaction.response.send_message(f"Пистолет выдан {player.display_name}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"Пистолет выдан {player.display_name}, но не удалось отправить сообщение в ЛС.", ephemeral=True)

class PistolTargetSelector(discord.ui.View):
    def __init__(self, guild, shooter):
        super().__init__(timeout=120)
        self.guild = guild
        self.shooter = shooter
        self.add_item(PistolTargetSelect(guild, shooter))

class PistolTargetSelect(discord.ui.Select):
    def __init__(self, guild, shooter):
        player_members = [m for m in guild.members if any(r.name.startswith("игрок_") for r in m.roles) and m != shooter]
        options = [discord.SelectOption(label=player.display_name, value=str(player.id)) for player in player_members]
        super().__init__(placeholder="Выберите цель для выстрела", options=options)
        self.guild = guild
        self.shooter = shooter

    async def callback(self, interaction: discord.Interaction):
        target_id = int(self.values[0])
        target = self.guild.get_member(target_id)
        
        if not target:
            await interaction.response.send_message("Цель не найдена.", ephemeral=True)
            return
        
        pistol_role = discord.utils.get(self.guild.roles, name="пистолет")
        if pistol_role:
            await self.shooter.remove_roles(pistol_role)
        
        category = discord.utils.get(self.guild.categories, name="Игровые комнаты")
        if category:
            for channel in category.voice_channels:
                if channel.name.startswith("Комната "):
                    await channel.set_permissions(self.shooter, overwrite=None)
        
        for role in self.shooter.roles:
            if role.name.startswith("игрок_"):
                try:
                    num = int(role.name.split("_")[1])
                    leader_role = await create_or_get_leader_role(self.guild)
                    player_channel = await create_or_get_player_channel(self.guild, role, leader_role, num)
                    if self.shooter.voice:
                        await self.shooter.move_to(player_channel)
                except:
                    pass
                break
        
        await interaction.response.send_message(f"🔫 Выстрел в {target.display_name}! Вы возвращены в свою комнату.", ephemeral=True)

class CallToButtonsView(discord.ui.View):
    def __init__(self, caller, players, guild, interaction):
        super().__init__(timeout=60)
        self.caller = caller
        self.players = players
        self.guild = guild
        self.interaction = interaction
        for player in players:
            self.add_item(CallToButton(player, self.caller, self.guild, self.interaction))

class CallToButton(discord.ui.Button):
    def __init__(self, target, caller, guild, interaction):
        super().__init__(label=target.display_name, style=discord.ButtonStyle.primary)
        self.target = target
        self.caller = caller
        self.guild = guild
        self.interaction = interaction

    async def callback(self, interaction: discord.Interaction):
        if self.caller.id in active_callers:
            await interaction.response.send_message("Вы уже инициировали звонок. Дождитесь завершения предыдущего!", ephemeral=True)
            return
        caller_role = discord.utils.find(lambda r: r.name.startswith(PLAYER_ROLE_NAME), self.caller.roles)
        target_role = discord.utils.find(lambda r: r.name.startswith(PLAYER_ROLE_NAME), self.target.roles)
        if not caller_role or not target_role:
            await interaction.response.send_message("Оба пользователя должны быть игроками.", ephemeral=True)
            return
        view = CallConfirmView(caller=self.caller, callee=self.target, guild=self.guild, interaction=self.interaction)
        try:
            await self.target.send(f"{self.caller.display_name} хочет с вами поговорить!", view=view)
            await interaction.response.send_message(f"Запрос отправлен {self.target.mention}", ephemeral=True)
            active_callers.add(self.caller.id)
            active_callees.add(self.target.id)
        except discord.Forbidden:
            await interaction.response.send_message(f"Не удалось отправить запрос {self.target.mention} в ЛС. Разрешите боту писать в ЛС.", ephemeral=True)

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN не найден в переменных окружения. Проверьте файл .env")
bot.run(TOKEN) 