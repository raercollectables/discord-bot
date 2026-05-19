import discord
from discord.ext import commands
from discord import app_commands

import os
import json
import random
from datetime import datetime, timezone

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

# Giveaway settings
GIVEAWAY_FEED_CHANNEL = 1506346834962944001
GIVEAWAY_ADMIN_ROLE = 1506348836895854712
WINNERS_CHANNEL = 1506345396039979008

TEXT_ALERT_POINTS = 1
PHOTO_ALERT_POINTS = 2
DELETE_GRACE_SECONDS = 30
DATA_FILE = "giveaway_entries.json"


def current_month():
    return datetime.now().strftime("%Y-%m")


def default_data():
    return {
        "month": current_month(),
        "entries": {},
        "tracked_messages": {}
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        data = default_data()
        save_data(data)
        return data

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    if data.get("month") != current_month():
        data = default_data()
        save_data(data)

    data.setdefault("entries", {})
    data.setdefault("tracked_messages", {})

    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def has_photo(message):
    return len(message.attachments) > 0


def is_giveaway_admin(member):
    return any(role.id == GIVEAWAY_ADMIN_ROLE for role in member.roles)


async def log_giveaway_entry(message, points, total):
    feed_channel = bot.get_channel(GIVEAWAY_FEED_CHANNEL)

    if feed_channel:
        await feed_channel.send(
            f"🎟️ **Giveaway Entry Added**\n"
            f"User: {message.author.mention}\n"
            f"Entries earned: **+{points}**\n"
            f"Monthly total: **{total}**\n"
            f"Source: {message.jump_url}",
            allowed_mentions=discord.AllowedMentions(users=True)
        )


@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Slash command sync failed: {e}")


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

        # GIVEAWAY TRACKING
        data = load_data()
        user_id = str(message.author.id)

        data["entries"].setdefault(user_id, 0)

        if has_photo(message):
            points = PHOTO_ALERT_POINTS
        else:
            points = TEXT_ALERT_POINTS

        data["entries"][user_id] += points

        data["tracked_messages"][str(message.id)] = {
            "user_id": user_id,
            "points": points,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        save_data(data)

        await log_giveaway_entry(
            message,
            points,
            data["entries"][user_id]
        )

        files = await collect_files()

        await message.channel.send(
            content=f"{message.content} {role.mention}",
            files=files,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

        print("In-store reposted")

        return

    print("Channel not mapped")


@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    data = load_data()
    msg_id = str(message.id)

    if msg_id not in data.get("tracked_messages", {}):
        return

    info = data["tracked_messages"][msg_id]

    created_at = datetime.fromisoformat(info["created_at"])
    now = datetime.now(timezone.utc)
    seconds_since_posted = (now - created_at).total_seconds()

    user_id = info["user_id"]
    points = info["points"]

    if seconds_since_posted <= DELETE_GRACE_SECONDS:
        del data["tracked_messages"][msg_id]
        save_data(data)
        return

    data["entries"][user_id] = max(0, data["entries"].get(user_id, 0) - points)

    del data["tracked_messages"][msg_id]
    save_data(data)

    feed_channel = bot.get_channel(GIVEAWAY_FEED_CHANNEL)

    if feed_channel:
        await feed_channel.send(
            f"⚠️ **Giveaway Entry Removed**\n"
            f"User: <@{user_id}>\n"
            f"Removed: **-{points}** entries\n"
            f"Reason: Original in-store alert was deleted\n"
            f"Monthly total: **{data['entries'][user_id]}**",
            allowed_mentions=discord.AllowedMentions(users=True)
        )


@bot.tree.command(name="entries", description="Check your monthly giveaway entries")
async def entries(interaction: discord.Interaction):
    data = load_data()
    user_id = str(interaction.user.id)
    total = data["entries"].get(user_id, 0)

    await interaction.response.send_message(
        f"🎟️ You have **{total}** giveaway entries this month.",
        ephemeral=True
    )


@bot.tree.command(name="leaderboard", description="Show the monthly giveaway leaderboard")
async def leaderboard(interaction: discord.Interaction):
    data = load_data()

    if not data["entries"]:
        await interaction.response.send_message("No giveaway entries yet this month.")
        return

    sorted_entries = sorted(
        data["entries"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    text = "🏆 **Monthly Giveaway Leaderboard**\n\n"

    for index, (user_id, points) in enumerate(sorted_entries, start=1):
        text += f"**{index}.** <@{user_id}> — **{points} entries**\n"

    await interaction.response.send_message(
        text,
        allowed_mentions=discord.AllowedMentions(users=True)
    )


@bot.tree.command(name="draw", description="Draw a weighted giveaway winner")
async def draw(interaction: discord.Interaction):
    if not is_giveaway_admin(interaction.user):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    data = load_data()
    tickets = []

    for user_id, points in data["entries"].items():
        tickets.extend([user_id] * points)

    if not tickets:
        await interaction.response.send_message("No entries available to draw from.")
        return

    winner_id = random.choice(tickets)

    await interaction.response.send_message(
        f"🎉 **Giveaway Winner:** <@{winner_id}>\n"
        f"🎟️ Entries: **{data['entries'][winner_id]}**",
        allowed_mentions=discord.AllowedMentions(users=True)
    )

    winners_channel = bot.get_channel(WINNERS_CHANNEL)

    if winners_channel:
        await winners_channel.send(
            f"🏆 **Monthly Giveaway Winner**\n"
            f"Winner: <@{winner_id}>\n"
            f"Entries: **{data['entries'][winner_id]}**\n"
            f"Month: **{data['month']}**",
            allowed_mentions=discord.AllowedMentions(users=True)
        )


@bot.tree.command(name="resetmonth", description="Reset giveaway entries for the month")
async def resetmonth(interaction: discord.Interaction):
    if not is_giveaway_admin(interaction.user):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    data = default_data()
    save_data(data)

    await interaction.response.send_message(
        "✅ Monthly giveaway entries have been reset."
    )


bot.run(TOKEN)
