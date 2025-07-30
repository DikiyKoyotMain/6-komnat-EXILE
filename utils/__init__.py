import discord

LEADER_ROLE_NAME = "ведущий"
PLAYER_ROLE_PREFIX = "игрок_"
PLAYER_ROLE_NAME = "игрок"
VOICE_CATEGORY_NAME = "Игровые комнаты"
PISTOL_ROLE_NAME = "пистолет"

delete_tasks = {}
player_original_channels = {}
original_nicknames = {}
current_votes = {}
active_callers = set()
active_callees = set()

async def create_or_get_leader_role(guild):
    role = discord.utils.get(guild.roles, name=LEADER_ROLE_NAME)
    if not role:
        role = await guild.create_role(name=LEADER_ROLE_NAME)
    return role

async def create_or_get_pistol_role(guild):
    role = discord.utils.get(guild.roles, name=PISTOL_ROLE_NAME)
    if not role:
        role = await guild.create_role(name=PISTOL_ROLE_NAME)
    return role

async def create_or_get_player_role(guild):
    existing_numbers = []
    for role in guild.roles:
        if role.name.startswith(PLAYER_ROLE_PREFIX):
            try:
                num = int(role.name.split("_")[1])
                existing_numbers.append(num)
            except:
                pass
    next_num = 1
    while next_num in existing_numbers:
        next_num += 1
    role_name = f"{PLAYER_ROLE_PREFIX}{next_num}"
    player_role = discord.utils.get(guild.roles, name=role_name)
    if not player_role:
        player_role = await guild.create_role(name=role_name)
    return player_role, next_num

async def create_or_get_voice_category(guild):
    category = discord.utils.get(guild.categories, name=VOICE_CATEGORY_NAME)
    if not category:
        category = await guild.create_category(VOICE_CATEGORY_NAME)
    return category

async def create_or_get_player_channel(guild, player_role, leader_role, num):
    category = await create_or_get_voice_category(guild)
    await category.edit(overwrites={})
    room_name = f"Комната {num}"
    overwrites = {
        leader_role: discord.PermissionOverwrite(view_channel=True, speak=True, connect=True),
        player_role: discord.PermissionOverwrite(view_channel=True, speak=True, connect=True, stream=True)
    }
    channel = discord.utils.get(category.voice_channels, name=room_name)
    if not channel:
        channel = await category.create_voice_channel(name=room_name, overwrites=overwrites)
    return channel

async def create_temp_call_channel(guild, caller, callee, leader_role):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        leader_role: discord.PermissionOverwrite(view_channel=True, speak=True, connect=True),
        caller: discord.PermissionOverwrite(view_channel=True, speak=True, connect=True),
        callee: discord.PermissionOverwrite(view_channel=True, speak=True, connect=True),
    }
    channel = await guild.create_voice_channel(
        f"Звонок {caller.display_name} и {callee.display_name}", overwrites=overwrites
    )
    return channel 