import discord
from discord.ext import commands, tasks
import json
import os
import time
import aiohttp
import random
import string
import asyncio
from datetime import timedelta, datetime

# ============================================================
#   AHMED'S DISCORD BOT
#   Added: Warning history, Anti-raid, Server suggestions,
#   Word of the day
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
BOT_LOGS_CHANNEL = "bot-logs"
MOD_ONLY_CHANNEL = "moderator-only"
SUGGESTION_INPUT_CHANNEL = "server-suggestion"
SUGGESTION_OUTPUT_CHANNEL = "\U0001f44d-suggestions"
SUGGESTION_THRESHOLD = 5
WOTD_CHANNEL = "word-of-the-day"
ANTI_RAID_THRESHOLD = 5
ANTI_RAID_SECONDS = 30

# ============================================================
#   WORD OF THE DAY LIST
# ============================================================

WORD_OF_THE_DAY_LIST = [
    {"word": "Ephemeral", "type": "adjective", "definition": "Lasting for a very short time.", "example": "The ephemeral beauty of cherry blossoms makes them even more special."},
    {"word": "Serendipity", "type": "noun", "definition": "The occurrence of happy events by chance.", "example": "It was pure serendipity that they met at the airport."},
    {"word": "Resilient", "type": "adjective", "definition": "Able to recover quickly from difficulties.", "example": "She was resilient enough to rebuild her life after the setback."},
    {"word": "Labyrinth", "type": "noun", "definition": "A complicated network of paths in which it is difficult to find your way.", "example": "The old city was a labyrinth of narrow streets."},
    {"word": "Melancholy", "type": "noun/adjective", "definition": "A deep, pensive sadness.", "example": "A sense of melancholy washed over him as he left his hometown."},
    {"word": "Eloquent", "type": "adjective", "definition": "Fluent and persuasive in speaking or writing.", "example": "Her eloquent speech moved the entire audience."},
    {"word": "Tenacious", "type": "adjective", "definition": "Holding firmly to something, refusing to give up.", "example": "His tenacious attitude helped him finish the marathon."},
    {"word": "Paradox", "type": "noun", "definition": "A statement that seems contradictory but may be true.", "example": "The paradox of choice is that having too many options can make you less happy."},
    {"word": "Wanderlust", "type": "noun", "definition": "A strong desire to travel and explore the world.", "example": "Her wanderlust took her across six continents before she turned 30."},
    {"word": "Catharsis", "type": "noun", "definition": "The release of strong emotions, often bringing a sense of relief.", "example": "Crying during the film provided a catharsis she did not expect."},
    {"word": "Magnanimous", "type": "adjective", "definition": "Generous and forgiving, especially towards a rival.", "example": "The champion was magnanimous in victory, praising his opponent."},
    {"word": "Enigmatic", "type": "adjective", "definition": "Mysterious and difficult to understand.", "example": "His enigmatic smile left everyone wondering what he was thinking."},
    {"word": "Juxtapose", "type": "verb", "definition": "To place two things side by side to highlight their differences.", "example": "The film juxtaposes wealth and poverty to make a powerful point."},
    {"word": "Euphoria", "type": "noun", "definition": "An intense feeling of happiness and excitement.", "example": "Winning the championship filled the team with pure euphoria."},
    {"word": "Stoic", "type": "adjective", "definition": "Enduring pain or hardship without showing emotion.", "example": "He remained stoic throughout the difficult operation."},
    {"word": "Hubris", "type": "noun", "definition": "Excessive pride or self-confidence that leads to downfall.", "example": "His hubris led him to underestimate his opponent."},
    {"word": "Solitude", "type": "noun", "definition": "The state of being alone, often in a peaceful way.", "example": "She found solitude in long walks through the forest."},
    {"word": "Vicarious", "type": "adjective", "definition": "Experienced through another person rather than directly.", "example": "He lived vicariously through the adventures in his favourite novels."},
    {"word": "Ambivalent", "type": "adjective", "definition": "Having mixed or contradictory feelings about something.", "example": "She felt ambivalent about moving to a new city."},
    {"word": "Catalyst", "type": "noun", "definition": "Something that triggers or speeds up a change or event.", "example": "The invention of the internet was a catalyst for enormous social change."},
    {"word": "Nostalgia", "type": "noun", "definition": "A sentimental longing for the past.", "example": "The old song filled him with nostalgia for his school days."},
    {"word": "Pragmatic", "type": "adjective", "definition": "Dealing with things sensibly and practically.", "example": "She took a pragmatic approach to solving the budget problem."},
    {"word": "Eloquence", "type": "noun", "definition": "The quality of being clear, expressive, and persuasive.", "example": "His eloquence made even complex topics easy to understand."},
    {"word": "Clandestine", "type": "adjective", "definition": "Done in secret, especially for illegal reasons.", "example": "They held clandestine meetings in an abandoned warehouse."},
    {"word": "Integrity", "type": "noun", "definition": "The quality of being honest and having strong moral principles.", "example": "Her integrity made her one of the most trusted people in the company."},
    {"word": "Byzantine", "type": "adjective", "definition": "Excessively complicated and difficult to understand.", "example": "The tax system was so byzantine that most people needed professional help."},
    {"word": "Verbose", "type": "adjective", "definition": "Using more words than are needed.", "example": "His verbose explanation confused rather than helped the audience."},
    {"word": "Altruistic", "type": "adjective", "definition": "Showing selfless concern for others.", "example": "Her altruistic nature led her to donate most of her earnings to charity."},
    {"word": "Dichotomy", "type": "noun", "definition": "A division into two opposite or contrasting groups.", "example": "There is a clear dichotomy between rural and urban life in that country."},
    {"word": "Zeitgeist", "type": "noun", "definition": "The defining mood or spirit of a particular period in history.", "example": "Social media perfectly captures the zeitgeist of the 21st century."},
    {"word": "Pensive", "type": "adjective", "definition": "Deeply thoughtful, sometimes with a hint of sadness.", "example": "She sat by the window in a pensive mood, staring at the rain."},
    {"word": "Ubiquitous", "type": "adjective", "definition": "Present, appearing, or found everywhere.", "example": "Smartphones have become ubiquitous in modern life."},
    {"word": "Lethargic", "type": "adjective", "definition": "Sluggish and lacking energy.", "example": "The heat made everyone feel lethargic and unmotivated."},
    {"word": "Inception", "type": "noun", "definition": "The beginning or establishment of something.", "example": "Since its inception, the club has grown to over a thousand members."},
    {"word": "Empathy", "type": "noun", "definition": "The ability to understand and share the feelings of another.", "example": "Great leaders often have a strong sense of empathy towards their team."},
    {"word": "Obsolete", "type": "adjective", "definition": "No longer in use or no longer useful.", "example": "Fax machines have become largely obsolete in the digital age."},
    {"word": "Volatile", "type": "adjective", "definition": "Liable to change rapidly and unpredictably.", "example": "The stock market was particularly volatile during the crisis."},
    {"word": "Profound", "type": "adjective", "definition": "Having great depth of knowledge or meaning.", "example": "The documentary had a profound impact on how she viewed the world."},
    {"word": "Ambiguous", "type": "adjective", "definition": "Open to more than one interpretation.", "example": "The contract contained several ambiguous clauses that caused confusion."},
    {"word": "Diligent", "type": "adjective", "definition": "Careful and persistent in work or effort.", "example": "Her diligent revision paid off when she aced all her exams."},
]

