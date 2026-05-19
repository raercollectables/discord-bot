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
async def on_ready():
    print(f"Bot is online as {bot.user}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    print(f"Message seen in: {message.channel.name} / {message.channel.id}")
    print(f"Content: {message.content}")
    print(f"Attachments: {len(message.attachments)}")

    async def collect_files():
        files = []

        for attachment in message.attachments:
            try:
                print(f"Downloading attachment: {attachment.filename}")
                files.append(await attachment.to_file())
            except Exception as e:
                print(f"Attachment failed: {e}")

        return files

    # Radar announcement/news/alerts channels
    # Deletes original, then reposts text + images + Radar Member tag
    if message.channel.id in ANNOUNCEMENT_CHANNELS:
        print("Matched announcement channel")

        role = message.guild.get_role(RADAR_MEMBER_ROLE)

        if role is None:
            print(f"Radar Member role not found: {RADAR_MEMBER_ROLE}")
            return

        files = await collect_files()

        try:
            await message.delete()
            print("Original message deleted")
        except Exception as e:
            print(f"Delete failed: {e}")

        await message.channel.send(
            content=f"{message.content} {role.mention}",
            files=files,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

        print("Announcement reposted")

        return

    # In-store stock channels
    # Keeps original, reposts text + images + state role tag
    if message.channel.id in CHANNEL_TO_ROLE:
        print("Matched in-store channel")

        role_id = CHANNEL_TO_ROLE[message.channel.id]
        role = message.guild.get_role(role_id)

        if role is None:
            print(f"In-store role not found: {role_id}")
            return

        files = await collect_files()

        await message.channel.send(
            content=f"{message.content} {role.mention}",
            files=files,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

        print("In-store reposted")

        return

    print("Channel not mapped")

bot.run(TOKEN)
