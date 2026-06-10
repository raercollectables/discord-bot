import discord
from discord.ext import commands, tasks
from discord import app_commands

import os
import json
import random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TOKEN = os.getenv("TOKEN")

AWST = ZoneInfo("Australia/Perth")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

CHANNEL_TO_ROLE = {
    1464844020101419184: 1467959378274681047,
    1464843010050359532: 1467959569400467527,
    1464843455908806666: 1467959606822043832,
    1464843626424172625: 1467960267139842213,
    1464844205628329985: 1467959638413541376,
    1464844447375298713: 1467960394579710015,
    1485255219414831164: 1467960582886920446,
    1464844304961765529: 1467959657942351892,
}

ANNOUNCEMENT_CHANNELS = {
    1466323776756256861,
    1466323977856352349,
    1466324139626332265,
}

RADAR_MEMBER_ROLE = 1467963589330735340

GIVEAWAY_FEED_CHANNEL = 1506346834962944001
GIVEAWAY_ADMIN_ROLE = 1506348836895854712
WINNERS_CHANNEL = 1506345396039979008
LEADERBOARD_CHANNEL = 1506349608945586237

SUCCESS_CHANNEL = 1466324272447488011
TESTIMONIALS_CHANNEL = 1464841969368039700

EXCLUDED_USERS = [
    1461748046416318574
]

TEXT_ALERT_POINTS = 1
PHOTO_ALERT_POINTS = 2
SUCCESS_POINTS = 5
TESTIMONIAL_POINTS = 10
DATA_FILE = "giveaway_entries.json"


def current_month():
    return datetime.now(AWST).strftime("%Y-%m")


def month_title():
    return datetime.now(AWST).strftime("%B %Y").upper()


