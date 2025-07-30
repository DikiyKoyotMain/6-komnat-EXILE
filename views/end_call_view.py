import discord
from utils import delete_tasks, player_original_channels, LEADER_ROLE_NAME, VOICE_CATEGORY_NAME, create_or_get_leader_role, create_or_get_player_channel

class EndCallView(discord.ui.View):
    def __init__(self, channel_id, caller_id, callee_id):
        super().__init__(timeout=300)
        self.channel_id = channel_id
        self.caller_id = caller_id
        self.callee_id = callee_id

    @discord.ui.button(label="Завершить звонок", style=discord.ButtonStyle.danger)
    async def end_call(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = None
        for g in interaction.client.guilds:
            member = g.get_member(user.id)
            if member:
                guild = g
                break
        if not guild:
            await interaction.response.send_message("Не удалось определить сервер.", ephemeral=True)
            return
        channel = guild.get_channel(self.channel_id)
        for uid in [self.caller_id, self.callee_id]:
            member = guild.get_member(uid)
            orig_channel = None
            if member:
                for role in member.roles:
                    if role.name.startswith("игрок_"):
                        try:
                            num = int(role.name.split("_")[1])
                            leader_role = await create_or_get_leader_role(guild)
                            orig_channel = await create_or_get_player_channel(guild, role, leader_role, num)
                        except Exception:
                            pass
                        break
            if member and orig_channel:
                try:
                    await member.move_to(orig_channel)
                except Exception:
                    pass
        if channel:
            await channel.delete(reason="Звонок завершён по кнопке")
        delete_tasks.pop(self.channel_id, None)
        player_original_channels.pop(self.caller_id, None)
        player_original_channels.pop(self.callee_id, None)
        await interaction.response.send_message("Звонок завершён! Вы возвращены в свои комнаты.", ephemeral=True) 