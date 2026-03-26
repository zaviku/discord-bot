import discord
from discord.ext import commands, tasks
import json
import os
import time
import aiohttp
import random
from datetime import timedelta, datetime

# ============================================================
#   AHMED'S DISCORD BOT
#   Features: Levels, XP, Level Roles, Twitch Notifications,
#   Daily Rewards, Trivia, User Profiles, Birthday Announcements
# ============================================================

CONFIG_FILE = "config.json"
DATA_FILE = "data.json"

TWITCH_CHANNEL = "ahmed_a_030"
TWITCH_LINK = "https://www.twitch.tv/ahmed_a_030"

LEVEL_ROLES = {
    1: "Level 1",
    5: "Level 5",
    10: "Level 10"
}

DAILY_XP = 50
DAILY_POINTS = 200
TRIVIA_CHANNEL = "bot-commands"
TRIVIA_XP_REWARD = 20
TRIVIA_POINTS_REWARD = 50
TRIVIA_TIMEOUT = 30

# ============================================================
#   TRIVIA QUESTIONS (randomised, normal difficulty)
# ============================================================

TRIVIA_QUESTIONS = [
    {"q": "What is the capital of France?", "a": "paris"},
    {"q": "How many sides does a hexagon have?", "a": "6"},
    {"q": "What planet is known as the Red Planet?", "a": "mars"},
    {"q": "What is the largest ocean on Earth?", "a": "pacific"},
    {"q": "How many players are on a football (soccer) team?", "a": "11"},
    {"q": "What gas do plants absorb from the atmosphere?", "a": "carbon dioxide"},
    {"q": "What is the fastest land animal?", "a": "cheetah"},
    {"q": "How many continents are there on Earth?", "a": "7"},
    {"q": "What is the chemical symbol for water?", "a": "h2o"},
    {"q": "In what country was the game Minecraft created?", "a": "sweden"},
    {"q": "What is the largest planet in our solar system?", "a": "jupiter"},
    {"q": "How many bones are in the adult human body?", "a": "206"},
    {"q": "What is the capital of Japan?", "a": "tokyo"},
    {"q": "Who invented the telephone?", "a": "alexander graham bell"},
    {"q": "What is the square root of 144?", "a": "12"},
    {"q": "What colour is the sky on a clear day?", "a": "blue"},
    {"q": "What is the longest river in the world?", "a": "nile"},
    {"q": "How many hours are in a day?", "a": "24"},
    {"q": "What sport is played at Wimbledon?", "a": "tennis"},
    {"q": "What is the currency of the United Kingdom?", "a": "pound"},
    {"q": "How many strings does a standard guitar have?", "a": "6"},
    {"q": "What is the capital of Australia?", "a": "canberra"},
    {"q": "What is the hardest natural substance on Earth?", "a": "diamond"},
    {"q": "How many months are in a year?", "a": "12"},
    {"q": "What language has the most native speakers in the world?", "a": "mandarin"},
    {"q": "What is the name of the closest star to Earth?", "a": "sun"},
    {"q": "How many players are on a basketball team?", "a": "5"},
    {"q": "What is the capital of Germany?", "a": "berlin"},
    {"q": "What year did World War 2 end?", "a": "1945"},
    {"q": "What is the smallest country in the world?", "a": "vatican city"},
    {"q": "How many days are in a leap year?", "a": "366"},
    {"q": "What is the name of the main character in Minecraft?", "a": "steve"},
    {"q": "What is the capital of the United States?", "a": "washington dc"},
    {"q": "How many wheels does a tricycle have?", "a": "3"},
    {"q": "What ocean is the Titanic at the bottom of?", "a": "atlantic"},
    {"q": "What is the most spoken language in Brazil?", "a": "portuguese"},
    {"q": "What is the tallest mountain in the world?", "a": "mount everest"},
    {"q": "How many zeros are in one million?", "a": "6"},
    {"q": "What is the capital of Spain?", "a": "madrid"},
    {"q": "What colour are emeralds?", "a": "green"},
]

# Track recently used questions per guild to avoid repeats
recent_trivia = {}
active_trivia = {}

# ============================================================
#   DATA AND CONFIG HELPERS
# ============================================================