# ============================================================
#   SAFE JSON STORAGE
# ============================================================

def get_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Config load error: {e}")
        return {}

def save_config(config):
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(config, f, indent=4)
    os.replace(tmp, CONFIG_FILE)

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Data load error: {e}")
    return {}

def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, DATA_FILE)

def ensure_keys(data):
    defaults = {
        "xp": {},
        "points": {},
        "joined_before": [],
        "twitch_live": False,
        "daily_claimed": {},
        "birthdays": {},
        "birthday_announced": {},
        "warnings": {},
        "promoted_suggestions": [],
        "wotd_used": []
    }
    for key, default in defaults.items():
        if key not in data:
            data[key] = default
    return data

def validate_config():
    required_keys = [
        "prefix", "welcome_channel", "level_up_channel",
        "mod_log_channel", "get_roles_channel",
        "xp_per_message", "xp_cooldown_seconds",
        "reaction_roles", "mod_roles"
    ]
    config = get_config()
    missing = [k for k in required_keys if k not in config]
    if missing:
        print(f"WARNING: Missing config keys: {missing}")
    else:
        print("Config validated successfully.")

# ============================================================
#   HELPERS
# ============================================================

xp_cooldowns = {}
recent_trivia = {}
active_trivia = {}
raid_tracker = {}

