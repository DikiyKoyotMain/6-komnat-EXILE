import discord

class EavesdropChannelSelector(discord.ui.View):
    def __init__(self, leader, channels):
        super().__init__(timeout=30)
        self.leader = leader
        self.channels = channels
        self.add_item(EavesdropSelect(leader, channels))

class EavesdropSelect(discord.ui.Select):
    def __init__(self, leader, channels):
        options = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in channels]
        super().__init__(placeholder="Выберите канал", options=options)
        self.leader = leader

    async def callback(self, interaction: discord.Interaction):
        channel_id = int(self.values[0])
        channel = discord.utils.get(interaction.guild.voice_channels, id=channel_id)
        if self.leader.voice:
            await self.leader.move_to(channel)
        else:
            await self.leader.edit(voice_channel=channel)
        await interaction.response.send_message(f"Вы перемещены в {channel.name} (подслушка активна)", ephemeral=True) 