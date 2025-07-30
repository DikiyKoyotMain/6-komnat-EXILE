import discord
from utils import current_votes

class VoteView(discord.ui.View):
    def __init__(self, players):
        super().__init__(timeout=60)
        self.players = players
        self.add_item(VoteDropdown(players))

class VoteDropdown(discord.ui.Select):
    def __init__(self, players):
        options = [
            discord.SelectOption(label=player.display_name, value=str(player.id))
            for player in players
        ]
        super().__init__(placeholder="Выбери игрока", options=options)

    async def callback(self, interaction: discord.Interaction):
        voter = interaction.user.id
        voted_for = int(self.values[0])
        current_votes[voter] = voted_for
        await interaction.response.send_message("Твой голос принят!", ephemeral=True) 