def get_level(total_xp):
    return total_xp // 100

def xp_for_next_level(total_xp):
    return (get_level(total_xp) + 1) * 100 - total_xp

def is_mod(member):
    config = get_config()
    mod_roles = config.get("mod_roles", [])
    return any(role.name in mod_roles for role in member.roles) or member.guild_permissions.administrator

def clean_answer(text):
    return text.lower().strip().translate(str.maketrans("", "", string.punctuation))

async def log_command(guild, user, command_name, extra=""):
    channel = discord.utils.get(guild.text_channels, name=BOT_LOGS_CHANNEL)
    if channel:
        role_label = "Mod" if is_mod(user) else "User"
        embed = discord.Embed(
            description=f"**{user.display_name}** used `?{command_name}` {extra}".strip(),
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"{role_label} • {datetime.now().strftime('%H:%M:%S')}")
        await channel.send(embed=embed)

async def log_action(guild, action, user, moderator, reason, duration=None):
    config = get_config()
    log_channel = discord.utils.get(guild.text_channels, name=config.get("mod_log_channel", "mod-logs"))
    if log_channel:
        embed = discord.Embed(title=f"Mod Action: {action}", color=discord.Color.red())
        embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Moderator", value=str(moderator), inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        if duration:
            embed.add_field(name="Duration", value=duration, inline=False)
        await log_channel.send(embed=embed)

# ============================================================
#   BOT SETUP
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

config = get_config()
bot = commands.Bot(command_prefix=config.get("prefix", "?"), intents=intents, help_command=None)

# ============================================================
#   TWITCH LIVE CHECKER
# ============================================================

async def get_twitch_token():
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    params = {"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"}
    async with aiohttp.ClientSession() as session:
        async with session.post("https://id.twitch.tv/oauth2/token", params=params) as resp:
            return (await resp.json()).get("access_token")

async def check_twitch_live():
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    token = await get_twitch_token()
    if not token:
        return False
    headers = {"Client-ID": client_id, "Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.twitch.tv/helix/streams?user_login={TWITCH_CHANNEL}", headers=headers) as resp:
            return len((await resp.json()).get("data", [])) > 0

@tasks.loop(minutes=2)
async def twitch_check_loop():
    data = load_data()
    data = ensure_keys(data)
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
async def before_twitch():
    await bot.wait_until_ready()

# ============================================================
#   BIRTHDAY CHECKER
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
async def before_birthday():
    await bot.wait_until_ready()
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    await asyncio.sleep((midnight - now).total_seconds())

# ============================================================
#   WORD OF THE DAY
# ============================================================

@tasks.loop(hours=24)
async def wotd_loop():
    data = load_data()
    data = ensure_keys(data)

    used = data.get("wotd_used", [])
    available = [w for w in WORD_OF_THE_DAY_LIST if w["word"] not in used]

    if not available:
        data["wotd_used"] = []
        available = WORD_OF_THE_DAY_LIST

    word = random.choice(available)
    data["wotd_used"].append(word["word"])
    save_data(data)

    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=WOTD_CHANNEL)
        if channel:
            embed = discord.Embed(
                title=f"Word of the Day: {word['word']}",
                color=discord.Color.teal()
            )
            embed.add_field(name="Type", value=word["type"], inline=True)
            embed.add_field(name="Definition", value=word["definition"], inline=False)
            embed.add_field(name="Example", value=f"*\"{word['example']}\"*", inline=False)
            embed.set_footer(text="Expand your vocabulary every day!")
            await channel.send(embed=embed)

@wotd_loop.before_loop
async def before_wotd():
    await bot.wait_until_ready()
    now = datetime.now()
    midnight = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now >= midnight:
        midnight += timedelta(days=1)
    await asyncio.sleep((midnight - now).total_seconds())