def default_data():
    return {
        "month": current_month(),
        "entries": {},
        "tracked_messages": {},
        "leaderboard_message_id": None
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
    data.setdefault("leaderboard_message_id", None)

    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def has_photo(message):
    return len(message.attachments) > 0


def is_giveaway_admin(member):
    return any(role.id == GIVEAWAY_ADMIN_ROLE for role in member.roles)


def build_leaderboard_text(data):
    text = f"🏆 **{month_title()} GIVEAWAY LEADERBOARD**\n\n"

    if not data["entries"]:
        text += "No entries yet this month.\n\n"
        text += "Post in-store alerts to earn giveaway entries.\n\n"
        text += "📊 Only the Top 100 members are displayed."
        return text

    sorted_entries = sorted(
        data["entries"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:100]

    medals = ["🥇", "🥈", "🥉"]

    for index, (user_id, points) in enumerate(sorted_entries, start=1):
        medal = medals[index - 1] if index <= 3 else f"**{index}.**"
        text += f"{medal} <@{user_id}> — **{points} entries**\n"

    text += "\n📊 Only the Top 100 members are displayed."
    text += "\nPrevious monthly leaderboards remain in this channel."
    text += "\nUpdates automatically."
    return text


async def update_monthly_leaderboard():
    data = load_data()
    channel = bot.get_channel(LEADERBOARD_CHANNEL)

    if not channel:
        print("Leaderboard channel not found")
        return

    leaderboard_text = build_leaderboard_text(data)

    if data.get("leaderboard_message_id"):
        try:
            msg = await channel.fetch_message(data["leaderboard_message_id"])
            await msg.edit(
                content=leaderboard_text,
                allowed_mentions=discord.AllowedMentions(users=True)
            )
            return
        except Exception as e:
            print(f"Could not edit leaderboard message, creating new one: {e}")

    msg = await channel.send(
        leaderboard_text,
        allowed_mentions=discord.AllowedMentions(users=True)
    )

    data["leaderboard_message_id"] = msg.id
    save_data(data)


@tasks.loop(minutes=1)
async def monthly_reset_checker():
    now = datetime.now(AWST)

    if now.day == 1 and now.hour == 0 and now.minute == 0:
        old_month = None

        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                old_data = json.load(f)
                old_month = old_data.get("month")

        if old_month == current_month():
            return

        data = default_data()
        save_data(data)

        await update_monthly_leaderboard()

        winners_channel = bot.get_channel(WINNERS_CHANNEL)

        if winners_channel:
            await winners_channel.send(
                f"📡 **{month_title()} Giveaway is now live!**\n\n"
                f"Post in-store alerts to earn giveaway entries.\n"
                f"Text alert = **{TEXT_ALERT_POINTS} entry**\n"
                f"Photo alert = **{PHOTO_ALERT_POINTS} entries**\n"
                f"Success post = **{SUCCESS_POINTS} entries**\n"
                f"Testimonial post = **{TESTIMONIAL_POINTS} entries**\n\n"
                f"Check your points in <#{LEADERBOARD_CHANNEL}> and your entries in <#{GIVEAWAY_FEED_CHANNEL}>.\n\n"
                f"📊 Only the Top 100 members are displayed on the leaderboard."
            )


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


async def add_giveaway_entries(message, points):
    if message.author.id in EXCLUDED_USERS:
        print("User is excluded from giveaway entries")
        return

    data = load_data()
    user_id = str(message.author.id)

    data["entries"].setdefault(user_id, 0)
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

    await update_monthly_leaderboard()


@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Slash command sync failed: {e}")

    if not monthly_reset_checker.is_running():
        monthly_reset_checker.start()

    await update_monthly_leaderboard()


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

    if message.channel.id == SUCCESS_CHANNEL:
        print("Matched success channel")

        await add_giveaway_entries(message, SUCCESS_POINTS)
        return

    if message.channel.id == TESTIMONIALS_CHANNEL:
        print("Matched testimonials channel")

        await add_giveaway_entries(message, TESTIMONIAL_POINTS)
        return

    if message.channel.id in CHANNEL_TO_ROLE:
        print("Matched in-store channel")

        role_id = CHANNEL_TO_ROLE[message.channel.id]
        role = message.guild.get_role(role_id)

        if role is None:
            print(f"In-store role not found: {role_id}")
            return

        if has_photo(message):
            points = PHOTO_ALERT_POINTS
        else:
            points = TEXT_ALERT_POINTS

        await add_giveaway_entries(message, points)

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

    user_id = info["user_id"]
    points = info["points"]

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

    await update_monthly_leaderboard()


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
    text = build_leaderboard_text(data)

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

    await update_monthly_leaderboard()

    await interaction.response.send_message(
        "✅ Monthly giveaway entries have been reset and a new leaderboard has been created."
    )


@bot.tree.command(name="giveentries", description="Give giveaway entries to a member")
@app_commands.describe(
    user="User to receive entries",
    amount="Number of entries to give"
)
async def giveentries(
    interaction: discord.Interaction,
    user: discord.Member,
    amount: int
):
    if not is_giveaway_admin(interaction.user):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    if amount <= 0:
        await interaction.response.send_message(
            "❌ Amount must be greater than 0.",
            ephemeral=True
        )
        return

    data = load_data()
    user_id = str(user.id)

    data["entries"].setdefault(user_id, 0)
    data["entries"][user_id] += amount

    save_data(data)
    await update_monthly_leaderboard()

    await interaction.response.send_message(
        f"✅ Added **{amount}** giveaway entries to {user.mention}.\n"
        f"🎟️ New total: **{data['entries'][user_id]}**",
        allowed_mentions=discord.AllowedMentions(users=True)
    )


@bot.tree.command(name="removeentries", description="Remove giveaway entries from a member")
@app_commands.describe(
    user="User to remove entries from",
    amount="Number of entries to remove"
)
async def removeentries(
    interaction: discord.Interaction,
    user: discord.Member,
    amount: int
):
    if not is_giveaway_admin(interaction.user):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    if amount <= 0:
        await interaction.response.send_message(
            "❌ Amount must be greater than 0.",
            ephemeral=True
        )
        return

    data = load_data()
    user_id = str(user.id)

    data["entries"].setdefault(user_id, 0)
    data["entries"][user_id] = max(0, data["entries"][user_id] - amount)

    save_data(data)
    await update_monthly_leaderboard()

    await interaction.response.send_message(
        f"✅ Removed **{amount}** giveaway entries from {user.mention}.\n"
        f"🎟️ New total: **{data['entries'][user_id]}**",
        allowed_mentions=discord.AllowedMentions(users=True)
    )


@bot.tree.command(name="setentries", description="Set a member's giveaway entries")
@app_commands.describe(
    user="User whose entries you want to set",
    amount="Exact number of entries"
)
async def setentries(
    interaction: discord.Interaction,
    user: discord.Member,
    amount: int
):
    if not is_giveaway_admin(interaction.user):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    if amount < 0:
        await interaction.response.send_message(
            "❌ Amount cannot be negative.",
            ephemeral=True
        )
        return

    data = load_data()
    user_id = str(user.id)

    data["entries"][user_id] = amount

    save_data(data)
    await update_monthly_leaderboard()

    await interaction.response.send_message(
        f"✅ Set {user.mention}'s giveaway entries to **{amount}**.",
        allowed_mentions=discord.AllowedMentions(users=True)
    )


bot.run(TOKEN)
