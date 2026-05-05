import discord
from discord.ext import commands

import os
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

CHANNEL_TO_ROLE = {
    1464844020101419184: 1467959378274681047,  # WA IN STORE
    1464843010050359532: 1467959569400467527,  # NSW IN STORE
    1464843455908806666: 1467959606822043832,  # VIC IN STORE
    1464843626424172625: 1467960267139842213,  # QLD IN STORE
    1464844205628329985: 1467959638413541376,  # SA IN STORE
    1464844447375298713: 1467960394579710015,  # TAS IN STORE
    1485255219414831164: 1467960582886920446,  # ACT IN STORE
    1464844304961765529: 1467959657942351892,  # NT IN STORE
}

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    print("Servers:")
    for guild in bot.guilds:
        print(f"- {guild.name} / {guild.id}")
        for channel in guild.text_channels:
            print(f"  #{channel.name} / {channel.id}")

@bot.event
async def on_message(message):
    print("MESSAGE EVENT TRIGGERED")
    print(f"Channel: {message.channel.name} / {message.channel.id}")
    print(f"Author: {message.author}")
    print(f"Content: {message.content}")

    if message.author.bot:
        return

    if message.channel.id not in CHANNEL_TO_ROLE:
        print("This channel is not mapped.")
        return

    role_id = CHANNEL_TO_ROLE[message.channel.id]
    role = message.guild.get_role(role_id)

    if role is None:
        print(f"Role not found: {role_id}")
        return

    await message.channel.send(
        f"{message.content} {role.mention}",
        allowed_mentions=discord.AllowedMentions(roles=True)
    )

bot.run(TOKEN)