# ============================================================
#   EVENTS
# ============================================================

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    validate_config()
    if not twitch_check_loop.is_running():
        twitch_check_loop.start()
    if not birthday_check_loop.is_running():
        birthday_check_loop.start()
    if not wotd_loop.is_running():
        wotd_loop.start()

@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    now = time.time()

    # ---- Anti-raid detection ----
    if guild_id not in raid_tracker:
        raid_tracker[guild_id] = []
    raid_tracker[guild_id].append(now)
    raid_tracker[guild_id] = [t for t in raid_tracker[guild_id] if now - t <= ANTI_RAID_SECONDS]

    if len(raid_tracker[guild_id]) >= ANTI_RAID_THRESHOLD:
        raid_tracker[guild_id] = []
        mod_channel = discord.utils.get(member.guild.text_channels, name=MOD_ONLY_CHANNEL)
        if mod_channel:
            embed = discord.Embed(
                title="RAID DETECTED",
                description=(
                    f"**{len(raid_tracker.get(guild_id, [ANTI_RAID_THRESHOLD]))+ANTI_RAID_THRESHOLD} or more accounts** joined within "
                    f"**{ANTI_RAID_SECONDS} seconds**.\n\n"
                    f"Consider enabling server lockdown immediately.\n"
                    f"Use `?lockdown` to prevent new members from chatting."
                ),
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Anti-Raid Alert • {datetime.now().strftime('%H:%M:%S')}")
            config = get_config()
            mod_roles = config.get("mod_roles", [])
            mentions = " ".join([
                role.mention for role in member.guild.roles
                if role.name in mod_roles
            ])
            await mod_channel.send(f"{mentions}", embed=embed)

    # ---- Welcome message ----
    config = get_config()
    data = load_data()
    data = ensure_keys(data)
    user_id = str(member.id)
    if user_id not in data["joined_before"]:
        data["joined_before"].append(user_id)
        save_data(data)
        channel = discord.utils.get(member.guild.text_channels, name=config.get("welcome_channel", "welcome"))
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

    if cooldown_key not in xp_cooldowns or now - xp_cooldowns[cooldown_key] >= config.get("xp_cooldown_seconds", 60):
        xp_cooldowns[cooldown_key] = now
        old_xp = data["xp"][guild_id][user_id]
        old_level = get_level(old_xp)
        data["xp"][guild_id][user_id] += config.get("xp_per_message", 5)
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
                    roles_to_remove = [
                        discord.utils.get(message.guild.roles, name=LEVEL_ROLES[lvl])
                        for lvl in LEVEL_ROLES if lvl < new_level
                        and discord.utils.get(message.guild.roles, name=LEVEL_ROLES[lvl]) in message.author.roles
                    ]
                    roles_to_remove = [r for r in roles_to_remove if r]
                    if roles_to_remove:
                        await message.author.remove_roles(*roles_to_remove)
                    await message.author.add_roles(role)

    # Trivia answer check
    if guild_id in active_trivia:
        trivia = active_trivia[guild_id]
        if message.channel.id == trivia["channel_id"] and not message.author.bot:
            if clean_answer(message.content) == clean_answer(trivia["answer"]):
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

    # ---- Suggestion promotion check ----
    if str(payload.emoji) == "👍":
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        if channel and channel.name == SUGGESTION_INPUT_CHANNEL:
            try:
                message = await channel.fetch_message(payload.message_id)
                thumbs_count = 0
                for reaction in message.reactions:
                    if str(reaction.emoji) == "👍":
                        thumbs_count = reaction.count
                        break

                if thumbs_count >= SUGGESTION_THRESHOLD:
                    data = load_data()
                    data = ensure_keys(data)
                    if str(payload.message_id) not in data["promoted_suggestions"]:
                        data["promoted_suggestions"].append(str(payload.message_id))
                        save_data(data)
                        output_channel = discord.utils.get(guild.text_channels, name=SUGGESTION_OUTPUT_CHANNEL)
                        if output_channel:
                            embed = discord.Embed(
                                title="Popular Suggestion!",
                                description=message.content,
                                color=discord.Color.green()
                            )
                            embed.add_field(name="Suggested by", value=message.author.mention, inline=True)
                            embed.add_field(name="Thumbs up", value=str(thumbs_count), inline=True)
                            embed.set_footer(text="This suggestion reached 5 or more thumbs up!")
                            await output_channel.send(embed=embed)
            except Exception as e:
                print(f"Suggestion check error: {e}")

    # ---- Reaction roles ----
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
    await log_command(ctx.guild, ctx.author, "help")
    user_is_mod = is_mod(ctx.author)
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
    if user_is_mod:
        embed.add_field(
            name="Mod Commands",
            value=(
                "`?trivia` - Start a trivia question in #bot-commands\n"
                "`?warn @user [reason]` - Warn a member via DM\n"
                "`?warnings @user` - View a member's full warning history\n"
                "`?clearwarnings @user` - Clear all warnings for a member\n"
                "`?timeout @user [minutes] [reason]` - Timeout a member\n"
                "`?untimeout @user` - Remove a timeout\n"
                "`?mute @user [reason]` - Mute a member\n"
                "`?unmute @user` - Unmute a member\n"
                "`?kick @user [reason]` - Kick a member\n"
                "`?ban @user [reason]` - Ban a member\n"
                "`?purge [amount]` - Delete up to 100 messages\n"
                "`?setuproles` - Post the reaction roles message\n"
                "`?setxp [amount]` - Change XP earned per message\n"
                "`?setcooldown [seconds]` - Change XP cooldown\n"
                "`?wotd` - Manually trigger word of the day\n"
            ),
            inline=False
        )
    embed.add_field(
        name="Level Roles",
        value="Level 1 → `Level 1` role\nLevel 5 → `Level 5` role\nLevel 10 → `Level 10` role",
        inline=False
    )
    embed.set_footer(text="Mod commands are hidden for regular users" if not user_is_mod else "You are viewing this as a Moderator")
    await ctx.send(embed=embed)

@bot.command(name="level")
async def level_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    await log_command(ctx.guild, ctx.author, "level", f"on {member.display_name}")
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
    await log_command(ctx.guild, ctx.author, "leaderboard")
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
    await log_command(ctx.guild, ctx.author, "profile", f"on {member.display_name}")
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
    warning_count = len(data.get("warnings", {}).get(guild_id, {}).get(user_id, []))
    embed = discord.Embed(title=f"{member.display_name}'s Profile", color=discord.Color.purple())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Level", value=str(current_level), inline=True)
    embed.add_field(name="Total XP", value=str(total_xp), inline=True)
    embed.add_field(name="Points", value=str(points), inline=True)
    embed.add_field(name="XP to Next Level", value=str(xp_needed), inline=True)
    embed.add_field(name="Joined Server", value=joined, inline=True)
    embed.add_field(name="Birthday", value=birthday, inline=True)
    if is_mod(ctx.author):
        embed.add_field(name="Warnings", value=str(warning_count), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="daily")
async def daily_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "daily")
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
    await log_command(ctx.guild, ctx.author, "birthday", date or "")
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