def get_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "xp": {},
        "points": {},
        "joined_before": [],
        "twitch_live": False,
        "daily_claimed": {},
        "birthdays": {},
        "birthday_announced": {}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def ensure_keys(data):
    for key in ["xp", "points", "joined_before", "daily_claimed", "birthdays", "birthday_announced"]:
        if key not in data:
            if key == "joined_before":
                data[key] = []
            else:
                data[key] = {}
    if "twitch_live" not in data:
        data["twitch_live"] = False
    return data

xp_cooldowns = {}

def get_level(total_xp):
    return total_xp // 100

def xp_for_next_level(total_xp):
    current_level = get_level(total_xp)
    return (current_level + 1) * 100 - total_xp

def is_mod(member):
    config = get_config()
    mod_roles = config.get("mod_roles", [])
    return any(role.name in mod_roles for role in member.roles) or member.guild_permissions.administrator

# ============================================================
#   BOT SETUP
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

config = get_config()
bot = commands.Bot(command_prefix=config["prefix"], intents=intents, help_command=None)

# ============================================================
#   TWITCH LIVE CHECKER
# ============================================================

async def get_twitch_token():
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET")
    url = "https://id.twitch.tv/oauth2/token"
    params = {"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as resp:
            data = await resp.json()
            return data.get("access_token")

async def check_twitch_live():
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    token = await get_twitch_token()
    if not token:
        return False
    headers = {"Client-ID": client_id, "Authorization": f"Bearer {token}"}
    url = f"https://api.twitch.tv/helix/streams?user_login={TWITCH_CHANNEL}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            return len(data.get("data", [])) > 0

@tasks.loop(minutes=2)
async def twitch_check_loop():
    data = load_data()
    try:
        is_live = await check_twitch_live()
    except Exception as e:
        print(f"Twitch check error: {e}")
        return
    was_live = data.get("twitch_live", False)
    if is_live and not was_live:
        data["twitch_live"] = True
        save_data(data)
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name="twitch-announcement")
            if channel:
                embed = discord.Embed(
                    title="ahmed_a_030 is now LIVE on Twitch!",
                    description=f"Come and join the stream!\n\n[Click here to watch]({TWITCH_LINK})",
                    color=discord.Color.purple()
                )
                embed.set_footer(text="Twitch Notification")
                await channel.send("@everyone", embed=embed)
    elif not is_live and was_live:
        data["twitch_live"] = False
        save_data(data)

@twitch_check_loop.before_loop
async def before_twitch_check():
    await bot.wait_until_ready()

# ============================================================
#   BIRTHDAY CHECKER (runs every day at midnight)
# ============================================================

@tasks.loop(hours=24)
async def birthday_check_loop():
    data = load_data()
    data = ensure_keys(data)
    today = datetime.now().strftime("%d/%m")
    year = str(datetime.now().year)

    for guild in bot.guilds:
        guild_id = str(guild.id)
        for user_id, birthday in data["birthdays"].items():
            if birthday == today:
                announced_key = f"{guild_id}_{user_id}_{year}"
                if announced_key not in data["birthday_announced"]:
                    data["birthday_announced"][announced_key] = True
                    save_data(data)
                    channel = discord.utils.get(guild.text_channels, name="announcements")
                    if channel:
                        member = guild.get_member(int(user_id))
                        if member:
                            embed = discord.Embed(
                                title="Happy Birthday!",
                                description=f"Everyone wish {member.mention} a happy birthday today!",
                                color=discord.Color.gold()
                            )
                            embed.set_thumbnail(url=member.display_avatar.url)
                            await channel.send(embed=embed)

@birthday_check_loop.before_loop
async def before_birthday_check():
    await bot.wait_until_ready()

# ============================================================
#   EVENTS
# ============================================================

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    twitch_check_loop.start()
    birthday_check_loop.start()

