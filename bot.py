import discord
from discord.ext import commands

import os
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
# In-store channels: original message stays, bot reposts with state role
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

# Radar channels: delete original, repost with RADAR MEMBER role
ANNOUNCEMENT_CHANNELS = {
    1466323776756256861,  # radar-announcements
    1466323977856352349,  # radar-alerts
    1466324139626332265,  # radar-news
}

RADAR_MEMBER_ROLE = 1467963589330735340


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    print(f"Message seen in: {message.channel.name} / {message.channel.id}")
    print(f"Content: {message.content}")

    if message.channel.id in ANNOUNCEMENT_CHANNELS:
        print("Matched announcement channel")

        role = message.guild.get_role(RADAR_MEMBER_ROLE)

        if role is None:
            print(f"Radar Member role not found: {RADAR_MEMBER_ROLE}")
            return

        try:
            await message.delete()
            print("Original message deleted")
        except Exception as e:
            print(f"Delete failed: {e}")

        try:
            await message.channel.send(
                f"{message.content} {role.mention}",
                allowed_mentions=discord.AllowedMentions(roles=True)
            )
            print("Announcement reposted")
        except Exception as e:
            print(f"Send failed: {e}")

        return

    if message.channel.id in CHANNEL_TO_ROLE:
        print("Matched in-store channel")

        role_id = CHANNEL_TO_ROLE[message.channel.id]
        role = message.guild.get_role(role_id)

        if role is None:
            print(f"In-store role not found: {role_id}")
            return

        await message.channel.send(
            f"{message.content} {role.mention}",
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

        return

    print("Channel not mapped")


bot.run(TOKEN)