@bot.command(name="warn")
@mod_only()
async def warn_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    await log_command(ctx.guild, ctx.author, "warn", f"on {member.display_name}")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    if guild_id not in data["warnings"]:
        data["warnings"][guild_id] = {}
    if user_id not in data["warnings"][guild_id]:
        data["warnings"][guild_id][user_id] = []

    warning_entry = {
        "reason": reason,
        "moderator": str(ctx.author),
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    data["warnings"][guild_id][user_id].append(warning_entry)
    total_warnings = len(data["warnings"][guild_id][user_id])
    save_data(data)

    try:
        await member.send(f"You have received a warning in **{ctx.guild.name}**.\nReason: {reason}")
    except discord.Forbidden:
        await ctx.send(f"Could not DM {member.mention} but warning has been logged.")

    await ctx.send(f"{member.mention} has been warned. They now have **{total_warnings}** warning(s). Reason: {reason}")
    await log_action(ctx.guild, "Warning", member, ctx.author, reason)

    # Log in bot-logs with total warning count
    bot_log_channel = discord.utils.get(ctx.guild.text_channels, name=BOT_LOGS_CHANNEL)
    if bot_log_channel:
        embed = discord.Embed(
            title="Warning Issued",
            description=f"{member.mention} was warned by {ctx.author.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warnings", value=str(total_warnings), inline=True)
        embed.set_footer(text=datetime.now().strftime("%d/%m/%Y %H:%M"))
        await bot_log_channel.send(embed=embed)

@bot.command(name="warnings")
@mod_only()
async def warnings_cmd(ctx, member: discord.Member):
    await log_command(ctx.guild, ctx.author, "warnings", f"on {member.display_name}")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    user_warnings = data.get("warnings", {}).get(guild_id, {}).get(user_id, [])

    embed = discord.Embed(
        title=f"Warning History — {member.display_name}",
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    if not user_warnings:
        embed.description = "This member has no warnings."
    else:
        embed.description = f"This member has **{len(user_warnings)}** warning(s).\n"
        for i, w in enumerate(user_warnings, 1):
            embed.add_field(
                name=f"Warning {i} — {w.get('timestamp', 'Unknown date')}",
                value=f"**Reason:** {w.get('reason', 'No reason')}\n**By:** {w.get('moderator', 'Unknown')}",
                inline=False
            )
    await ctx.send(embed=embed)

@bot.command(name="clearwarnings")
@mod_only()
async def clearwarnings_cmd(ctx, member: discord.Member):
    await log_command(ctx.guild, ctx.author, "clearwarnings", f"on {member.display_name}")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    if guild_id in data["warnings"] and user_id in data["warnings"][guild_id]:
        data["warnings"][guild_id][user_id] = []
        save_data(data)
        await ctx.send(f"All warnings for {member.mention} have been cleared.")
    else:
        await ctx.send(f"{member.mention} has no warnings to clear.")

@bot.command(name="trivia")
@mod_only()
async def trivia_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "trivia")
    guild_id = str(ctx.guild.id)
    if guild_id in active_trivia:
        await ctx.send("A trivia question is already active. Wait for it to finish first.")
        return
    trivia_channel = discord.utils.get(ctx.guild.text_channels, name=TRIVIA_CHANNEL)
    if not trivia_channel:
        await ctx.send(f"Could not find a channel named **{TRIVIA_CHANNEL}**.")
        return
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
    active_trivia[guild_id] = {"answer": question["a"], "channel_id": trivia_channel.id}
    embed = discord.Embed(
        title="Trivia Time!",
        description=(
            f"{question['q']}\n\n"
            f"First to type the correct answer wins "
            f"**{TRIVIA_XP_REWARD} XP** and **{TRIVIA_POINTS_REWARD} points**!\n"
            f"You have {TRIVIA_TIMEOUT} seconds!"
        ),
        color=discord.Color.blue()
    )
    await trivia_channel.send(embed=embed)
    await asyncio.sleep(TRIVIA_TIMEOUT)
    if guild_id in active_trivia:
        del active_trivia[guild_id]
        await trivia_channel.send(f"Time is up! Nobody got it. The answer was **{question['a'].title()}**.")

@bot.command(name="wotd")
@mod_only()
async def wotd_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "wotd")
    data = load_data()
    data = ensure_keys(data)
    used = data.get("wotd_used", [])
    available = [w for w in WORD_OF_THE_DAY_LIST if w["word"] not in used]
    if not available:
        data["wotd_used"] = []
        available = WORD_OF_THE_DAY_LIST
    word = random.choice(available)
    data["wotd_used"].append(word["word"])
    save_data(data)
    channel = discord.utils.get(ctx.guild.text_channels, name=WOTD_CHANNEL)
    if not channel:
        await ctx.send(f"Could not find a channel named **{WOTD_CHANNEL}**.")
        return
    embed = discord.Embed(title=f"Word of the Day: {word['word']}", color=discord.Color.teal())
    embed.add_field(name="Type", value=word["type"], inline=True)
    embed.add_field(name="Definition", value=word["definition"], inline=False)
    embed.add_field(name="Example", value=f"*\"{word['example']}\"*", inline=False)
    embed.set_footer(text="Expand your vocabulary every day!")
    await channel.send(embed=embed)
    await ctx.send(f"Word of the day posted in {channel.mention}.")