@bot.event
async def on_member_join(member):
    config = get_config()
    data = load_data()
    data = ensure_keys(data)
    user_id = str(member.id)
    if user_id not in data["joined_before"]:
        data["joined_before"].append(user_id)
        save_data(data)
        channel = discord.utils.get(member.guild.text_channels, name=config["welcome_channel"])
        if channel:
            embed = discord.Embed(
                title=f"Welcome to {member.guild.name}!",
                description=(
                    f"Hey {member.mention}, welcome to the server!\n\n"
                    f"Head over to **#get-roles** to pick your roles.\n"
                    f"Chat in the server to earn XP and level up.\n"
                    f"Use **?help** to see what commands are available.\n\n"
                    f"Enjoy your stay!"
                ),
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{member.guild.member_count}")
            await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    config = get_config()
    data = load_data()
    data = ensure_keys(data)

    user_id = str(message.author.id)
    guild_id = str(message.guild.id)
    cooldown_key = f"{guild_id}_{user_id}"
    now = time.time()

    if guild_id not in data["xp"]:
        data["xp"][guild_id] = {}
    if user_id not in data["xp"][guild_id]:
        data["xp"][guild_id][user_id] = 0
    if guild_id not in data["points"]:
        data["points"][guild_id] = {}
    if user_id not in data["points"][guild_id]:
        data["points"][guild_id][user_id] = 0

    if cooldown_key not in xp_cooldowns or now - xp_cooldowns[cooldown_key] >= config["xp_cooldown_seconds"]:
        xp_cooldowns[cooldown_key] = now
        old_xp = data["xp"][guild_id][user_id]
        old_level = get_level(old_xp)
        data["xp"][guild_id][user_id] += config["xp_per_message"]
        new_xp = data["xp"][guild_id][user_id]
        new_level = get_level(new_xp)
        save_data(data)

        if new_level > old_level:
            level_channel = discord.utils.get(message.guild.text_channels, name="leveling-annoucements")
            if level_channel:
                await level_channel.send(f"{message.author.mention} has reached **Level {new_level}**!")
            if new_level in LEVEL_ROLES:
                role_name = LEVEL_ROLES[new_level]
                role = discord.utils.get(message.guild.roles, name=role_name)
                if role:
                    roles_to_remove = []
                    for lvl, rname in LEVEL_ROLES.items():
                        if lvl < new_level:
                            old_role = discord.utils.get(message.guild.roles, name=rname)
                            if old_role and old_role in message.author.roles:
                                roles_to_remove.append(old_role)
                    if roles_to_remove:
                        await message.author.remove_roles(*roles_to_remove)
                    await message.author.add_roles(role)

    # ---- Trivia answer checker ----
    if guild_id in active_trivia:
        trivia = active_trivia[guild_id]
        if message.channel.id == trivia["channel_id"] and not message.author.bot:
            if message.content.strip().lower() == trivia["answer"]:
                del active_trivia[guild_id]
                data = load_data()
                data = ensure_keys(data)
                if guild_id not in data["xp"]:
                    data["xp"][guild_id] = {}
                if user_id not in data["xp"][guild_id]:
                    data["xp"][guild_id][user_id] = 0
                if guild_id not in data["points"]:
                    data["points"][guild_id] = {}
                if user_id not in data["points"][guild_id]:
                    data["points"][guild_id][user_id] = 0
                data["xp"][guild_id][user_id] += TRIVIA_XP_REWARD
                data["points"][guild_id][user_id] += TRIVIA_POINTS_REWARD
                save_data(data)
                embed = discord.Embed(
                    title="Correct!",
                    description=(
                        f"{message.author.mention} got it right!\n"
                        f"The answer was **{trivia['answer'].title()}**\n\n"
                        f"+{TRIVIA_XP_REWARD} XP and +{TRIVIA_POINTS_REWARD} points awarded!"
                    ),
                    color=discord.Color.green()
                )
                await message.channel.send(embed=embed)

    await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    config = get_config()
    rr = config.get("reaction_roles", {})
    stored_message_id = rr.get("message_id")
    if stored_message_id and str(payload.message_id) == str(stored_message_id):
        emoji = str(payload.emoji)
        role_name = rr["mapping"].get(emoji)
        if role_name:
            guild = bot.get_guild(payload.guild_id)
            role = discord.utils.get(guild.roles, name=role_name)
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.add_roles(role)

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return
    config = get_config()
    rr = config.get("reaction_roles", {})
    stored_message_id = rr.get("message_id")
    if stored_message_id and str(payload.message_id) == str(stored_message_id):
        emoji = str(payload.emoji)
        role_name = rr["mapping"].get(emoji)
        if role_name:
            guild = bot.get_guild(payload.guild_id)
            role = discord.utils.get(guild.roles, name=role_name)
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.remove_roles(role)

# ============================================================
#   USER COMMANDS
# ============================================================

@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(title="Bot Commands", description="Prefix for all commands is `?`", color=discord.Color.purple())
    embed.add_field(
        name="User Commands",
        value=(
            "`?help` - Shows this command list\n"
            "`?level` - Your level, total XP, and XP needed for next level\n"
            "`?level @user` - Check another user's level\n"
            "`?leaderboard` - Top 10 XP earners\n"
            "`?profile` - View your full profile\n"
            "`?profile @user` - View another user's profile\n"
            "`?daily` - Claim your daily XP and points reward\n"
            "`?birthday DD/MM` - Register your birthday\n"
        ),
        inline=False
    )
    embed.add_field(
        name="Mod Commands",
        value=(
            "`?trivia` - Start a trivia question in #bot-commands\n"
            "`?timeout @user [minutes] [reason]` - Timeout a member\n"
            "`?untimeout @user` - Remove a timeout\n"
            "`?mute @user [reason]` - Mute a member\n"
            "`?unmute @user` - Unmute a member\n"
            "`?kick @user [reason]` - Kick a member\n"
            "`?ban @user [reason]` - Ban a member\n"
            "`?warn @user [reason]` - Warn a member via DM\n"
            "`?purge [amount]` - Delete up to 100 messages\n"
            "`?setuproles` - Post the reaction roles message\n"
            "`?setxp [amount]` - Change XP earned per message\n"
            "`?setcooldown [seconds]` - Change XP cooldown\n"
        ),
        inline=False
    )
    embed.add_field(
        name="Level Roles",
        value="Level 1 → `Level 1` role\nLevel 5 → `Level 5` role\nLevel 10 → `Level 10` role",
        inline=False
    )
    embed.set_footer(text="Mod commands require a Moderator, Admin, or Owner role")
    await ctx.send(embed=embed)

@bot.command(name="level")
async def level_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_data()
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    total_xp = data.get("xp", {}).get(guild_id, {}).get(user_id, 0)
    current_level = get_level(total_xp)
    xp_needed = xp_for_next_level(total_xp)
    embed = discord.Embed(title=f"{member.display_name}'s Level", color=discord.Color.purple())
    embed.add_field(name="Level", value=str(current_level), inline=True)
    embed.add_field(name="Total XP", value=str(total_xp), inline=True)
    embed.add_field(name="Progress to Next Level", value=f"{xp_needed} XP needed to reach Level {current_level + 1}", inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb"])
async def leaderboard(ctx):
    data = load_data()
    guild_id = str(ctx.guild.id)
    guild_xp = data.get("xp", {}).get(guild_id, {})
    if not guild_xp:
        await ctx.send("No XP data yet. Start chatting to earn XP!")
        return
    sorted_users = sorted(guild_xp.items(), key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title="XP Leaderboard", color=discord.Color.gold())
    description = ""
    count = 0
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for user_id, xp in sorted_users:
        if count >= 10:
            break
        member = ctx.guild.get_member(int(user_id))
        if not member:
            continue
        count += 1
        rank = medals.get(count, f"**{count}.**")
        description += f"{rank} {member.display_name} — Level {get_level(xp)} | {xp} XP\n"
    embed.description = description if description else "No members with XP found."
    await ctx.send(embed=embed)

@bot.command(name="profile")
async def profile_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    total_xp = data.get("xp", {}).get(guild_id, {}).get(user_id, 0)
    points = data.get("points", {}).get(guild_id, {}).get(user_id, 0)
    current_level = get_level(total_xp)
    xp_needed = xp_for_next_level(total_xp)
    birthday = data.get("birthdays", {}).get(user_id, "Not set")
    joined = member.joined_at.strftime("%d %b %Y") if member.joined_at else "Unknown"

    embed = discord.Embed(title=f"{member.display_name}'s Profile", color=discord.Color.purple())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Level", value=str(current_level), inline=True)
    embed.add_field(name="Total XP", value=str(total_xp), inline=True)
    embed.add_field(name="Points", value=str(points), inline=True)
    embed.add_field(name="XP to Next Level", value=str(xp_needed), inline=True)
    embed.add_field(name="Joined Server", value=joined, inline=True)
    embed.add_field(name="Birthday", value=birthday, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="daily")
async def daily_cmd(ctx):
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    today = datetime.now().strftime("%Y-%m-%d")
    claim_key = f"{guild_id}_{user_id}"

    if data["daily_claimed"].get(claim_key) == today:
        await ctx.send(f"{ctx.author.mention} you have already claimed your daily reward today. Come back tomorrow!")
        return

    data["daily_claimed"][claim_key] = today

    if guild_id not in data["xp"]:
        data["xp"][guild_id] = {}
    if user_id not in data["xp"][guild_id]:
        data["xp"][guild_id][user_id] = 0
    if guild_id not in data["points"]:
        data["points"][guild_id] = {}
    if user_id not in data["points"][guild_id]:
        data["points"][guild_id][user_id] = 0

    data["xp"][guild_id][user_id] += DAILY_XP
    data["points"][guild_id][user_id] += DAILY_POINTS
    save_data(data)

    embed = discord.Embed(
        title="Daily Reward Claimed!",
        description=(
            f"{ctx.author.mention} claimed their daily reward!\n\n"
            f"+**{DAILY_XP} XP**\n"
            f"+**{DAILY_POINTS} Points**\n\n"
            f"Come back tomorrow for another reward!"
        ),
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="birthday")
async def birthday_cmd(ctx, date: str = None):
    if not date:
        await ctx.send("Please provide your birthday in DD/MM format. Example: `?birthday 25/03`")
        return
    try:
        datetime.strptime(date, "%d/%m")
    except ValueError:
        await ctx.send("Invalid date format. Please use DD/MM. Example: `?birthday 25/03`")
        return

    data = load_data()
    data = ensure_keys(data)
    data["birthdays"][str(ctx.author.id)] = date
    save_data(data)
    await ctx.send(f"{ctx.author.mention} your birthday has been set to **{date}**. We will announce it on the day!")

# ============================================================
#   MOD COMMANDS
# ============================================================

def mod_only():
    async def predicate(ctx):
        if not is_mod(ctx.author):
            await ctx.send("You do not have permission to use this command.")
            return False
        return True
    return commands.check(predicate)

async def log_action(guild, action, user, moderator, reason, duration=None):
    config = get_config()
    log_channel = discord.utils.get(guild.text_channels, name=config["mod_log_channel"])
    if log_channel:
        embed = discord.Embed(title=f"Mod Action: {action}", color=discord.Color.red())
        embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Moderator", value=str(moderator), inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        if duration:
            embed.add_field(name="Duration", value=duration, inline=False)
        await log_channel.send(embed=embed)

@bot.command(name="trivia")
@mod_only()
async def trivia_cmd(ctx):
    guild_id = str(ctx.guild.id)

    if guild_id in active_trivia:
        await ctx.send("A trivia question is already active. Wait for it to finish first.")
        return

    trivia_channel = discord.utils.get(ctx.guild.text_channels, name=TRIVIA_CHANNEL)
    if not trivia_channel:
        await ctx.send(f"Could not find a channel named **{TRIVIA_CHANNEL}**. Please create it first.")
        return

    # Pick a random question avoiding recent repeats
    if guild_id not in recent_trivia:
        recent_trivia[guild_id] = []

    available = [q for q in TRIVIA_QUESTIONS if q["q"] not in recent_trivia[guild_id]]
    if not available:
        recent_trivia[guild_id] = []
        available = TRIVIA_QUESTIONS

    question = random.choice(available)
    recent_trivia[guild_id].append(question["q"])
    if len(recent_trivia[guild_id]) > 10:
        recent_trivia[guild_id].pop(0)

    active_trivia[guild_id] = {
        "answer": question["a"],
        "channel_id": trivia_channel.id
    }

    embed = discord.Embed(
        title="Trivia Time!",
        description=(
            f"{question['q']}\n\n"
            f"First person to type the correct answer wins "
            f"**{TRIVIA_XP_REWARD} XP** and **{TRIVIA_POINTS_REWARD} points**!\n"
            f"You have {TRIVIA_TIMEOUT} seconds!"
        ),
        color=discord.Color.blue()
    )
    await trivia_channel.send(embed=embed)

    await discord.utils.sleep_until(
        datetime.now() + timedelta(seconds=TRIVIA_TIMEOUT)
    )

    if guild_id in active_trivia:
        del active_trivia[guild_id]
        await trivia_channel.send(
            f"Time is up! Nobody got it. The answer was **{question['a'].title()}**."
        )

@bot.command(name="timeout")
@mod_only()
async def timeout_cmd(ctx, member: discord.Member, minutes: int = 10, *, reason="No reason provided"):
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"{member.mention} has been timed out for {minutes} minutes. Reason: {reason}")
    await log_action(ctx.guild, "Timeout", member, ctx.author, reason, f"{minutes} minutes")

@bot.command(name="untimeout")
@mod_only()
async def untimeout_cmd(ctx, member: discord.Member, *, reason="Timeout removed"):
    await member.timeout(None, reason=reason)
    await ctx.send(f"{member.mention}'s timeout has been removed.")
    await log_action(ctx.guild, "Timeout Removed", member, ctx.author, reason)

@bot.command(name="mute")
@mod_only()
async def mute_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False, speak=False, add_reactions=False)
    if mute_role in member.roles:
        await ctx.send(f"{member.mention} is already muted.")
        return
    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f"{member.mention} has been muted. Reason: {reason}")
    await log_action(ctx.guild, "Mute", member, ctx.author, reason)

