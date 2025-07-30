import discord
import asyncio
from utils import player_original_channels, delete_tasks, LEADER_ROLE_NAME, active_callers, active_callees, create_temp_call_channel
from views.end_call_view import EndCallView

class CallConfirmView(discord.ui.View):
    def __init__(self, caller, callee, guild, interaction):
        super().__init__(timeout=5)
        self.caller = caller
        self.callee = callee
        self.guild = guild
        self.interaction = interaction
        self.channel = None
        self.delete_task = None
        self.auto_decline_task = None
        self._start_auto_decline()

    def _start_auto_decline(self):
        async def auto_decline():
            await asyncio.sleep(5)
            if self.caller.id in active_callers:
                try:
                    await self.caller.send(f"{self.callee.display_name} не ответил на звонок в течение 5 секунд. Звонок автоматически отклонён.")
                except:
                    pass
                active_callers.discard(self.caller.id)
                active_callees.discard(self.callee.id)
        self.auto_decline_task = asyncio.create_task(auto_decline())

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.auto_decline_task and not self.auto_decline_task.done():
            self.auto_decline_task.cancel()
        
        from utils import create_or_get_leader_role
        leader_role = await create_or_get_leader_role(self.guild)
        self.channel = await create_temp_call_channel(self.guild, self.caller, self.callee, leader_role)
        player_original_channels[self.caller.id] = self.caller.voice.channel.id if self.caller.voice else None
        player_original_channels[self.callee.id] = self.callee.voice.channel.id if self.callee.voice else None
        if self.caller.voice:
            await self.caller.move_to(self.channel)
        if self.callee.voice:
            await self.callee.move_to(self.channel)
        await interaction.response.send_message(f"Вы соединены с {self.caller.display_name}!", ephemeral=True)
        try:
            await self.caller.send(f"{self.callee.display_name} принял звонок! Перемещаю вас в общий канал.", view=EndCallView(self.channel.id, self.caller.id, self.callee.id))
        except:
            pass
        try:
            await self.callee.send(f"Вы на звонке с {self.caller.display_name}.", view=EndCallView(self.channel.id, self.caller.id, self.callee.id))
        except:
            pass
        delete_tasks[self.channel.id] = None
        active_callers.discard(self.caller.id)
        active_callees.discard(self.callee.id)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.auto_decline_task and not self.auto_decline_task.done():
            self.auto_decline_task.cancel()
        
        await interaction.response.send_message("Звонок отклонён.", ephemeral=True)
        try:
            await self.caller.send(f"{self.callee.display_name} отклонил звонок.")
        except:
            pass
        active_callers.discard(self.caller.id)
        active_callees.discard(self.callee.id)
        self.stop()

    async def on_timeout(self):
        if self.auto_decline_task and not self.auto_decline_task.done():
            self.auto_decline_task.cancel()
        active_callers.discard(self.caller.id)
        active_callees.discard(self.callee.id) 