@bot.command(name="timeout")
@mod_only()
async def timeout_cmd(ctx, member: discord.Member, minutes: int = 10, *, reason="No reason provided"):
    await log_command(ctx.guild, ctx.author, "timeout", f"on {member.display_name}")
    try:
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await ctx.send(f"{member.mention} has been timed out for {minutes} minutes. Reason: {reason}")
        await log_action(ctx.guild, "Timeout", member, ctx.author, reason, f"{minutes} minutes")
    except discord.Forbidden:
        await ctx.send("I do not have permission to timeout that member.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")

@bot.command(name="untimeout")
@mod_only()
async def untimeout_cmd(ctx, member: discord.Member, *, reason="Timeout removed"):
    await log_command(ctx.guild, ctx.author, "untimeout", f"on {member.display_name}")
    try:
        await member.timeout(None, reason=reason)
        await ctx.send(f"{member.mention}'s timeout has been removed.")
        await log_action(ctx.guild, "Timeout Removed", member, ctx.author, reason)
    except discord.Forbidden:
        await ctx.send("I do not have permission to remove that timeout.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")

@bot.command(name="mute")
@mod_only()
async def mute_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    await log_command(ctx.guild, ctx.author, "mute", f"on {member.display_name}")
    try:
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
    except discord.Forbidden:
        await ctx.send("I do not have permission to mute that member.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")