@bot.command(name="unmute")
@mod_only()
async def unmute_cmd(ctx, member: discord.Member):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role and mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f"{member.mention} has been unmuted.")
        await log_action(ctx.guild, "Unmute", member, ctx.author, "Unmuted by moderator")
    else:
        await ctx.send(f"{member.mention} is not muted.")

@bot.command(name="kick")
@mod_only()
async def kick_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"{member.mention} has been kicked. Reason: {reason}")
    await log_action(ctx.guild, "Kick", member, ctx.author, reason)

@bot.command(name="ban")
@mod_only()
async def ban_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"{member.mention} has been banned. Reason: {reason}")
    await log_action(ctx.guild, "Ban", member, ctx.author, reason)

@bot.command(name="warn")
@mod_only()
async def warn_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    try:
        await member.send(f"You have received a warning in **{ctx.guild.name}**.\nReason: {reason}")
    except discord.Forbidden:
        await ctx.send(f"Could not DM {member.mention} but warning has been logged.")
    await ctx.send(f"{member.mention} has been warned. Reason: {reason}")
    await log_action(ctx.guild, "Warning", member, ctx.author, reason)

@bot.command(name="purge")
@mod_only()
async def purge_cmd(ctx, amount: int = 10):
    if amount < 1 or amount > 100:
        await ctx.send("Please specify a number between 1 and 100.")
        return
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"Deleted {amount} messages.")
    await msg.delete(delay=3)