@bot.command(name="unmute")
@mod_only()
async def unmute_cmd(ctx, member: discord.Member):
    await log_command(ctx.guild, ctx.author, "unmute", f"on {member.display_name}")
    try:
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if mute_role and mute_role in member.roles:
            await member.remove_roles(mute_role)
            await ctx.send(f"{member.mention} has been unmuted.")
            await log_action(ctx.guild, "Unmute", member, ctx.author, "Unmuted by moderator")
        else:
            await ctx.send(f"{member.mention} is not muted.")
    except discord.Forbidden:
        await ctx.send("I do not have permission to unmute that member.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")

@bot.command(name="kick")
@mod_only()
async def kick_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    await log_command(ctx.guild, ctx.author, "kick", f"on {member.display_name}")
    try:
        await member.kick(reason=reason)
        await ctx.send(f"{member.mention} has been kicked. Reason: {reason}")
        await log_action(ctx.guild, "Kick", member, ctx.author, reason)
    except discord.Forbidden:
        await ctx.send("I do not have permission to kick that member.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")

@bot.command(name="ban")
@mod_only()
async def ban_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    await log_command(ctx.guild, ctx.author, "ban", f"on {member.display_name}")
    try:
        await member.ban(reason=reason)
        await ctx.send(f"{member.mention} has been banned. Reason: {reason}")
        await log_action(ctx.guild, "Ban", member, ctx.author, reason)
    except discord.Forbidden:
        await ctx.send("I do not have permission to ban that member.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")

@bot.command(name="purge")
@mod_only()
async def purge_cmd(ctx, amount: int = 10):
    await log_command(ctx.guild, ctx.author, "purge", f"{amount} messages")
    if amount < 1 or amount > 100:
        await ctx.send("Please specify a number between 1 and 100.")
        return
    try:
        await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"Deleted {amount} messages.")
        await msg.delete(delay=3)
    except discord.Forbidden:
        await ctx.send("I do not have permission to delete messages in this channel.")

@bot.command(name="setxp")
@mod_only()
async def setxp_cmd(ctx, amount: int):
    await log_command(ctx.guild, ctx.author, "setxp", str(amount))
    config = get_config()
    config["xp_per_message"] = amount
    save_config(config)
    await ctx.send(f"XP per message updated to **{amount}**. No restart needed.")

@bot.command(name="setcooldown")
@mod_only()
async def setcooldown_cmd(ctx, seconds: int):
    await log_command(ctx.guild, ctx.author, "setcooldown", str(seconds))
    config = get_config()
    config["xp_cooldown_seconds"] = seconds
    save_config(config)
    await ctx.send(f"XP cooldown updated to **{seconds} seconds**. No restart needed.")

@bot.command(name="setuproles")
@mod_only()
async def setup_roles(ctx):
    await log_command(ctx.guild, ctx.author, "setuproles")
    config = get_config()
    rr = config.get("reaction_roles", {})
    mapping = rr.get("mapping", {})
    channel = discord.utils.get(ctx.guild.text_channels, name=config.get("get_roles_channel", "get-roles"))
    if not channel:
        await ctx.send(f"Could not find a channel named **{config.get('get_roles_channel')}**. Please create it first.")
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