@bot.command(name="setxp")
@mod_only()
async def setxp_cmd(ctx, amount: int):
    config = get_config()
    config["xp_per_message"] = amount
    save_config(config)
    await ctx.send(f"XP per message updated to **{amount}**. No restart needed.")

@bot.command(name="setcooldown")
@mod_only()
async def setcooldown_cmd(ctx, seconds: int):
    config = get_config()
    config["xp_cooldown_seconds"] = seconds
    save_config(config)
    await ctx.send(f"XP cooldown updated to **{seconds} seconds**. No restart needed.")

@bot.command(name="setuproles")
@mod_only()
async def setup_roles(ctx):
    config = get_config()
    rr = config.get("reaction_roles", {})
    mapping = rr.get("mapping", {})
    channel = discord.utils.get(ctx.guild.text_channels, name=config["get_roles_channel"])
    if not channel:
        await ctx.send(f"Could not find a channel named **{config['get_roles_channel']}**. Please create it first.")
        return
    for emoji, role_name in mapping.items():
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.guild.create_role(name=role_name)
            await ctx.send(f"Created missing role: **{role_name}**")
    description = "React below to receive your role.\n\n**What is your gender?**\n"
    for emoji, role_name in mapping.items():
        description += f"{emoji} — {role_name}\n"
    description += "\nYou can remove your reaction at any time to remove the role."
    embed = discord.Embed(title="Get Your Roles", description=description, color=discord.Color.purple())
    msg = await channel.send(embed=embed)
    for emoji in mapping.keys():
        await msg.add_reaction(emoji)
    config["reaction_roles"]["message_id"] = str(msg.id)
    save_config(config)
    await ctx.send(f"Reaction roles message posted in {channel.mention}.")

# ============================================================
#   ERROR HANDLING
# ============================================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("That member could not be found. Try mentioning them with @.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing a required argument. Use `?help` to see correct usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument. Make sure you are mentioning a valid user.")
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        print(f"Unhandled error: {error}")

# ============================================================
#   RUN BOT
# ============================================================

bot.run(os.environ.get("TOKEN"))
