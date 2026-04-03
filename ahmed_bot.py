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
#   Added: RPS with streaks, Gambling, Shop + Inventory,
#   Shields, Steal, UserInfo, updated ?help
# ============================================================

# Data paths — override with DATA_DIR env var to point at a persistent volume
# Railway: set DATA_DIR to your mounted volume path e.g. /data
# Local:   leave unset and files sit next to the bot script
_DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(_DATA_DIR, "config.json")
DATA_FILE   = os.path.join(_DATA_DIR, "data.json")

# One-time migration: if running with DATA_DIR and the volume is empty,
# copy config.json / data.json from the app folder so nothing is lost.
import shutil as _shutil
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(_DATA_DIR, exist_ok=True)
for _fname in ("config.json", "data.json"):
    _src = os.path.join(_APP_DIR, _fname)
    _dst = os.path.join(_DATA_DIR, _fname)
    if not os.path.exists(_dst) and os.path.exists(_src):
        _shutil.copy2(_src, _dst)
        print(f"Migrated {_fname} to {_dst}")

TWITCH_CHANNEL = "vexonn_gaming"
TWITCH_LINK = "https://www.twitch.tv/vexonn_gaming"
YOUTUBE_HANDLE = "ahmed_a_030"
YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@ahmed_a_030"
TIKTOK_USERNAME = "vexonn_gaming"
TIKTOK_URL = "https://www.tiktok.com/@vexonn_gaming"
UPLOAD_CHANNEL = "upload-announcement"

LEVEL_ROLES = {1: "Level 1", 5: "Level 5", 10: "Level 10"}

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

# RPS
RPS_BASE_XP = 10
RPS_BASE_POINTS = 25

# Steal cooldown in seconds (5 hours)
STEAL_COOLDOWN = 18000

# ============================================================
#   SHOP CATALOGUE
# ============================================================

SHOP_ITEMS = {
    "shield_30m":    {"name": "Shield (30 min)",   "price": 100,  "type": "shield",  "duration": 1800,    "description": "Protects you from theft for 30 minutes."},
    "shield_1h":     {"name": "Shield (1 hour)",   "price": 150,  "type": "shield",  "duration": 3600,    "description": "Protects you from theft for 1 hour."},
    "shield_5h":     {"name": "Shield (5 hours)",  "price": 400,  "type": "shield",  "duration": 18000,   "description": "Protects you from theft for 5 hours."},
    "shield_10h":    {"name": "Shield (10 hours)", "price": 700,  "type": "shield",  "duration": 36000,   "description": "Protects you from theft for 10 hours."},
    "shield_1d":     {"name": "Shield (1 day)",    "price": 1000, "type": "shield",  "duration": 86400,   "description": "Protects you from theft for 1 day."},
    "shield_3d":     {"name": "Shield (3 days)",   "price": 2500, "type": "shield",  "duration": 259200,  "description": "Protects you from theft for 3 days."},
    "shield_7d":     {"name": "Shield (7 days)",   "price": 5000, "type": "shield",  "duration": 604800,  "description": "Protects you from theft for 7 days."},
    "xp_boost_1h":   {"name": "XP Boost (1 hour)", "price": 500,  "type": "xp_boost","duration": 3600,   "description": "Doubles XP earned from chatting for 1 hour."},
    "xp_boost_24h":  {"name": "XP Boost (24 hrs)", "price": 1500, "type": "xp_boost","duration": 86400,  "description": "Doubles XP earned from chatting for 24 hours."},
    "point_vault":   {"name": "Point Vault",        "price": 300,  "type": "vault",   "capacity": 500,    "description": "Stores up to 500 points that can never be stolen."},
    "robbery_kit":   {"name": "Robbery Kit",        "price": 400,  "type": "rob_kit", "boost": 0.15,      "description": "Increases max steal amount by 15% on your next steal."},
    "steal_insurance":{"name":"Steal Insurance",    "price": 600,  "type": "insurance","description": "If someone steals from you, they lose points too."},
    "daily_booster": {"name": "Daily Booster",      "price": 800,  "type": "daily_boost","description": "Doubles your next daily reward claim."},
}

# ============================================================
#   WORD OF THE DAY LIST
# ============================================================

WORD_OF_THE_DAY_LIST = [
    {"word": "Ephemeral",    "type": "adjective",      "definition": "Lasting for a very short time.",                                             "example": "The ephemeral beauty of cherry blossoms makes them even more special."},
    {"word": "Serendipity",  "type": "noun",            "definition": "The occurrence of happy events by chance.",                                  "example": "It was pure serendipity that they met at the airport."},
    {"word": "Resilient",    "type": "adjective",       "definition": "Able to recover quickly from difficulties.",                                 "example": "She was resilient enough to rebuild her life after the setback."},
    {"word": "Labyrinth",    "type": "noun",            "definition": "A complicated network of paths in which it is difficult to find your way.",  "example": "The old city was a labyrinth of narrow streets."},
    {"word": "Melancholy",   "type": "noun/adjective",  "definition": "A deep, pensive sadness.",                                                   "example": "A sense of melancholy washed over him as he left his hometown."},
    {"word": "Eloquent",     "type": "adjective",       "definition": "Fluent and persuasive in speaking or writing.",                              "example": "Her eloquent speech moved the entire audience."},
    {"word": "Tenacious",    "type": "adjective",       "definition": "Holding firmly to something, refusing to give up.",                          "example": "His tenacious attitude helped him finish the marathon."},
    {"word": "Paradox",      "type": "noun",            "definition": "A statement that seems contradictory but may be true.",                      "example": "The paradox of choice is that having too many options can make you less happy."},
    {"word": "Wanderlust",   "type": "noun",            "definition": "A strong desire to travel and explore the world.",                           "example": "Her wanderlust took her across six continents before she turned 30."},
    {"word": "Catharsis",    "type": "noun",            "definition": "The release of strong emotions, often bringing a sense of relief.",           "example": "Crying during the film provided a catharsis she did not expect."},
    {"word": "Magnanimous",  "type": "adjective",       "definition": "Generous and forgiving, especially towards a rival.",                        "example": "The champion was magnanimous in victory, praising his opponent."},
    {"word": "Enigmatic",    "type": "adjective",       "definition": "Mysterious and difficult to understand.",                                    "example": "His enigmatic smile left everyone wondering what he was thinking."},
    {"word": "Juxtapose",    "type": "verb",            "definition": "To place two things side by side to highlight their differences.",            "example": "The film juxtaposes wealth and poverty to make a powerful point."},
    {"word": "Euphoria",     "type": "noun",            "definition": "An intense feeling of happiness and excitement.",                            "example": "Winning the championship filled the team with pure euphoria."},
    {"word": "Stoic",        "type": "adjective",       "definition": "Enduring pain or hardship without showing emotion.",                         "example": "He remained stoic throughout the difficult operation."},
    {"word": "Hubris",       "type": "noun",            "definition": "Excessive pride or self-confidence that leads to downfall.",                  "example": "His hubris led him to underestimate his opponent."},
    {"word": "Solitude",     "type": "noun",            "definition": "The state of being alone, often in a peaceful way.",                         "example": "She found solitude in long walks through the forest."},
    {"word": "Vicarious",    "type": "adjective",       "definition": "Experienced through another person rather than directly.",                   "example": "He lived vicariously through the adventures in his favourite novels."},
    {"word": "Ambivalent",   "type": "adjective",       "definition": "Having mixed or contradictory feelings about something.",                    "example": "She felt ambivalent about moving to a new city."},
    {"word": "Catalyst",     "type": "noun",            "definition": "Something that triggers or speeds up a change or event.",                    "example": "The invention of the internet was a catalyst for enormous social change."},
    {"word": "Nostalgia",    "type": "noun",            "definition": "A sentimental longing for the past.",                                        "example": "The old song filled him with nostalgia for his school days."},
    {"word": "Pragmatic",    "type": "adjective",       "definition": "Dealing with things sensibly and practically.",                              "example": "She took a pragmatic approach to solving the budget problem."},
    {"word": "Clandestine",  "type": "adjective",       "definition": "Done in secret, especially for illegal reasons.",                            "example": "They held clandestine meetings in an abandoned warehouse."},
    {"word": "Integrity",    "type": "noun",            "definition": "The quality of being honest and having strong moral principles.",             "example": "Her integrity made her one of the most trusted people in the company."},
    {"word": "Ubiquitous",   "type": "adjective",       "definition": "Present, appearing, or found everywhere.",                                   "example": "Smartphones have become ubiquitous in modern life."},
    {"word": "Zeitgeist",    "type": "noun",            "definition": "The defining mood or spirit of a particular period in history.",              "example": "Social media perfectly captures the zeitgeist of the 21st century."},
    {"word": "Empathy",      "type": "noun",            "definition": "The ability to understand and share the feelings of another.",               "example": "Great leaders often have a strong sense of empathy towards their team."},
    {"word": "Obsolete",     "type": "adjective",       "definition": "No longer in use or no longer useful.",                                      "example": "Fax machines have become largely obsolete in the digital age."},
    {"word": "Volatile",     "type": "adjective",       "definition": "Liable to change rapidly and unpredictably.",                               "example": "The stock market was particularly volatile during the crisis."},
    {"word": "Diligent",     "type": "adjective",       "definition": "Careful and persistent in work or effort.",                                  "example": "Her diligent revision paid off when she aced all her exams."},
    {"word": "Benevolent",   "type": "adjective",       "definition": "Well-meaning and kindly.",                                                   "example": "The benevolent teacher stayed after school to help struggling students."},
    {"word": "Candid",       "type": "adjective",       "definition": "Truthful and straightforward; frank.",                                       "example": "He gave a candid assessment of the team's weaknesses."},
    {"word": "Cynical",      "type": "adjective",       "definition": "Distrustful of human sincerity or motives.",                                 "example": "Years of disappointment had made him cynical about politics."},
    {"word": "Daunting",     "type": "adjective",       "definition": "Seeming difficult to deal with in prospect; intimidating.",                  "example": "The mountain looked daunting from base camp."},
    {"word": "Frugal",       "type": "adjective",       "definition": "Sparing or economical with money or food.",                                  "example": "She was frugal with her savings, never wasting a penny."},
    {"word": "Gregarious",   "type": "adjective",       "definition": "Fond of company; sociable.",                                                 "example": "He was gregarious by nature and thrived at social events."},
    {"word": "Imminent",     "type": "adjective",       "definition": "About to happen very soon.",                                                 "example": "The dark clouds signalled that a storm was imminent."},
    {"word": "Lament",       "type": "verb/noun",       "definition": "To express grief or sorrow.",                                                "example": "He lamented the loss of his childhood home."},
    {"word": "Meticulous",   "type": "adjective",       "definition": "Showing great attention to detail and care.",                                "example": "The surgeon was meticulous in every step of the procedure."},
    {"word": "Nonchalant",   "type": "adjective",       "definition": "Feeling or appearing casually calm and relaxed.",                            "example": "She was nonchalant about the exam despite not revising."},
    {"word": "Perseverance", "type": "noun",            "definition": "Continued effort despite difficulty.",                                       "example": "His perseverance through injury made his comeback impressive."},
    {"word": "Reciprocal",   "type": "adjective",       "definition": "Given, felt, or done in return; mutual.",                                    "example": "They had a reciprocal respect for each other's work."},
    {"word": "Serene",       "type": "adjective",       "definition": "Calm, peaceful, and untroubled.",                                            "example": "The lake was serene at dawn with no wind to disturb it."},
    {"word": "Tenacity",     "type": "noun",            "definition": "The quality of being determined and persistent.",                             "example": "Her tenacity in training led to a gold medal at the championships."},
    {"word": "Verbose",      "type": "adjective",       "definition": "Using more words than needed; wordy.",                                       "example": "The verbose report could have been summarised in one page."},
    {"word": "Wistful",      "type": "adjective",       "definition": "Having a feeling of vague longing or regret.",                               "example": "She gave a wistful smile as she looked through old photographs."},
]

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
    {"q": "What is the longest river in the world?", "a": "nile"},
    {"q": "How many hours are in a day?", "a": "24"},
    {"q": "What sport is played at Wimbledon?", "a": "tennis"},
    {"q": "What is the currency of the United Kingdom?", "a": "pound"},
    {"q": "How many strings does a standard guitar have?", "a": "6"},
    {"q": "What is the capital of Australia?", "a": "canberra"},
    {"q": "What is the hardest natural substance on Earth?", "a": "diamond"},
    {"q": "What language has the most native speakers in the world?", "a": "mandarin"},
    {"q": "What is the name of the closest star to Earth?", "a": "sun"},
    {"q": "How many players are on a basketball team?", "a": "5"},
    {"q": "What is the capital of Germany?", "a": "berlin"},
    {"q": "What year did World War 2 end?", "a": "1945"},
    {"q": "What is the smallest country in the world?", "a": "vatican city"},
    {"q": "How many days are in a leap year?", "a": "366"},
    {"q": "What is the capital of the United States?", "a": "washington dc"},
    {"q": "What ocean is the Titanic at the bottom of?", "a": "atlantic"},
    {"q": "What is the tallest mountain in the world?", "a": "mount everest"},
    {"q": "What is the capital of Spain?", "a": "madrid"},
    {"q": "What colour are emeralds?", "a": "green"},
    {"q": "What is the largest desert in the world?", "a": "sahara"},
    {"q": "How many letters are in the English alphabet?", "a": "26"},
    {"q": "What is the chemical symbol for gold?", "a": "au"},
    {"q": "Which planet has the most moons?", "a": "saturn"},
    {"q": "Who painted the Mona Lisa?", "a": "leonardo da vinci"},
    {"q": "What is the longest bone in the human body?", "a": "femur"},
    {"q": "What year did the first iPhone release?", "a": "2007"},
    {"q": "How many sides does an octagon have?", "a": "8"},
    {"q": "What is the capital of Brazil?", "a": "brasilia"},
    {"q": "What gas makes up most of the atmosphere?", "a": "nitrogen"},
    {"q": "What is the powerhouse of the cell?", "a": "mitochondria"},
    {"q": "How many planets are in our solar system?", "a": "8"},
    {"q": "What is the square root of 256?", "a": "16"},
    {"q": "What element does O represent?", "a": "oxygen"},
    {"q": "How many hearts does an octopus have?", "a": "3"},
    {"q": "What country has the most natural lakes?", "a": "canada"},
    {"q": "What is the currency of Japan?", "a": "yen"},
    {"q": "What is the hardest material known to science?", "a": "diamond"},
    {"q": "How many keys does a standard piano have?", "a": "88"},
    {"q": "What sport uses a shuttlecock?", "a": "badminton"},
]

recent_trivia = {}
active_trivia = {}
raid_tracker = {}

# Global lock — prevents two commands corrupting data.json at the same time
_data_lock = asyncio.Lock()

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
        "xp": {}, "points": {}, "joined_before": [],
        "twitch_live": False, "daily_claimed": {},
        "birthdays": {}, "birthday_announced": {},
        "warnings": {}, "promoted_suggestions": [],
        "wotd_used": [], "inventories": {},
        "rps_streaks": {}, "last_robbed": {},
        "vault": {}, "xp_boosts": {},
        "daily_streaks": {}, "timeout_expiry": {}, "tempbans": {},
        "last_youtube_id": None, "last_tiktok_id": None,
        "message_counts": {}, "trivia_wins": {}, "steal_counts": {},
        "achievements": {}, "suggestions_made": {}, "job_data": {}
    }
    for key, default in defaults.items():
        if key not in data:
            data[key] = default
    return data

def validate_config():
    required_keys = ["prefix", "welcome_channel", "level_up_channel",
                     "mod_log_channel", "get_roles_channel",
                     "xp_per_message", "xp_cooldown_seconds",
                     "reaction_roles", "mod_roles"]
    config = get_config()
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise RuntimeError(f"FATAL: Missing required config keys: {missing}. Add them to {CONFIG_FILE} before starting the bot.")
    else:
        print("Config validated successfully.")

# ============================================================
#   HELPERS
# ============================================================

xp_cooldowns = {}

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

def get_user_points(data, guild_id, user_id):
    return data.get("points", {}).get(guild_id, {}).get(user_id, 0)

def set_user_points(data, guild_id, user_id, amount):
    if guild_id not in data["points"]:
        data["points"][guild_id] = {}
    data["points"][guild_id][user_id] = max(0, amount)

def get_user_xp(data, guild_id, user_id):
    return data.get("xp", {}).get(guild_id, {}).get(user_id, 0)

def set_user_xp(data, guild_id, user_id, amount):
    if guild_id not in data["xp"]:
        data["xp"][guild_id] = {}
    data["xp"][guild_id][user_id] = max(0, amount)

def get_inventory(data, guild_id, user_id):
    return data.get("inventories", {}).get(guild_id, {}).get(user_id, [])

def add_to_inventory(data, guild_id, user_id, item_id, extra=None):
    if guild_id not in data["inventories"]:
        data["inventories"][guild_id] = {}
    if user_id not in data["inventories"][guild_id]:
        data["inventories"][guild_id][user_id] = []
    entry = {"item_id": item_id, "purchased_at": time.time()}
    if extra:
        entry.update(extra)
    data["inventories"][guild_id][user_id].append(entry)

def has_active_shield(data, guild_id, user_id):
    now = time.time()
    inv = get_inventory(data, guild_id, user_id)
    for item in inv:
        if SHOP_ITEMS.get(item["item_id"], {}).get("type") == "shield":
            duration = SHOP_ITEMS[item["item_id"]]["duration"]
            if now - item["purchased_at"] < duration:
                expires_in = duration - (now - item["purchased_at"])
                return True, expires_in
    return False, 0

def has_active_xp_boost(data, guild_id, user_id):
    now = time.time()
    inv = get_inventory(data, guild_id, user_id)
    for item in inv:
        if SHOP_ITEMS.get(item["item_id"], {}).get("type") == "xp_boost":
            duration = SHOP_ITEMS[item["item_id"]]["duration"]
            if now - item["purchased_at"] < duration:
                return True
    return False

def has_item(data, guild_id, user_id, item_type):
    inv = get_inventory(data, guild_id, user_id)
    for item in inv:
        if SHOP_ITEMS.get(item["item_id"], {}).get("type") == item_type:
            return True
    return False

def remove_item_by_type(data, guild_id, user_id, item_type):
    if guild_id not in data["inventories"]:
        return
    if user_id not in data["inventories"][guild_id]:
        return
    inv = data["inventories"][guild_id][user_id]
    for i, item in enumerate(inv):
        if SHOP_ITEMS.get(item["item_id"], {}).get("type") == item_type:
            data["inventories"][guild_id][user_id].pop(i)
            return

def get_vault(data, guild_id, user_id):
    return data.get("vault", {}).get(guild_id, {}).get(user_id, 0)

def set_vault(data, guild_id, user_id, amount):
    if guild_id not in data["vault"]:
        data["vault"][guild_id] = {}
    data["vault"][guild_id][user_id] = max(0, amount)

def format_duration(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m"
    elif seconds < 86400:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
    else:
        return f"{int(seconds // 86400)}d {int((seconds % 86400) // 3600)}h"

async def check_and_announce_level_up(guild, member, old_xp, new_xp, data, guild_id, user_id):
    """Call this after awarding XP outside of on_message so level-ups are announced."""
    old_level = get_level(old_xp)
    new_level = get_level(new_xp)
    if new_level > old_level:
        level_channel = discord.utils.get(guild.text_channels, name="levelling-announcements")
        if level_channel:
            embed = discord.Embed(
                title="Level Up!",
                description=(
                    f"Congratulations {member.mention}!\n\n"
                    f"You have levelled up to **Level {new_level}**! Keep it up!"
                ),
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Level {new_level} reached")
            await level_channel.send(embed=embed)
        if new_level in LEVEL_ROLES:
            role_name = LEVEL_ROLES[new_level]
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                roles_to_remove = [
                    discord.utils.get(guild.roles, name=LEVEL_ROLES[lvl])
                    for lvl in LEVEL_ROLES if lvl < new_level
                    and discord.utils.get(guild.roles, name=LEVEL_ROLES[lvl]) in member.roles
                ]
                roles_to_remove = [r for r in roles_to_remove if r]
                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove)
                await member.add_roles(role)
                if new_level == 5:
                    lvl5_role = discord.utils.get(guild.roles, name="Level 5")
                    if lvl5_role:
                        new_perms = lvl5_role.permissions
                        new_perms.update(attach_files=True)
                        await lvl5_role.edit(permissions=new_perms, reason="Level 5: pic perms unlocked")

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

_twitch_token_cache = {"token": None, "expires_at": 0}

async def get_twitch_token():
    now = time.time()
    if _twitch_token_cache["token"] and now < _twitch_token_cache["expires_at"]:
        return _twitch_token_cache["token"]
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    params = {"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"}
    async with aiohttp.ClientSession() as session:
        async with session.post("https://id.twitch.tv/oauth2/token", params=params) as resp:
            result = await resp.json()
            token = result.get("access_token")
            expires_in = result.get("expires_in", 3600 * 24 * 30)  # default 30 days
            _twitch_token_cache["token"] = token
            _twitch_token_cache["expires_at"] = now + expires_in - 300  # refresh 5 min early
            return token

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
                    title="Vexon is now LIVE on Twitch!",
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
#   YOUTUBE UPLOAD CHECKER
# ============================================================
# Uses YouTube's public RSS feed — no API key needed.
# The feed returns the latest 15 videos. We store the most
# recent video ID so we only announce genuinely new uploads.

import xml.etree.ElementTree as _ET

async def get_latest_youtube_video():
    """Fetch the latest video from the YouTube RSS feed."""
    try:
        # First fetch the channel page to get the real channel ID
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://www.youtube.com/@{YOUTUBE_HANDLE}",
                headers={"User-Agent": "Mozilla/5.0"}
            ) as resp:
                html = await resp.text()
        # Extract channel ID from page source
        import re as _re
        match = _re.search(r'"channelId":"(UC[A-Za-z0-9_-]{22})"', html)
        if not match:
            return None
        channel_id = match.group(1)
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(rss_url) as resp:
                xml_text = await resp.text()
        root = _ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "media": "http://search.yahoo.com/mrss/"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            return None
        video_id  = entry.find("yt:videoId", ns).text
        title     = entry.find("atom:title", ns).text
        link      = entry.find("atom:link", ns).attrib.get("href", f"https://www.youtube.com/watch?v={video_id}")
        thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        return {"id": video_id, "title": title, "link": link, "thumbnail": thumbnail}
    except Exception as e:
        print(f"YouTube fetch error: {e}")
        return None

@tasks.loop(minutes=10)
async def youtube_check_loop():
    data = load_data()
    data = ensure_keys(data)
    video = await get_latest_youtube_video()
    if not video:
        return
    last_id = data.get("last_youtube_id")
    if video["id"] == last_id:
        return
    data["last_youtube_id"] = video["id"]
    save_data(data)
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=UPLOAD_CHANNEL)
        if channel:
            embed = discord.Embed(
                title=video["title"],
                url=video["link"],
                description=f"**Vexon** published a new video on YouTube!\n\n[Watch now]({video['link']})",
                color=discord.Color.red()
            )
            embed.set_image(url=video["thumbnail"])
            embed.set_author(name="Vexon", icon_url="https://www.youtube.com/favicon.ico")
            embed.set_footer(text="YouTube • New Upload")
            await channel.send(f"@everyone {video['title']} | {video['link']} !", embed=embed)

@youtube_check_loop.before_loop
async def before_youtube():
    await bot.wait_until_ready()

# ============================================================
#   TIKTOK UPLOAD CHECKER
# ============================================================
# TikTok has no public API, so we scrape the profile page
# and look for the latest video ID in the page source.

async def get_latest_tiktok_video():
    """Scrape the TikTok profile page for the latest video."""
    try:
        import re as _re
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://www.tiktok.com/@{TIKTOK_USERNAME}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            ) as resp:
                html = await resp.text()
        # Extract video IDs from the page
        video_ids = _re.findall(r'"id":"(\d{17,19})"', html)
        if not video_ids:
            return None
        latest_id = video_ids[0]
        link = f"https://www.tiktok.com/@{TIKTOK_USERNAME}/video/{latest_id}"
        return {"id": latest_id, "link": link}
    except Exception as e:
        print(f"TikTok fetch error: {e}")
        return None

@tasks.loop(minutes=15)
async def tiktok_check_loop():
    data = load_data()
    data = ensure_keys(data)
    video = await get_latest_tiktok_video()
    if not video:
        return
    last_id = data.get("last_tiktok_id")
    if video["id"] == last_id:
        return
    data["last_tiktok_id"] = video["id"]
    save_data(data)
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=UPLOAD_CHANNEL)
        if channel:
            embed = discord.Embed(
                title="Vexon uploaded a new TikTok!",
                url=video["link"],
                description="#fyp",
                color=discord.Color.from_rgb(0, 0, 0)
            )
            embed.add_field(name="View on TikTok", value=f"[Open TikTok]({video['link']})", inline=False)
            embed.set_footer(text="TikTok • New Upload")
            await channel.send(f"@everyone", embed=embed)

@tiktok_check_loop.before_loop
async def before_tiktok():
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
    today = datetime.now().strftime("%Y-%m-%d")
    if data.get("wotd_last_posted") == today:
        return  # Already posted today (e.g. via ?wotd command)
    used = data.get("wotd_used", [])
    available = [w for w in WORD_OF_THE_DAY_LIST if w["word"] not in used]
    if not available:
        data["wotd_used"] = []
        available = WORD_OF_THE_DAY_LIST
    word = random.choice(available)
    data["wotd_used"].append(word["word"])
    data["wotd_last_posted"] = today
    save_data(data)
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=WOTD_CHANNEL)
        if channel:
            embed = discord.Embed(title=f"Word of the Day: {word['word']}", color=discord.Color.teal())
            embed.add_field(name="Type", value=word["type"], inline=True)
            embed.add_field(name="Definition", value=word["definition"], inline=False)
            embed.add_field(name="Example", value=f"*\"{word['example']}\"*", inline=False)
            embed.set_footer(text="Expand your vocabulary every day!")
            await channel.send(embed=embed)

@wotd_loop.before_loop
async def before_wotd():
    await bot.wait_until_ready()
    now = datetime.now()
    target = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    await asyncio.sleep((target - now).total_seconds())

# ============================================================
#   TIMEOUT AUTO-EXPIRE TASK
# ============================================================

@tasks.loop(seconds=30)
async def timeout_expire_loop():
    """
    Runs every 30 seconds. When a stored timeout has passed its expiry
    timestamp, removes the Timed Out role, closes the case channel,
    and notifies the member that their sentence is up.
    """
    now = int(time.time())
    data = load_data()
    data = ensure_keys(data)
    if "timeout_expiry" not in data:
        return

    expired_keys = [k for k, exp in data["timeout_expiry"].items() if now >= exp]
    if not expired_keys:
        return

    changed = False
    for key in expired_keys:
        try:
            guild_id_str, member_id_str = key.split("_", 1)
            guild = bot.get_guild(int(guild_id_str))
            if not guild:
                data["timeout_expiry"].pop(key, None)
                changed = True
                continue

            member = guild.get_member(int(member_id_str))

            # Remove Timed Out role
            timeout_role = discord.utils.get(guild.roles, name="Timed Out")
            if member and timeout_role and timeout_role in member.roles:
                await member.remove_roles(timeout_role, reason="Timeout expired automatically")

            # Close the channel — send sentence-served message first
            safe_name = "".join(c if c.isalnum() or c == "-" else "-" for c in (member.display_name.lower() if member else member_id_str))
            channel_name = f"timeout-{safe_name}"[:100]
            channel = discord.utils.get(guild.text_channels, name=channel_name)
            if channel:
                mention = member.mention if member else f"<@{member_id_str}>"
                served_desc = (
                    f"{mention} your timeout has now expired. "
                    "You have served your sentence and may talk in the server again.\n\n"
                    "This channel will be deleted in 5 seconds."
                )
                served_desc = (
                    f"{mention} your timeout has now expired. "
                    "You have served your sentence and may talk in the server again.\n\n"
                    "This channel will be deleted in 5 seconds."
                )
                embed = discord.Embed(
                    title="Timeout Served",
                    description=served_desc,
                    color=discord.Color.green()
                )
                await channel.send(embed=embed)
                await asyncio.sleep(5)
                await channel.delete(reason="Timeout expired")

            data["timeout_expiry"].pop(key, None)
            changed = True
        except Exception as e:
            print(f"Timeout expire error for key {key}: {e}")

    if changed:
        save_data(data)

@timeout_expire_loop.before_loop
async def before_timeout_expire():
    await bot.wait_until_ready()



# ============================================================
#   JOB SYSTEM
# ============================================================

JOBS = {
    "janitor":     {"name": "Janitor",     "emoji": "🧹", "base_pay": 80,  "base_xp": 10, "req_shifts": 0,   "desc": "Entry-level. Just show up."},
    "cashier":     {"name": "Cashier",     "emoji": "🛒", "base_pay": 130, "base_xp": 15, "req_shifts": 5,   "desc": "5 shifts required to unlock."},
    "chef":        {"name": "Chef",        "emoji": "👨‍🍳", "base_pay": 200, "base_xp": 25, "req_shifts": 15,  "desc": "15 shifts required to unlock."},
    "developer":   {"name": "Developer",   "emoji": "💻", "base_pay": 350, "base_xp": 40, "req_shifts": 30,  "desc": "30 shifts required to unlock."},
    "scientist":   {"name": "Scientist",   "emoji": "🔬", "base_pay": 500, "base_xp": 60, "req_shifts": 50,  "desc": "50 shifts required to unlock."},
    "ceo":         {"name": "CEO",         "emoji": "🏢", "base_pay": 800, "base_xp": 80, "req_shifts": 100, "desc": "100 shifts required to unlock."},
}

WORK_MINIGAMES = [
    {"type": "unscramble", "words": ["discord", "python", "server", "gaming", "stream", "points", "level", "trophy", "shield", "rocket"]},
    {"type": "repeat",     "sequences": ["abc123", "xyz789", "bot420", "win999", "gg2ez", "top1gg"]},
    {"type": "math",       "problems": [("5 + 7", "12"), ("9 * 4", "36"), ("50 / 2", "25"), ("100 - 37", "63"), ("8 * 8", "64"), ("144 / 12", "12")]},
]

WORK_COOLDOWN = 3600  # 1 hour

@bot.command(name="jobs")
async def jobs_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "jobs")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id  = str(ctx.author.id)
    shifts   = data.get("job_data", {}).get(guild_id, {}).get(user_id, {}).get("total_shifts", 0)
    cur_job  = data.get("job_data", {}).get(guild_id, {}).get(user_id, {}).get("job", None)

    embed = discord.Embed(title="Available Jobs", description="Use `?work` to start a shift once you have a job. Use `?choosejob [job]` to pick one.", color=discord.Color.blue())
    for key, job in JOBS.items():
        locked = shifts < job["req_shifts"]
        status = "🔒 Locked" if locked else ("✅ Current" if cur_job == key else "Available")
        embed.add_field(
            name=f"{job['emoji']} {job['name']} — {status}",
            value=f"Pay: **{job['base_pay']}–{job['base_pay']*2}** pts | XP: **{job['base_xp']}** | Requires {job['req_shifts']} shifts\n{job['desc']}",
            inline=False
        )
    embed.set_footer(text=f"Your total shifts: {shifts}")
    await ctx.send(embed=embed)

@bot.command(name="choosejob")
async def choosejob_cmd(ctx, job_key: str = None):
    await log_command(ctx.guild, ctx.author, "choosejob", job_key or "")
    if not job_key or job_key.lower() not in JOBS:
        jobs_list = ", ".join(f"`{k}`" for k in JOBS)
        await ctx.send(f"Please choose a valid job: {jobs_list}")
        return
    job_key = job_key.lower()
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id  = str(ctx.author.id)
    if "job_data" not in data:
        data["job_data"] = {}
    if guild_id not in data["job_data"]:
        data["job_data"][guild_id] = {}
    if user_id not in data["job_data"][guild_id]:
        data["job_data"][guild_id][user_id] = {"job": None, "total_shifts": 0, "last_work": 0}
    shifts = data["job_data"][guild_id][user_id].get("total_shifts", 0)
    job = JOBS[job_key]
    if shifts < job["req_shifts"]:
        await ctx.send(f"You need **{job['req_shifts']} shifts** to unlock {job['emoji']} **{job['name']}**. You have {shifts}.")
        return
    data["job_data"][guild_id][user_id]["job"] = job_key
    save_data(data)
    await ctx.send(f"You are now working as a {job['emoji']} **{job['name']}**! Use `?work` to start your next shift.")

@bot.command(name="work")
async def work_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "work")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id  = str(ctx.author.id)
    if "job_data" not in data:
        data["job_data"] = {}
    if guild_id not in data["job_data"]:
        data["job_data"][guild_id] = {}
    if user_id not in data["job_data"][guild_id]:
        data["job_data"][guild_id][user_id] = {"job": None, "total_shifts": 0, "last_work": 0}

    job_entry = data["job_data"][guild_id][user_id]
    if not job_entry.get("job"):
        await ctx.send("You don't have a job yet! Use `?jobs` to browse and `?choosejob [job]` to pick one.")
        return

    now = time.time()
    last_work = job_entry.get("last_work", 0)
    if now - last_work < WORK_COOLDOWN:
        remaining = int(WORK_COOLDOWN - (now - last_work))
        mins = remaining // 60
        secs = remaining % 60
        next_ts = int(last_work + WORK_COOLDOWN)
        await ctx.send(f"You need to rest! Next shift available <t:{next_ts}:R>.")
        return

    job = JOBS[job_entry["job"]]
    # Pick a random mini-game
    game_cat = random.choice(WORK_MINIGAMES)
    if game_cat["type"] == "unscramble":
        word = random.choice(game_cat["words"])
        scrambled = list(word)
        random.shuffle(scrambled)
        while "".join(scrambled) == word:
            random.shuffle(scrambled)
        scrambled_str = "".join(scrambled)
        await ctx.send(
            f"{job['emoji']} **{job['name']} Shift** — Unscramble this word to earn your pay!\n\n"
            f"**`{scrambled_str.upper()}`**\n\nType the correct word within 20 seconds."
        )
        def check(m): return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=20)
            correct = msg.content.strip().lower() == word
        except:
            correct = False
    elif game_cat["type"] == "repeat":
        seq = random.choice(game_cat["sequences"])
        await ctx.send(
            f"{job['emoji']} **{job['name']} Shift** — Repeat this code exactly to earn your pay!\n\n"
            f"**`{seq}`**\n\nType it within 20 seconds."
        )
        def check(m): return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=20)
            correct = msg.content.strip() == seq
        except:
            correct = False
    else:  # math
        prob, answer = random.choice(game_cat["problems"])
        await ctx.send(
            f"{job['emoji']} **{job['name']} Shift** — Solve this to earn your pay!\n\n"
            f"**`{prob} = ?`**\n\nType the answer within 20 seconds."
        )
        def check(m): return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=20)
            correct = msg.content.strip() == answer
        except:
            correct = False

    job_entry["last_work"] = now
    if correct:
        pay = random.randint(job["base_pay"], job["base_pay"] * 2)
        xp_gain = job["base_xp"]
        old_xp = get_user_xp(data, guild_id, user_id)
        set_user_points(data, guild_id, user_id, get_user_points(data, guild_id, user_id) + pay)
        set_user_xp(data, guild_id, user_id, old_xp + xp_gain)
        job_entry["total_shifts"] = job_entry.get("total_shifts", 0) + 1
        save_data(data)
        await check_and_announce_level_up(ctx.guild, ctx.author, old_xp, old_xp + xp_gain, data, guild_id, user_id)
        await ctx.send(
            f"✅ Great work! You earned **{pay} points** and **{xp_gain} XP** from your shift as {job['emoji']} {job['name']}.\n"
            f"Total shifts: **{job_entry['total_shifts']}**"
        )
    else:
        save_data(data)
        await ctx.send(f"❌ You failed the task and got no pay this shift. Better luck next time!")

# ============================================================
#   ACHIEVEMENTS SYSTEM
# ============================================================

ACHIEVEMENTS = {
    "first_daily":     {"name": "First Steps",         "icon": "🌅", "desc": "Claim your first daily reward."},
    "streak_7":        {"name": "Week Warrior",         "icon": "🔥", "desc": "Reach a 7-day daily streak."},
    "streak_30":       {"name": "Monthly Legend",       "icon": "💎", "desc": "Reach a 30-day daily streak."},
    "msg_100":         {"name": "Chatterbox",           "icon": "💬", "desc": "Send 100 messages."},
    "msg_1000":        {"name": "Veteran",              "icon": "🏆", "desc": "Send 1000 messages."},
    "trivia_10":       {"name": "Quiz Master",          "icon": "🧠", "desc": "Win 10 trivia questions."},
    "steal_5":         {"name": "Pickpocket",           "icon": "🥷", "desc": "Successfully steal 5 times."},
    "level_10":        {"name": "Level 10",             "icon": "⭐", "desc": "Reach Level 10."},
    "shopaholic":      {"name": "Shopaholic",           "icon": "🛍️", "desc": "Buy 10 items from the shop."},
    "rich":            {"name": "Loaded",               "icon": "💰", "desc": "Accumulate 10,000 points."},
}

async def check_and_grant_achievements(guild, member, data, guild_id, user_id, channel):
    """Check all achievement conditions and award any newly unlocked ones."""
    if guild_id not in data["achievements"]:
        data["achievements"][guild_id] = {}
    if user_id not in data["achievements"][guild_id]:
        data["achievements"][guild_id][user_id] = []
    unlocked = data["achievements"][guild_id][user_id]
    newly_unlocked = []

    def check(key, condition):
        if key not in unlocked and condition:
            unlocked.append(key)
            newly_unlocked.append(ACHIEVEMENTS[key])

    claim_key = f"{guild_id}_{user_id}"
    daily_streak  = data["daily_streaks"].get(claim_key, 0)
    msg_count     = data["message_counts"].get(guild_id, {}).get(user_id, 0)
    trivia_wins   = data["trivia_wins"].get(guild_id, {}).get(user_id, 0)
    steal_count   = data["steal_counts"].get(guild_id, {}).get(user_id, 0)
    total_xp      = get_user_xp(data, guild_id, user_id)
    points        = get_user_points(data, guild_id, user_id)
    inv_count     = len(get_inventory(data, guild_id, user_id))

    check("first_daily",  daily_streak >= 1)
    check("streak_7",     daily_streak >= 7)
    check("streak_30",    daily_streak >= 30)
    check("msg_100",      msg_count >= 100)
    check("msg_1000",     msg_count >= 1000)
    check("trivia_10",    trivia_wins >= 10)
    check("steal_5",      steal_count >= 5)
    check("level_10",     get_level(total_xp) >= 10)
    check("shopaholic",   inv_count >= 10)
    check("rich",         points >= 10000)

    if newly_unlocked:
        data["achievements"][guild_id][user_id] = unlocked
        save_data(data)  # persist immediately so ?achieve reflects it
        for ach in newly_unlocked:
            if channel:
                embed = discord.Embed(
                    title=f"{ach['icon']} Achievement Unlocked: {ach['name']}",
                    description=f"{member.mention} {ach['desc']}",
                    color=discord.Color.gold()
                )
                await channel.send(embed=embed)

# ============================================================
#   TEMPBAN AUTO-UNBAN LOOP
# ============================================================

@tasks.loop(minutes=5)
async def tempban_expire_loop():
    """Checks every 5 mins and unbans members whose temp-ban has expired."""
    now = int(time.time())
    data = load_data()
    data = ensure_keys(data)
    expired = {uid: info for uid, info in data["tempbans"].items() if now >= info["unban_ts"]}
    if not expired:
        return
    changed = False
    for user_id_str, info in list(expired.items()):
        try:
            guild = bot.get_guild(int(info["guild_id"]))
            if not guild:
                continue
            await guild.unban(discord.Object(id=int(user_id_str)), reason="Temp-ban expired")
            config = get_config()
            log_ch = discord.utils.get(guild.text_channels, name=config.get("mod_log_channel", "mod-logs"))
            if log_ch:
                orig_reason = info.get("reason", "N/A")
                orig_mod = info.get("mod", "Unknown")
                embed = discord.Embed(
                    title="Temp-Ban Expired — Auto Unban",
                    description=(
                        f"**User ID:** {user_id_str}\n"
                        f"**Original reason:** {orig_reason}\n"
                        f"**Banned by:** {orig_mod}\n"
                        "User has been automatically unbanned."
                    ),
                    color=discord.Color.green()
                )
                await log_ch.send(embed=embed)
            del data["tempbans"][user_id_str]
            changed = True
        except Exception as e:
            print(f"Tempban unban error for {user_id_str}: {e}")
    if changed:
        save_data(data)

@tempban_expire_loop.before_loop
async def before_tempban_expire():
    await bot.wait_until_ready()

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
    if not timeout_expire_loop.is_running():
        timeout_expire_loop.start()
    if not tempban_expire_loop.is_running():
        tempban_expire_loop.start()
    if not youtube_check_loop.is_running():
        youtube_check_loop.start()
    if not tiktok_check_loop.is_running():
        tiktok_check_loop.start()

@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    now = time.time()
    if guild_id not in raid_tracker:
        raid_tracker[guild_id] = []
    raid_tracker[guild_id].append(now)
    raid_tracker[guild_id] = [t for t in raid_tracker[guild_id] if now - t <= ANTI_RAID_SECONDS]
    if len(raid_tracker[guild_id]) >= ANTI_RAID_THRESHOLD:
        raid_tracker[guild_id] = []
        mod_channel = discord.utils.get(member.guild.text_channels, name=MOD_ONLY_CHANNEL)
        if mod_channel:
            embed = discord.Embed(
                title="⚠️ RAID DETECTED",
                description=(
                    f"**{ANTI_RAID_THRESHOLD}+ accounts** joined within **{ANTI_RAID_SECONDS} seconds**.\n\n"
                    f"Consider enabling server lockdown immediately."
                ),
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Anti-Raid Alert • {datetime.now().strftime('%H:%M:%S')}")
            config = get_config()
            mentions = " ".join([r.mention for r in member.guild.roles if r.name in config.get("mod_roles", [])])
            await mod_channel.send(mentions, embed=embed)

    config = get_config()
    data = load_data()
    data = ensure_keys(data)
    user_id = str(member.id)
    guild_id = str(member.guild.id)
    joined_key = f"{guild_id}_{user_id}"
    if joined_key not in data["joined_before"]:
        data["joined_before"].append(joined_key)
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

    if cooldown_key not in xp_cooldowns or now - xp_cooldowns[cooldown_key] >= config.get("xp_cooldown_seconds", 5):
        xp_cooldowns[cooldown_key] = now
        old_xp = data["xp"][guild_id][user_id]
        old_level = get_level(old_xp)

        xp_gain = config.get("xp_per_message", 5)
        if has_active_xp_boost(data, guild_id, user_id):
            xp_gain *= 2

        data["xp"][guild_id][user_id] += xp_gain
        new_xp = data["xp"][guild_id][user_id]
        new_level = get_level(new_xp)
        # Track message count per guild
        if guild_id not in data["message_counts"]:
            data["message_counts"][guild_id] = {}
        data["message_counts"][guild_id][user_id] = data["message_counts"][guild_id].get(user_id, 0) + 1
        save_data(data)

        if new_level > old_level:
            level_channel = discord.utils.get(message.guild.text_channels, name="levelling-announcements")
            if level_channel:
                embed = discord.Embed(
                    title="Level Up!",
                    description=(
                        f"Congratulations {message.author.mention}!\n\n"
                        f"You have levelled up to **Level {new_level}**! Keep it up!"
                    ),
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=message.author.display_avatar.url)
                await level_channel.send(embed=embed)
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

    if guild_id in active_trivia:
        trivia = active_trivia[guild_id]
        if message.channel.id == trivia["channel_id"] and not message.author.bot:
            if clean_answer(message.content) == clean_answer(trivia["answer"]):
                del active_trivia[guild_id]
                data = load_data()
                data = ensure_keys(data)
                old_xp = data["xp"].get(guild_id, {}).get(user_id, 0)
                data["xp"][guild_id][user_id] = old_xp + TRIVIA_XP_REWARD
                data["points"][guild_id][user_id] = data["points"].get(guild_id, {}).get(user_id, 0) + TRIVIA_POINTS_REWARD
                if guild_id not in data["trivia_wins"]:
                    data["trivia_wins"][guild_id] = {}
                data["trivia_wins"][guild_id][user_id] = data["trivia_wins"][guild_id].get(user_id, 0) + 1
                save_data(data)
                await check_and_announce_level_up(message.guild, message.author, old_xp, old_xp + TRIVIA_XP_REWARD, data, guild_id, user_id)
                await check_and_grant_achievements(message.guild, message.author, data, guild_id, user_id, message.channel)
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
    if str(payload.emoji) == "👍":
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        if channel and channel.name == SUGGESTION_INPUT_CHANNEL:
            try:
                message = await channel.fetch_message(payload.message_id)
                thumbs_count = sum(r.count for r in message.reactions if str(r.emoji) == "👍")
                if thumbs_count >= SUGGESTION_THRESHOLD:
                    data = load_data()
                    data = ensure_keys(data)
                    if str(payload.message_id) not in data["promoted_suggestions"]:
                        data["promoted_suggestions"].append(str(payload.message_id))
                        save_data(data)
                        out = discord.utils.get(guild.text_channels, name=SUGGESTION_OUTPUT_CHANNEL)
                        if out:
                            embed = discord.Embed(title="Popular Suggestion!", description=message.content, color=discord.Color.green())
                            embed.add_field(name="Suggested by", value=message.author.mention, inline=True)
                            embed.add_field(name="Thumbs up", value=str(thumbs_count), inline=True)
                            embed.set_footer(text="This suggestion reached 5 or more thumbs up!")
                            await out.send(embed=embed)
            except Exception as e:
                print(f"Suggestion error: {e}")
    config = get_config()
    rr = config.get("reaction_roles", {})
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    emoji = str(payload.emoji)

    # Gender roles
    stored_message_id = rr.get("message_id")
    mapping = rr.get("mapping", {})
    if stored_message_id and str(payload.message_id) == str(stored_message_id):
        role_name = mapping.get(emoji)
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.add_roles(role)

    # Continent roles
    continent_msg_id = rr.get("continent_message_id")
    if continent_msg_id and str(payload.message_id) == str(continent_msg_id):
        role_name = CONTINENT_ROLES.get(emoji)
        if role_name:
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
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    emoji = str(payload.emoji)

    # Gender roles
    stored_message_id = rr.get("message_id")
    mapping = rr.get("mapping", {})
    if stored_message_id and str(payload.message_id) == str(stored_message_id):
        role_name = mapping.get(emoji)
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.remove_roles(role)

    # Continent roles
    continent_msg_id = rr.get("continent_message_id")
    if continent_msg_id and str(payload.message_id) == str(continent_msg_id):
        role_name = CONTINENT_ROLES.get(emoji)
        if role_name:
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
        name="📊 Levels and XP",
        value=(
            "`?level` - Your level, XP, and progress\n"
            "`?level @user` - Check another user's level\n"
            "`?leaderboard [xp|points|streak|trivia|steals|rps]` - Multiple leaderboards\n"
            "`?profile` - Your full profile (account info, economy, roles)\n"
            "`?profile @user` - View another user's full profile\n"
        ),
        inline=False
    )
    embed.add_field(
        name="🎮 Games and Economy",
        value=(
            "`?rps [rock/paper/scissors]` - Play Rock Paper Scissors\n"
            "`?gamble [amount]` - Gamble your points\n"
            "`?steal @user` - Attempt to steal points\n"
            "`?daily` - Claim daily reward (24h cooldown, streak bonus)\n"
            "`?shop` - Browse the shop\n"
            "`?buy [item_id]` - Purchase an item\n"
            "`?inventory` - View your inventory\n"
            "`?jobs` - Browse jobs\n"
            "`?choosejob [job]` - Pick your job\n"
            "`?work` - Do a shift mini-game (1h cooldown)\n"
            "`?lyric` - Guess the song from a lyric\n"
            "`?moviequote` - Guess the movie from a quote\n"
            "`?emojipuzzle` - Solve an emoji puzzle\n"
            "`?guessgame` - Guess the game from a clue\n"
            "`?achieve` - View your achievements\n"
        ),
        inline=False
    )
    embed.add_field(
        name="📅 Daily Streak Tiers",
        value=(
            "3+ days → **1.5x** rewards\n"
            "7+ days → **2.0x** rewards\n"
            "14+ days → **2.5x** rewards\n"
            "30+ days → **3.0x** rewards\n"
            "Higher streaks also increase your chance of getting a free random item!"
        ),
        inline=False
    )
    embed.add_field(
        name="👤 Community",
        value=(
            "`?birthday DD/MM` - Register your birthday\n"
        ),
        inline=False
    )
    if user_is_mod:
        embed.add_field(
            name="🛡️ Mod Commands",
            value=(
                "`?trivia` - Start a trivia question\n"
                "`?warn @user [reason]` - Warn a member\n"
                "`?warnings @user` - View warning history\n"
                "`?clearwarnings @user` - Clear all warnings\n"
                "`?timeout @user [mins] [reason]` - Timeout a member (auto-expires)\n"
                "`?mute @user [reason]` - Mute a member\n"
                "`?unmute @user` - Unmute a member\n"
                "`?tempban @user [days] [reason]` - Temp-ban 1-30 days (auto-unbans)\n"
                "`?ban @user [reason]` - Permanent ban (Head Mods + Ahmed only)\n"
                "`?purge [amount]` - Delete up to 100 messages\n"
                "`?setuproles` - Post reaction roles message\n"
                "`?wotd` - Manually trigger word of the day\n"
            ),
            inline=False
        )
    embed.add_field(
        name="⭐ Level Roles",
        value="Level 1 → `Level 1`\nLevel 5 → `Level 5` + Attach Files perm\nLevel 10 → `Level 10`",
        inline=False
    )
    embed.set_footer(text="You are viewing this as a Moderator" if user_is_mod else "Mod commands are hidden for regular users")
    await ctx.send(embed=embed)

@bot.command(name="level")
async def level_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    await log_command(ctx.guild, ctx.author, "level", f"on {member.display_name}")
    data = load_data()
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    total_xp = get_user_xp(data, guild_id, user_id)
    current_level = get_level(total_xp)
    xp_needed = xp_for_next_level(total_xp)
    embed = discord.Embed(title=f"{member.display_name}'s Level", color=discord.Color.purple())
    embed.add_field(name="Level", value=str(current_level), inline=True)
    embed.add_field(name="Total XP", value=str(total_xp), inline=True)
    embed.add_field(name="Progress", value=f"{xp_needed} XP to Level {current_level + 1}", inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb"])
async def leaderboard(ctx, board: str = "xp"):
    """?leaderboard [xp|points|streak|trivia|steals|rps] — default xp"""
    await log_command(ctx.guild, ctx.author, "leaderboard", board)
    data = load_data()
    guild_id = str(ctx.guild.id)
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    def build_board(title, colour, raw_dict):
        sorted_items = sorted(raw_dict.items(), key=lambda x: x[1], reverse=True)
        desc = ""
        count = 0
        for uid, val in sorted_items:
            if count >= 10:
                break
            m = ctx.guild.get_member(int(uid))
            if not m:
                continue
            count += 1
            rank = medals.get(count, f"**{count}.**")
            desc += f"{rank} {m.display_name} — **{val}**\n"
        embed = discord.Embed(title=title, description=desc or "No data yet.", color=colour)
        return embed

    board = board.lower()
    if board in ("xp", "level"):
        raw = data.get("xp", {}).get(guild_id, {})
        await ctx.send(embed=build_board("🏆 XP Leaderboard", discord.Color.gold(), raw))
    elif board in ("points", "rich", "richest"):
        raw = data.get("points", {}).get(guild_id, {})
        await ctx.send(embed=build_board("💰 Richest Members", discord.Color.green(), raw))
    elif board in ("streak", "daily"):
        raw = {k.split("_", 1)[1]: v for k, v in data.get("daily_streaks", {}).items() if k.startswith(guild_id + "_")}
        await ctx.send(embed=build_board("🔥 Daily Streak Leaderboard", discord.Color.orange(), raw))
    elif board in ("trivia",):
        raw = data.get("trivia_wins", {}).get(guild_id, {})
        await ctx.send(embed=build_board("🧠 Trivia Wins Leaderboard", discord.Color.blue(), raw))
    elif board in ("steals", "thieves"):
        raw = data.get("steal_counts", {}).get(guild_id, {})
        await ctx.send(embed=build_board("🥷 Top Thieves Leaderboard", discord.Color.dark_grey(), raw))
    elif board in ("rps",):
        raw = data.get("rps_streaks", {}).get(guild_id, {})
        await ctx.send(embed=build_board("✂️ RPS Streak Leaderboard", discord.Color.purple(), raw))
    else:
        await ctx.send(
            "Available boards: `xp`, `points`, `streak`, `trivia`, `steals`, `rps`\n"
            "Example: `?leaderboard points`"
        )

@bot.command(name="profile")
async def profile_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    await log_command(ctx.guild, ctx.author, "profile", f"on {member.display_name}")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    # Economy stats
    total_xp = get_user_xp(data, guild_id, user_id)
    points = get_user_points(data, guild_id, user_id)
    vault = get_vault(data, guild_id, user_id)
    current_level = get_level(total_xp)
    xp_needed = xp_for_next_level(total_xp)
    rps_streak = data.get("rps_streaks", {}).get(guild_id, {}).get(user_id, 0)
    daily_streak = data.get("daily_streaks", {}).get(f"{guild_id}_{user_id}", 0)
    has_shield, shield_remaining = has_active_shield(data, guild_id, user_id)
    boost_active = has_active_xp_boost(data, guild_id, user_id)
    warning_count = len(data.get("warnings", {}).get(guild_id, {}).get(user_id, []))
    birthday = data.get("birthdays", {}).get(user_id, "Not set")

    # Account / server stats
    now = datetime.utcnow()
    created = member.created_at.strftime("%d %b %Y")
    joined = member.joined_at.strftime("%d %b %Y") if member.joined_at else "Unknown"
    account_age = (now - member.created_at.replace(tzinfo=None)).days
    server_age = (now - member.joined_at.replace(tzinfo=None)).days if member.joined_at else 0
    roles = [r.mention for r in member.roles if r.name != "@everyone"]
    roles_str = ", ".join(roles) if roles else "None"

    embed = discord.Embed(title=f"{member.display_name}'s Profile", color=member.color or discord.Color.purple())
    embed.set_thumbnail(url=member.display_avatar.url)

    # Account info section
    embed.add_field(name="Username", value=str(member), inline=True)
    embed.add_field(name="Account Created", value=f"{created} ({account_age} days ago)", inline=True)
    embed.add_field(name="Joined Server", value=f"{joined} ({server_age} days ago)", inline=True)
    embed.add_field(name="Birthday", value=birthday, inline=True)

    # Economy section
    embed.add_field(name="\u200b", value="**— Economy —**", inline=False)
    embed.add_field(name="Level", value=str(current_level), inline=True)
    embed.add_field(name="Total XP", value=str(total_xp), inline=True)
    embed.add_field(name="XP to Next Level", value=str(xp_needed), inline=True)
    embed.add_field(name="Points", value=str(points), inline=True)
    embed.add_field(name="Vault", value=str(vault), inline=True)
    embed.add_field(name="RPS Streak", value=str(rps_streak), inline=True)
    embed.add_field(name="Daily Streak", value=f"🔥 {daily_streak} day{'s' if daily_streak != 1 else ''}", inline=True)
    embed.add_field(name="Shield", value=f"Active ({format_duration(shield_remaining)} left)" if has_shield else "None", inline=True)
    embed.add_field(name="XP Boost", value="Active" if boost_active else "None", inline=True)

    # Roles
    embed.add_field(name=f"Roles ({len(roles)})", value=roles_str[:1000], inline=False)

    # Achievements
    user_achievements = data.get("achievements", {}).get(guild_id, {}).get(user_id, [])
    if user_achievements:
        ach_str = " ".join(ACHIEVEMENTS[k]["icon"] + " " + ACHIEVEMENTS[k]["name"] for k in user_achievements if k in ACHIEVEMENTS)
        embed.add_field(name="Achievements", value=ach_str or "None", inline=False)

    # Mod-only section
    if is_mod(ctx.author):
        embed.add_field(name="Warnings", value=str(warning_count), inline=True)
        embed.add_field(name="Bot Account", value="Yes" if member.bot else "No", inline=True)

    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="daily")
async def daily_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "daily")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    claim_key = f"{guild_id}_{user_id}"

    now_ts = time.time()
    last_claimed_ts = data["daily_claimed"].get(claim_key)

    # Convert old date-string entries to expired (treats them as not claimed)
    if isinstance(last_claimed_ts, str):
        last_claimed_ts = 0

    DAILY_COOLDOWN = 86400  # exactly 24 hours in seconds

    if last_claimed_ts and now_ts - last_claimed_ts < DAILY_COOLDOWN:
        seconds_left = int(DAILY_COOLDOWN - (now_ts - last_claimed_ts))
        hours_left   = seconds_left // 3600
        minutes_left = (seconds_left % 3600) // 60
        next_claim_ts = int(last_claimed_ts + DAILY_COOLDOWN)
        current_streak = data["daily_streaks"].get(claim_key, 1)
        time_str = f"{hours_left}h {minutes_left}m" if hours_left > 0 else f"{minutes_left}m"
        fire_bar = "\U0001f525" * min(current_streak, 10) + ("+" if current_streak > 10 else "")
        embed = discord.Embed(
            title="Already Claimed",
            description=(
                f"{ctx.author.mention} you have already claimed your daily reward.\n\n"
                f"**Next claim available:** <t:{next_claim_ts}:R> (<t:{next_claim_ts}:t>)\n"
                f"**Current streak:** {fire_bar} **{current_streak}**\n\n"
                "Don't miss it or your streak resets!"
            ),
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
        return

    # Update streak
    # Streak breaks if more than 48h have passed since last claim
    if "daily_streaks" not in data:
        data["daily_streaks"] = {}
    current_streak = data["daily_streaks"].get(claim_key, 0)
    if last_claimed_ts and now_ts - last_claimed_ts < 172800:  # within 48h = streak continues
        current_streak += 1
    else:
        current_streak = 1
    data["daily_streaks"][claim_key] = current_streak
    data["daily_claimed"][claim_key] = now_ts  # store Unix float

    # Streak multiplier tiers
    if current_streak >= 30:
        multiplier = 3.0
        tier_label = "30+ day streak"
    elif current_streak >= 14:
        multiplier = 2.5
        tier_label = "14+ day streak"
    elif current_streak >= 7:
        multiplier = 2.0
        tier_label = "7+ day streak"
    elif current_streak >= 3:
        multiplier = 1.5
        tier_label = "3+ day streak"
    else:
        multiplier = 1.0
        tier_label = None

    xp_reward = int(DAILY_XP * multiplier)
    points_reward = int(DAILY_POINTS * multiplier)

    # Daily Booster item doubles on top of streak
    booster_applied = False
    if has_item(data, guild_id, user_id, "daily_boost"):
        xp_reward *= 2
        points_reward *= 2
        remove_item_by_type(data, guild_id, user_id, "daily_boost")
        booster_applied = True

    current_xp = get_user_xp(data, guild_id, user_id)
    current_pts = get_user_points(data, guild_id, user_id)
    set_user_xp(data, guild_id, user_id, current_xp + xp_reward)
    set_user_points(data, guild_id, user_id, current_pts + points_reward)

    # Random item reward — chance scales with streak (15% base, +5% per 7 days, max 60%)
    item_chance = min(0.60, 0.15 + (current_streak // 7) * 0.05)
    bonus_item = None
    if random.random() < item_chance:
        bonus_item_id = random.choice(list(SHOP_ITEMS.keys()))
        bonus_item = SHOP_ITEMS[bonus_item_id]
        add_to_inventory(data, guild_id, user_id, bonus_item_id)

    save_data(data)
    await check_and_announce_level_up(ctx.guild, ctx.author, current_xp, current_xp + xp_reward, data, guild_id, user_id)
    await check_and_grant_achievements(ctx.guild, ctx.author, data, guild_id, user_id, ctx.channel)

    # Build embed
    streak_bar = "🔥" * min(current_streak, 10) + ("+" if current_streak > 10 else "")
    description_lines = [
        f"{ctx.author.mention} claimed their daily reward!\n",
        f"**Day Streak:** {streak_bar} **{current_streak}**",
    ]
    if tier_label:
        description_lines.append(f"**Streak Bonus:** {tier_label} ({multiplier}x multiplier)")
    if booster_applied:
        description_lines.append("**Daily Booster applied!** (extra 2x on top)")
    description_lines += [
        f"\n+**{xp_reward} XP**",
        f"+**{points_reward} Points**",
    ]
    if bonus_item:
        description_lines.append(f"\n🎁 **Bonus item unlocked:** {bonus_item['name']}!")
    description_lines.append("\nCome back tomorrow to keep your streak going!")

    embed = discord.Embed(
        title="Daily Reward Claimed!",
        description="\n".join(description_lines),
        color=discord.Color.green() if current_streak < 7 else discord.Color.gold()
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"Streak: {current_streak} day{'s' if current_streak != 1 else ''} | Miss a day and it resets!")
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
        await ctx.send("Invalid format. Use DD/MM. Example: `?birthday 25/03`")
        return
    data = load_data()
    data = ensure_keys(data)
    data["birthdays"][str(ctx.author.id)] = date
    save_data(data)
    await ctx.send(f"{ctx.author.mention} your birthday has been set to **{date}**. We will announce it on the day!")

# ============================================================
#   ROCK PAPER SCISSORS
# ============================================================

@bot.command(name="rps")
async def rps_cmd(ctx, choice: str = None):
    await log_command(ctx.guild, ctx.author, "rps", choice or "")
    if not choice or choice.lower() not in ["rock", "paper", "scissors"]:
        await ctx.send("Please choose `rock`, `paper`, or `scissors`. Example: `?rps rock`")
        return

    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    player = choice.lower()

    emoji_map = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

    if guild_id not in data["rps_streaks"]:
        data["rps_streaks"][guild_id] = {}
    streak = data["rps_streaks"][guild_id].get(user_id, 0)

    # Determine outcome - completely fair logic
    if player == bot_choice:
        result = "tie"
    elif (player == "rock" and bot_choice == "scissors") or \
         (player == "paper" and bot_choice == "rock") or \
         (player == "scissors" and bot_choice == "paper"):
        result = "win"
    else:
        result = "lose"

    if result == "win":
        streak += 1
        xp_reward = RPS_BASE_XP * streak
        pts_reward = RPS_BASE_POINTS * streak
        current_xp = get_user_xp(data, guild_id, user_id)
        current_pts = get_user_points(data, guild_id, user_id)
        set_user_xp(data, guild_id, user_id, current_xp + xp_reward)
        set_user_points(data, guild_id, user_id, current_pts + pts_reward)
        data["rps_streaks"][guild_id][user_id] = streak
        save_data(data)
        await check_and_announce_level_up(ctx.guild, ctx.author, current_xp, current_xp + xp_reward, data, guild_id, user_id)
        embed = discord.Embed(
            title="You Won! 🎉",
            description=(
                f"You chose {emoji_map[player]} **{player}** — Bot chose {emoji_map[bot_choice]} **{bot_choice}**\n\n"
                f"🔥 Streak: **{streak}**\n"
                f"+**{xp_reward} XP** and +**{pts_reward} points** (streak multiplier applied!)"
            ),
            color=discord.Color.green()
        )
    elif result == "lose":
        data["rps_streaks"][guild_id][user_id] = 0
        save_data(data)
        embed = discord.Embed(
            title="You Lost! 💀",
            description=(
                f"You chose {emoji_map[player]} **{player}** — Bot chose {emoji_map[bot_choice]} **{bot_choice}**\n\n"
                f"Streak reset to 0. Better luck next time!"
            ),
            color=discord.Color.red()
        )
    else:
        embed = discord.Embed(
            title="It's a Tie! 🤝",
            description=(
                f"You both chose {emoji_map[player]} **{player}**\n\n"
                f"Streak maintained at **{streak}**. No rewards for ties."
            ),
            color=discord.Color.yellow()
        )
        data["rps_streaks"][guild_id][user_id] = streak
        save_data(data)

    embed.set_footer(text=f"Current streak: {data['rps_streaks'][guild_id].get(user_id, 0)}")
    await ctx.send(embed=embed)

# ============================================================
#   GAMBLING
# ============================================================

@bot.command(name="gamble")
async def gamble_cmd(ctx, amount: int = None):
    await log_command(ctx.guild, ctx.author, "gamble", str(amount) if amount else "")
    if not amount or amount <= 0:
        await ctx.send("Please specify a valid amount. Example: `?gamble 100`")
        return
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    current_pts = get_user_points(data, guild_id, user_id)
    if amount > current_pts:
        await ctx.send(f"You only have **{current_pts}** points. You cannot gamble more than you have.")
        return
    # Completely random 50/50
    outcome = random.randint(0, 1)
    if outcome == 1:
        set_user_points(data, guild_id, user_id, current_pts + amount)
        save_data(data)
        new_total = current_pts + amount
        embed = discord.Embed(
            title="🎰 You Won!",
            description=(
                f"You gambled **{amount}** points and won!\n\n"
                f"+**{amount}** points\n"
                f"New balance: **{new_total}** points"
            ),
            color=discord.Color.green()
        )
    else:
        set_user_points(data, guild_id, user_id, current_pts - amount)
        save_data(data)
        new_total = current_pts - amount
        embed = discord.Embed(
            title="🎰 You Lost!",
            description=(
                f"You gambled **{amount}** points and lost!\n\n"
                f"-**{amount}** points\n"
                f"New balance: **{new_total}** points"
            ),
            color=discord.Color.red()
        )
    await ctx.send(embed=embed)

# ============================================================
#   SHOP AND INVENTORY
# ============================================================

@bot.command(name="shop")
async def shop_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "shop")
    embed = discord.Embed(title="🛒 Shop", description="Use `?buy [item_id]` to purchase an item.", color=discord.Color.blue())

    shields = "\n".join([f"`{k}` — **{v['name']}** — {v['price']} pts\n{v['description']}" for k, v in SHOP_ITEMS.items() if v["type"] == "shield"])
    boosts = "\n".join([f"`{k}` — **{v['name']}** — {v['price']} pts\n{v['description']}" for k, v in SHOP_ITEMS.items() if v["type"] == "xp_boost"])
    other_types = ["vault", "rob_kit", "insurance", "daily_boost"]
    other = "\n".join([f"`{k}` — **{v['name']}** — {v['price']} pts\n{v['description']}" for k, v in SHOP_ITEMS.items() if v["type"] in other_types])

    embed.add_field(name="🛡️ Shields", value=shields, inline=False)
    embed.add_field(name="⚡ XP Boosts", value=boosts, inline=False)
    embed.add_field(name="🎒 Other", value=other, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="buy")
async def buy_cmd(ctx, item_id: str = None):
    await log_command(ctx.guild, ctx.author, "buy", item_id or "")
    if not item_id or item_id not in SHOP_ITEMS:
        await ctx.send(f"Invalid item ID. Use `?shop` to see available items.")
        return
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    item = SHOP_ITEMS[item_id]
    current_pts = get_user_points(data, guild_id, user_id)
    if current_pts < item["price"]:
        await ctx.send(f"You need **{item['price']}** points but only have **{current_pts}**.")
        return
    set_user_points(data, guild_id, user_id, current_pts - item["price"])
    add_to_inventory(data, guild_id, user_id, item_id)
    # Special handling for vault — each purchase adds capacity, not replaces it
    if item["type"] == "vault":
        current_vault = get_vault(data, guild_id, user_id)
        set_vault(data, guild_id, user_id, current_vault + item["capacity"])
    save_data(data)
    await check_and_grant_achievements(ctx.guild, ctx.author, data, guild_id, user_id, ctx.channel)
    embed = discord.Embed(
        title="Purchase Successful!",
        description=f"You bought **{item['name']}** for **{item['price']}** points!\n{item['description']}",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Remaining balance: {get_user_points(data, guild_id, user_id)} points")
    await ctx.send(embed=embed)

@bot.command(name="inventory", aliases=["inv"])
async def inventory_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "inventory")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    inv = get_inventory(data, guild_id, user_id)
    now = time.time()
    embed = discord.Embed(title=f"{ctx.author.display_name}'s Inventory", color=discord.Color.blue())
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    if not inv:
        embed.description = "Your inventory is empty. Use `?shop` to buy items!"
    else:
        for item_entry in inv:
            item_id = item_entry["item_id"]
            item = SHOP_ITEMS.get(item_id)
            if not item:
                continue
            purchased = item_entry.get("purchased_at", now)
            if item.get("type") in ("shield", "xp_boost"):
                duration = item.get("duration", 0)
                remaining = duration - (now - purchased)
                if remaining > 0:
                    status = f"Active — {format_duration(remaining)} remaining"
                else:
                    status = "Expired"
            else:
                status = "In inventory"
            embed.add_field(name=item["name"], value=status, inline=False)
        vault_amt = get_vault(data, guild_id, user_id)
        if vault_amt > 0:
            embed.add_field(name="🏦 Point Vault", value=f"{vault_amt} points protected", inline=False)
    await ctx.send(embed=embed)

# ============================================================
#   STEAL
# ============================================================

@bot.command(name="steal")
async def steal_cmd(ctx, target: discord.Member = None):
    await log_command(ctx.guild, ctx.author, "steal", f"targeting {target.display_name if target else 'nobody'}")
    if not target:
        await ctx.send("You need to mention someone to steal from. Example: `?steal @user`")
        return
    if target.id == ctx.author.id:
        await ctx.send("You cannot steal from yourself!")
        return
    if target.bot:
        await ctx.send("You cannot steal from a bot!")
        return

    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    thief_id = str(ctx.author.id)
    victim_id = str(target.id)
    now = time.time()

    # Check if victim has an active shield
    shielded, shield_remaining = has_active_shield(data, guild_id, victim_id)
    if shielded:
        # Random chance the thief gets penalised
        penalty_messages = [
            f"🛡️ **Blocked!** {target.display_name}'s shield deflected your grubby little hands right back at you! Their vault is sealed tighter than Fort Knox. Shield expires in **{format_duration(shield_remaining)}**.",
            f"🛡️ **Nope!** You tried to reach into {target.display_name}'s pockets but their shield zapped you like a bug light. Come back in **{format_duration(shield_remaining)}**.",
            f"🛡️ **Denied!** {target.display_name} is protected. You got caught red-handed and the shield guard is not impressed. Try again in **{format_duration(shield_remaining)}**.",
        ]
        if random.random() < 0.4:
            penalty = random.randint(10, 80)
            thief_pts = get_user_points(data, guild_id, thief_id)
            set_user_points(data, guild_id, thief_id, thief_pts - penalty)
            save_data(data)
            await ctx.send(random.choice(penalty_messages) + f"\n\nTo make matters worse, the shield's security system docked you **{penalty} points**.")
        else:
            await ctx.send(random.choice(penalty_messages))
        return

    # Check if victim was robbed in the last 5 hours
    last_robbed_key = f"{guild_id}_{victim_id}"
    last_robbed_time = data["last_robbed"].get(last_robbed_key, 0)
    if now - last_robbed_time < STEAL_COOLDOWN:
        remaining = STEAL_COOLDOWN - (now - last_robbed_time)
        await ctx.send(
            f"😔 {target.display_name} was already robbed recently and has not had time to recover. "
            f"Leave them alone for another **{format_duration(remaining)}**."
        )
        return

    # Check if thief stole recently (30 min cooldown per thief)
    thief_cooldown_key = f"thief_{guild_id}_{thief_id}"
    last_stole = data["last_robbed"].get(thief_cooldown_key, 0)
    if now - last_stole < 1800:
        remaining = 1800 - (now - last_stole)
        await ctx.send(f"⏳ You need to lay low for a bit. You can steal again in **{format_duration(remaining)}**.")
        return

    victim_pts = get_user_points(data, guild_id, victim_id)
    vault_amt = get_vault(data, guild_id, victim_id)
    stealable = max(0, victim_pts - vault_amt)

    if stealable <= 0:
        await ctx.send(f"💸 {target.display_name} has nothing worth stealing or all their points are vaulted. Move on.")
        return

    # Calculate max stealable amount based on balance tiers
    if stealable <= 100:
        max_steal = int(stealable * 0.80)
    elif stealable <= 10000:
        max_steal = int(stealable * 0.85)
    else:
        max_steal = int(stealable * 0.80)

    # Apply robbery kit boost if thief has one
    rob_kit_active = has_item(data, guild_id, thief_id, "rob_kit")
    if rob_kit_active:
        max_steal = int(max_steal * 1.15)

    stolen = random.randint(1, max(1, max_steal))

    # Apply steal insurance — victim keeps points and thief loses some
    if has_item(data, guild_id, victim_id, "insurance"):
        penalty = random.randint(stolen // 2, stolen)
        thief_pts = get_user_points(data, guild_id, thief_id)
        set_user_points(data, guild_id, thief_id, thief_pts - penalty)
        remove_item_by_type(data, guild_id, victim_id, "insurance")
        # Robbery kit still consumed even on failed steal
        if rob_kit_active:
            remove_item_by_type(data, guild_id, thief_id, "rob_kit")
        save_data(data)
        await ctx.send(
            f"🚨 **Steal Insurance triggered!** {target.display_name} had insurance. "
            f"Not only did the steal fail, but you lost **{penalty} points** in the process. Ouch."
        )
        return

    # Consume robbery kit only now that the steal is going ahead
    if rob_kit_active:
        remove_item_by_type(data, guild_id, thief_id, "rob_kit")

    # Execute the steal
    set_user_points(data, guild_id, victim_id, victim_pts - stolen)
    thief_pts = get_user_points(data, guild_id, thief_id)
    set_user_points(data, guild_id, thief_id, thief_pts + stolen)
    data["last_robbed"][last_robbed_key] = now
    data["last_robbed"][thief_cooldown_key] = now
    if guild_id not in data["steal_counts"]:
        data["steal_counts"][guild_id] = {}
    data["steal_counts"][guild_id][thief_id] = data["steal_counts"][guild_id].get(thief_id, 0) + 1
    save_data(data)

    await check_and_grant_achievements(ctx.guild, ctx.author, data, guild_id, thief_id, ctx.channel)
    embed = discord.Embed(
        title="🥷 Successful Heist!",
        description=(
            f"You slipped **{stolen} points** out of {target.mention}'s pocket without them noticing.\n\n"
            f"Their balance went from **{victim_pts}** → **{victim_pts - stolen}**\n"
            f"Your balance is now **{thief_pts + stolen}** points."
        ),
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"{target.display_name} cannot be robbed again for 5 hours.")
    await ctx.send(embed=embed)

    # Notify victim in DM
    try:
        await target.send(
            f"🚨 **You were robbed!** {ctx.author.display_name} just stole **{stolen} points** from you in **{ctx.guild.name}**.\n"
            f"Consider buying a shield from `?shop` to protect yourself next time."
        )
    except discord.Forbidden:
        pass

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
    warning_entry = {"reason": reason, "moderator": str(ctx.author), "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M")}
    data["warnings"][guild_id][user_id].append(warning_entry)
    total_warnings = len(data["warnings"][guild_id][user_id])
    save_data(data)
    try:
        await member.send(f"You have received a warning in **{ctx.guild.name}**.\nReason: {reason}")
    except discord.Forbidden:
        await ctx.send(f"Could not DM {member.mention} but warning has been logged.")
    await ctx.send(f"{member.mention} has been warned. They now have **{total_warnings}** warning(s). Reason: {reason}")
    await log_action(ctx.guild, "Warning", member, ctx.author, reason)
    bot_log = discord.utils.get(ctx.guild.text_channels, name=BOT_LOGS_CHANNEL)
    if bot_log:
        embed = discord.Embed(title="Warning Issued", description=f"{member.mention} warned by {ctx.author.mention}", color=discord.Color.orange())
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Total Warnings", value=str(total_warnings))
        embed.set_footer(text=datetime.now().strftime("%d/%m/%Y %H:%M"))
        await bot_log.send(embed=embed)

@bot.command(name="warnings")
@mod_only()
async def warnings_cmd(ctx, member: discord.Member):
    await log_command(ctx.guild, ctx.author, "warnings", f"on {member.display_name}")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    user_warnings = data.get("warnings", {}).get(guild_id, {}).get(user_id, [])
    embed = discord.Embed(title=f"Warning History — {member.display_name}", color=discord.Color.orange())
    embed.set_thumbnail(url=member.display_avatar.url)
    if not user_warnings:
        embed.description = "This member has no warnings."
    else:
        embed.description = f"This member has **{len(user_warnings)}** warning(s).\n"
        for i, w in enumerate(user_warnings, 1):
            embed.add_field(
                name=f"Warning {i} — {w.get('timestamp', 'Unknown')}",
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
        await ctx.send("A trivia question is already active.")
        return
    trivia_channel = discord.utils.get(ctx.guild.text_channels, name=TRIVIA_CHANNEL)
    if not trivia_channel:
        await ctx.send(f"Could not find **#{TRIVIA_CHANNEL}**.")
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
        description=f"{question['q']}\n\nFirst to answer wins **{TRIVIA_XP_REWARD} XP** and **{TRIVIA_POINTS_REWARD} points**!\nYou have {TRIVIA_TIMEOUT} seconds!",
        color=discord.Color.blue()
    )
    await trivia_channel.send(embed=embed)
    await asyncio.sleep(TRIVIA_TIMEOUT)
    if guild_id in active_trivia:
        del active_trivia[guild_id]
        await trivia_channel.send(f"Time is up! The answer was **{question['a'].title()}**.")

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
    data["wotd_last_posted"] = datetime.now().strftime("%Y-%m-%d")
    save_data(data)
    channel = discord.utils.get(ctx.guild.text_channels, name=WOTD_CHANNEL)
    if not channel:
        await ctx.send(f"Could not find **#{WOTD_CHANNEL}**.")
        return
    embed = discord.Embed(title=f"Word of the Day: {word['word']}", color=discord.Color.teal())
    embed.add_field(name="Type", value=word["type"], inline=True)
    embed.add_field(name="Definition", value=word["definition"], inline=False)
    embed.add_field(name="Example", value=f"*\"{word['example']}\"*", inline=False)
    embed.set_footer(text="Expand your vocabulary every day!")
    await channel.send(embed=embed)
    await ctx.send(f"Word of the day posted in {channel.mention}.")

# ============================================================
#   CASE CHANNEL HELPER
# ============================================================

CASE_CATEGORY = "#4 | Timeouts/Muted"  # Your existing category name

async def create_case_channel(guild, member, action_type, reason, moderator, duration=None, channel_prefix="case"):
    """
    Creates a private read-only channel for the punished member inside
    the existing '#4 | Timeouts/Muted' category.
    - The member can see it but NOT send messages.
    - Mod, Head Mods, and Ahmed (owner role) can see and send.
    """
    config = get_config()
    mod_role_names = config.get("mod_roles", [])

    # Build a safe channel name: prefix-username
    safe_name = "".join(c if c.isalnum() or c == "-" else "-" for c in member.display_name.lower())
    channel_name = f"{channel_prefix}-{safe_name}"[:100]

    # Use the existing category
    category = discord.utils.get(guild.categories, name=CASE_CATEGORY)
    if not category:
        print(f"WARNING: Could not find category '{CASE_CATEGORY}'. Channel will be created at server root.")

    # Only set the member-specific overwrite — everything else syncs from the category
    overwrites = {
        member: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True),
    }

    channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

    # Sync all other permissions from the category so your existing setup is respected
    await channel.edit(sync_permissions=True)

    # Re-apply the member overwrite after sync (sync would have wiped it)
    await channel.set_permissions(member, view_channel=True, send_messages=False, read_message_history=True)

    # Post the case embed
    colour = discord.Color.red() if action_type == "Timed Out" else discord.Color.dark_red()
    desc_lines = [
        f"**Member:** {member.mention} (`{member}`)",
        f"**Action:** {action_type}",
        f"**Reason:** {reason}",
        f"**Moderator:** {moderator.mention}",
    ]
    if duration:
        desc_lines.append(f"**Duration:** {duration}")
    desc_lines += [
        "",
        f"{member.mention}, you can read this channel. You will be told when you can talk from Mods.",
        "This channel will be deleted once your punishment is lifted.",
    ]

    embed = discord.Embed(
        title=f"Case — {action_type}",
        description="\n".join(desc_lines),
        color=colour,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Case opened by {moderator.display_name}")
    await channel.send(embed=embed)
    return channel


async def close_case_channel(guild, member, channel_prefix="case"):
    """Finds and deletes the case channel for a member."""
    safe_name = "".join(c if c.isalnum() or c == "-" else "-" for c in member.display_name.lower())
    channel_name = f"{channel_prefix}-{safe_name}"[:100]
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if channel:
        await channel.send(
            f"{member.mention} your punishment has been lifted. This channel will now be deleted."
        )
        await asyncio.sleep(5)
        await channel.delete(reason="Punishment lifted")


@bot.command(name="timeout")
@mod_only()
async def timeout_cmd(ctx, member: discord.Member, minutes: int = 10, *, reason="No reason provided"):
    await log_command(ctx.guild, ctx.author, "timeout", f"on {member.display_name}")
    try:
        await member.timeout(timedelta(minutes=minutes), reason=reason)

        # Store expiry timestamp so the auto-expire task can clean up
        data = load_data()
        data = ensure_keys(data)
        if "timeout_expiry" not in data:
            data["timeout_expiry"] = {}
        expiry_ts = int(time.time()) + (minutes * 60)
        data["timeout_expiry"][f"{ctx.guild.id}_{member.id}"] = expiry_ts
        save_data(data)

        # Assign the "Timed Out" role
        timeout_role = discord.utils.get(ctx.guild.roles, name="Timed Out")
        if timeout_role and timeout_role not in member.roles:
            await member.add_roles(timeout_role, reason=reason)

        # Build Discord timestamps — these show in the user's local timezone automatically
        ends_at_display   = f"<t:{expiry_ts}:F>"   # e.g. "Tuesday, 1 April 2025 at 17:35"
        ends_at_relative  = f"<t:{expiry_ts}:R>"   # e.g. "in 10 minutes"

        # Create the private case channel with timeout- prefix
        await create_case_channel(
            ctx.guild, member, "Timed Out", reason, ctx.author,
            duration=f"{minutes} minute(s) — ends {ends_at_display} ({ends_at_relative})",
            channel_prefix="timeout"
        )

        await ctx.send(
            f"{member.mention} has been timed out for **{minutes} minute(s)**. "
            f"Timeout ends {ends_at_display} ({ends_at_relative}). Reason: {reason}"
        )
        await log_action(ctx.guild, "Timeout", member, ctx.author, reason, f"{minutes} minutes")
    except discord.Forbidden:
        await ctx.send("I do not have permission to timeout that member.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")


@bot.command(name="mute")
@mod_only()
async def mute_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    await log_command(ctx.guild, ctx.author, "mute", f"on {member.display_name}")
    try:
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            await ctx.send(
                "Could not find a role called **Muted**. "
                "Create it in Server Settings > Roles, then deny Send Messages in every channel for that role."
            )
            return
        if mute_role in member.roles:
            await ctx.send(f"{member.mention} is already muted.")
            return

        await member.add_roles(mute_role, reason=reason)

        # Create the private case channel with muted- prefix
        await create_case_channel(ctx.guild, member, "Muted", reason, ctx.author, channel_prefix="muted")

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

            # Close the muted- channel
            await close_case_channel(ctx.guild, member, channel_prefix="muted")

            await ctx.send(f"{member.mention} has been unmuted.")
            await log_action(ctx.guild, "Unmute", member, ctx.author, "Unmuted by moderator")
        else:
            await ctx.send(f"{member.mention} is not muted.")
    except discord.Forbidden:
        await ctx.send("I do not have permission to unmute that member.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")


@bot.command(name="tempban")
@mod_only()
async def tempban_cmd(ctx, member: discord.Member, days: int = 1, *, reason="No reason provided"):
    """Temp-ban a member for 1-30 days. Bot auto-unbans when time is up."""
    await log_command(ctx.guild, ctx.author, "tempban", f"on {member.display_name}")
    if days < 1 or days > 30:
        await ctx.send("Duration must be 1 to 30 days. Example: `?tempban @user 3 spamming`")
        return
    data = load_data()
    data = ensure_keys(data)
    unban_ts = int(time.time()) + (days * 86400)
    unban_display = f"<t:{unban_ts}:F>"
    try:
        data["tempbans"][str(member.id)] = {
            "guild_id": str(ctx.guild.id),
            "unban_ts": unban_ts,
            "reason": reason,
            "mod": str(ctx.author)
        }
        save_data(data)
        await member.ban(reason=f"Temp-ban ({days}d) by {ctx.author}", delete_message_days=0)
        embed = discord.Embed(
            title="Member Temp-Banned",
            description=(
                f"**Member:** {member.mention}\n"
                f"**Duration:** {days} day(s)\n"
                f"**Unban date:** {unban_display}\n"
                f"**Banned by:** {ctx.author.mention}\n"
                f"**Reason:** {reason}"
            ),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        await log_action(ctx.guild, "Temp-Ban", member, ctx.author, reason, f"{days} day(s)")
    except discord.Forbidden:
        await ctx.send("I do not have permission to ban that member.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")

@bot.command(name="ban")
@mod_only()
async def ban_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    await log_command(ctx.guild, ctx.author, "ban", f"on {member.display_name}")
    senior_roles = ["Head Mods", "Ahmed"]
    if not any(r.name in senior_roles for r in ctx.author.roles) and not ctx.author.guild_permissions.administrator:
        await ctx.send("Only **Head Mods** and the **Ahmed** role can permanently ban members.")
        return
    try:
        await member.ban(reason=f"Banned by {ctx.author} — {reason}")
        embed = discord.Embed(
            title="Member Permanently Banned",
            description=(
                f"**Member:** {member.mention}\n"
                f"**Banned by:** {ctx.author.mention}\n"
                f"**Reason:** {reason}"
            ),
            color=discord.Color.dark_red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        await log_action(ctx.guild, "Permanent Ban", member, ctx.author, reason)
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
        await ctx.send("I do not have permission to delete messages here.")

CONTINENT_ROLES = {
    "🌍": "Africa",
    "🌏": "Asia",
    "🗺️": "Europe",
    "🌎": "North America",
    "🏝️": "South America",
    "🦘": "Oceania",
}

@bot.command(name="setuproles")
@mod_only()
async def setup_roles(ctx):
    await log_command(ctx.guild, ctx.author, "setuproles")
    config = get_config()
    rr = config.get("reaction_roles", {})
    mapping = rr.get("mapping", {})
    channel = discord.utils.get(ctx.guild.text_channels, name=config.get("get_roles_channel", "get-roles"))
    if not channel:
        await ctx.send(f"Could not find **#{config.get('get_roles_channel')}**.")
        return

    # ---- Gender roles (from config) ----
    for emoji, role_name in mapping.items():
        if not discord.utils.get(ctx.guild.roles, name=role_name):
            await ctx.guild.create_role(name=role_name)
            await ctx.send(f"Created role: **{role_name}**")

    description = "React below to receive your role.\n\n**What is your gender?**\n"
    for emoji, role_name in mapping.items():
        description += f"{emoji} — {role_name}\n"
    description += "\nYou can remove your reaction at any time to remove the role."
    embed_gender = discord.Embed(title="Get Your Roles", description=description, color=discord.Color.purple())
    msg_gender = await channel.send(embed=embed_gender)
    for emoji in mapping.keys():
        await msg_gender.add_reaction(emoji)
    config["reaction_roles"]["message_id"] = str(msg_gender.id)
    save_config(config)

    # ---- Continent roles (hardcoded) ----
    for emoji, role_name in CONTINENT_ROLES.items():
        if not discord.utils.get(ctx.guild.roles, name=role_name):
            await ctx.guild.create_role(name=role_name)
            await ctx.send(f"Created role: **{role_name}**")

    continent_desc = "React below to show where you are from.\n\n**Which continent are you from?**\n"
    for emoji, role_name in CONTINENT_ROLES.items():
        continent_desc += f"{emoji} — {role_name}\n"
    continent_desc += "\nYou can remove your reaction at any time to remove the role."
    embed_continent = discord.Embed(title="Continent Roles", description=continent_desc, color=discord.Color.blue())
    msg_continent = await channel.send(embed=embed_continent)
    for emoji in CONTINENT_ROLES.keys():
        await msg_continent.add_reaction(emoji)

    # Store continent message ID for reaction handlers
    config["reaction_roles"]["continent_message_id"] = str(msg_continent.id)
    save_config(config)

    await ctx.send(f"Role messages posted in {channel.mention}. Remember to set permissions on the new roles!")


@bot.command(name="achieve", aliases=["achievements", "badges"])
async def achieve_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    await log_command(ctx.guild, ctx.author, "achieve", f"on {member.display_name}")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    unlocked = data.get("achievements", {}).get(guild_id, {}).get(user_id, [])

    embed = discord.Embed(
        title=f"{member.display_name}'s Achievements",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    if not unlocked:
        embed.description = "No achievements unlocked yet. Keep playing to earn some!"
    else:
        lines = []
        for key, ach in ACHIEVEMENTS.items():
            if key in unlocked:
                lines.append(f"{ach['icon']} **{ach['name']}** — {ach['desc']}")
        embed.description = "\n".join(lines)

    locked = [ach for key, ach in ACHIEVEMENTS.items() if key not in unlocked]
    if locked:
        locked_str = "  ".join(f"🔒 {a['name']}" for a in locked)
        embed.add_field(name="Locked", value=locked_str, inline=False)

    embed.set_footer(text=f"{len(unlocked)}/{len(ACHIEVEMENTS)} achievements unlocked")
    await ctx.send(embed=embed)


# ============================================================
#   FUN QUIZ EVENTS
# ============================================================

LYRIC_QUIZ = [
    {"lyric": "Is this the real life? Is this just fantasy?",                "answer": "bohemian rhapsody", "artist": "Queen"},
    {"lyric": "Never gonna give you up, never gonna let you down",           "answer": "never gonna give you up", "artist": "Rick Astley"},
    {"lyric": "We will, we will rock you",                                   "answer": "we will rock you", "artist": "Queen"},
    {"lyric": "I kissed a girl and I liked it",                              "answer": "i kissed a girl", "artist": "Katy Perry"},
    {"lyric": "Hello, is it me you're looking for?",                         "answer": "hello", "artist": "Lionel Richie"},
    {"lyric": "Baby shark, doo doo doo doo doo doo",                         "answer": "baby shark", "artist": "Pinkfong"},
    {"lyric": "Sweet child o' mine, where do we go?",                        "answer": "sweet child o mine", "artist": "Guns N Roses"},
    {"lyric": "I will always love you",                                      "answer": "i will always love you", "artist": "Whitney Houston"},
    {"lyric": "Smells like teen spirit, here we are now, entertain us",      "answer": "smells like teen spirit", "artist": "Nirvana"},
    {"lyric": "Don't stop believin', hold on to that feelin'",               "answer": "dont stop believin", "artist": "Journey"},
    {"lyric": "Billie Jean is not my lover",                                 "answer": "billie jean", "artist": "Michael Jackson"},
    {"lyric": "You shake my nerves and you rattle my brain",                 "answer": "great balls of fire", "artist": "Jerry Lee Lewis"},
    {"lyric": "Somebody once told me the world is gonna roll me",            "answer": "all star", "artist": "Smash Mouth"},
    {"lyric": "I've got the eye of the tiger, a fighter",                    "answer": "roar", "artist": "Katy Perry"},
    {"lyric": "Just a small town girl, livin in a lonely world",             "answer": "dont stop believin", "artist": "Journey"},
]

MOVIE_QUOTES = [
    {"quote": "May the Force be with you.",                                  "answer": "star wars", "character": "Han Solo"},
    {"quote": "You can't handle the truth!",                                 "answer": "a few good men", "character": "Colonel Jessup"},
    {"quote": "To infinity and beyond!",                                     "answer": "toy story", "character": "Buzz Lightyear"},
    {"quote": "Here's looking at you, kid.",                                 "answer": "casablanca", "character": "Rick Blaine"},
    {"quote": "I'll be back.",                                               "answer": "terminator", "character": "The Terminator"},
    {"quote": "Why so serious?",                                             "answer": "the dark knight", "character": "The Joker"},
    {"quote": "Houston, we have a problem.",                                 "answer": "apollo 13", "character": "Jim Lovell"},
    {"quote": "You talking to me?",                                          "answer": "taxi driver", "character": "Travis Bickle"},
    {"quote": "Life is like a box of chocolates.",                           "answer": "forrest gump", "character": "Forrest Gump"},
    {"quote": "I see dead people.",                                          "answer": "the sixth sense", "character": "Cole Sear"},
    {"quote": "Just keep swimming.",                                         "answer": "finding nemo", "character": "Dory"},
    {"quote": "With great power comes great responsibility.",                "answer": "spider man", "character": "Uncle Ben"},
    {"quote": "Elementary, my dear Watson.",                                 "answer": "sherlock holmes", "character": "Sherlock Holmes"},
    {"quote": "Oh yes, the past can hurt.",                                  "answer": "the lion king", "character": "Rafiki"},
    {"quote": "I am your father.",                                           "answer": "star wars", "character": "Darth Vader"},
]

EMOJI_PUZZLES = [
    {"puzzle": "🦁👑",              "answer": "the lion king",      "hint": "Disney animated film"},
    {"puzzle": "🕷️👨",              "answer": "spider man",         "hint": "Marvel superhero"},
    {"puzzle": "🧊❄️👸",            "answer": "frozen",             "hint": "Disney princess film"},
    {"puzzle": "🚂⚡",              "answer": "harry potter",       "hint": "Wizarding school adventure"},
    {"puzzle": "🦈🎵",              "answer": "jaws",               "hint": "Classic Spielberg thriller"},
    {"puzzle": "🤖🚗",              "answer": "transformers",       "hint": "Robots in disguise"},
    {"puzzle": "🔫💎",              "answer": "james bond",         "hint": "British spy franchise"},
    {"puzzle": "👻👻👻",             "answer": "ghostbusters",       "hint": "Who you gonna call?"},
    {"puzzle": "🦕🌴",              "answer": "jurassic park",      "hint": "Dinosaur theme park"},
    {"puzzle": "🐠🌊🔍",            "answer": "finding nemo",       "hint": "Fish in the ocean"},
    {"puzzle": "⚡🦸🌩️",            "answer": "thor",               "hint": "Marvel god of thunder"},
    {"puzzle": "🧸❤️",              "answer": "toy story",          "hint": "Toys come to life"},
    {"puzzle": "🌙⭐🚀",            "answer": "space jam",          "hint": "Cartoon meets basketball"},
    {"puzzle": "🏎️💨",              "answer": "fast and furious",   "hint": "Street racing franchise"},
    {"puzzle": "🧠🤔💡",            "answer": "inside out",         "hint": "Disney Pixar emotions"},
]

GUESS_THE_GAME = [
    {"clue": "A Swedish sandbox game where you mine, craft and build.",              "answer": "minecraft"},
    {"clue": "100 players drop from a bus. Last one standing wins.",                 "answer": "fortnite"},
    {"clue": "A racing game series by Nintendo featuring go-karts and items.",       "answer": "mario kart"},
    {"clue": "You are a plumber who jumps on mushrooms and saves a princess.",       "answer": "super mario"},
    {"clue": "A battle royale set in the Apex Games with unique Legend abilities.",  "answer": "apex legends"},
    {"clue": "Protect your tower and destroy the enemy's Nexus in 5v5 teams.",       "answer": "league of legends"},
    {"clue": "A first-person shooter with Operators and bomb defusal.",              "answer": "counter strike"},
    {"clue": "An open-world crime game set in cities like Los Santos.",              "answer": "gta"},
    {"clue": "Build a base, survive the storm, and complete the story.",             "answer": "fortnite save the world"},
    {"clue": "A roguelike dungeon crawler where you escape the Underworld.",         "answer": "hades"},
    {"clue": "5v5 tactical shooter where agents have unique abilities.",             "answer": "valorant"},
    {"clue": "A blue hedgehog who runs very fast and collects rings.",               "answer": "sonic"},
    {"clue": "An open-world RPG set in the kingdom of Hyrule.",                      "answer": "zelda"},
    {"clue": "A rhythm game where you tap notes falling to the beat.",               "answer": "guitar hero"},
    {"clue": "Hunt monsters with friends and craft weapons from their parts.",        "answer": "monster hunter"},
]

FUN_QUIZ_TIMEOUT = 30  # seconds to answer
FUN_QUIZ_XP = 20
FUN_QUIZ_POINTS = 60

@bot.command(name="lyric")
async def lyric_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "lyric")
    question = random.choice(LYRIC_QUIZ)
    embed = discord.Embed(
        title="🎵 Name That Song!",
        description=f"*\"{question['lyric']}\"*\n\nWhat song is this from? You have {FUN_QUIZ_TIMEOUT} seconds!",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)
    def check(m): return m.author != ctx.bot.user and m.channel == ctx.channel
    try:
        msg = await ctx.bot.wait_for("message", check=check, timeout=FUN_QUIZ_TIMEOUT)
        if clean_answer(msg.content) == clean_answer(question["answer"]):
            data = load_data()
            data = ensure_keys(data)
            guild_id = str(ctx.guild.id)
            user_id = str(msg.author.id)
            old_xp = get_user_xp(data, guild_id, user_id)
            set_user_xp(data, guild_id, user_id, old_xp + FUN_QUIZ_XP)
            set_user_points(data, guild_id, user_id, get_user_points(data, guild_id, user_id) + FUN_QUIZ_POINTS)
            save_data(data)
            await check_and_announce_level_up(ctx.guild, msg.author, old_xp, old_xp + FUN_QUIZ_XP, data, guild_id, user_id)
            await ctx.send(embed=discord.Embed(
                title="✅ Correct!",
                description=f"{msg.author.mention} got it! The song was **{question['answer'].title()}** by **{question['artist']}**!\n+**{FUN_QUIZ_XP} XP** and +**{FUN_QUIZ_POINTS} points**!",
                color=discord.Color.green()
            ))
        else:
            await ctx.send(f"❌ Wrong! The answer was **{question['answer'].title()}** by **{question['artist']}**.")
    except:
        await ctx.send(f"⏰ Time's up! The song was **{question['answer'].title()}** by **{question['artist']}**.")

@bot.command(name="moviequote", aliases=["quote"])
async def moviequote_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "moviequote")
    question = random.choice(MOVIE_QUOTES)
    embed = discord.Embed(
        title="🎬 Name That Movie!",
        description=f"*\"{question['quote']}\"*\n— *{question['character']}*\n\nWhat movie is this from? You have {FUN_QUIZ_TIMEOUT} seconds!",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)
    def check(m): return m.author != ctx.bot.user and m.channel == ctx.channel
    try:
        msg = await ctx.bot.wait_for("message", check=check, timeout=FUN_QUIZ_TIMEOUT)
        if clean_answer(msg.content) == clean_answer(question["answer"]):
            data = load_data()
            data = ensure_keys(data)
            guild_id = str(ctx.guild.id)
            user_id = str(msg.author.id)
            old_xp = get_user_xp(data, guild_id, user_id)
            set_user_xp(data, guild_id, user_id, old_xp + FUN_QUIZ_XP)
            set_user_points(data, guild_id, user_id, get_user_points(data, guild_id, user_id) + FUN_QUIZ_POINTS)
            save_data(data)
            await check_and_announce_level_up(ctx.guild, msg.author, old_xp, old_xp + FUN_QUIZ_XP, data, guild_id, user_id)
            await ctx.send(embed=discord.Embed(
                title="✅ Correct!",
                description=f"{msg.author.mention} got it! The movie was **{question['answer'].title()}**!\n+**{FUN_QUIZ_XP} XP** and +**{FUN_QUIZ_POINTS} points**!",
                color=discord.Color.green()
            ))
        else:
            await ctx.send(f"❌ Wrong! The answer was **{question['answer'].title()}**.")
    except:
        await ctx.send(f"⏰ Time's up! The answer was **{question['answer'].title()}**.")

@bot.command(name="emojipuzzle", aliases=["emoji"])
async def emojipuzzle_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "emojipuzzle")
    question = random.choice(EMOJI_PUZZLES)
    embed = discord.Embed(
        title="🧩 Emoji Puzzle!",
        description=f"**{question['puzzle']}**\n\n*Hint: {question['hint']}*\n\nWhat movie/show is this? You have {FUN_QUIZ_TIMEOUT} seconds!",
        color=discord.Color.teal()
    )
    await ctx.send(embed=embed)
    def check(m): return m.author != ctx.bot.user and m.channel == ctx.channel
    try:
        msg = await ctx.bot.wait_for("message", check=check, timeout=FUN_QUIZ_TIMEOUT)
        if clean_answer(msg.content) == clean_answer(question["answer"]):
            data = load_data()
            data = ensure_keys(data)
            guild_id = str(ctx.guild.id)
            user_id = str(msg.author.id)
            old_xp = get_user_xp(data, guild_id, user_id)
            set_user_xp(data, guild_id, user_id, old_xp + FUN_QUIZ_XP)
            set_user_points(data, guild_id, user_id, get_user_points(data, guild_id, user_id) + FUN_QUIZ_POINTS)
            save_data(data)
            await check_and_announce_level_up(ctx.guild, msg.author, old_xp, old_xp + FUN_QUIZ_XP, data, guild_id, user_id)
            await ctx.send(embed=discord.Embed(
                title="✅ Correct!",
                description=f"{msg.author.mention} solved it! The answer was **{question['answer'].title()}**!\n+**{FUN_QUIZ_XP} XP** and +**{FUN_QUIZ_POINTS} points**!",
                color=discord.Color.green()
            ))
        else:
            await ctx.send(f"❌ Wrong! The answer was **{question['answer'].title()}**.")
    except:
        await ctx.send(f"⏰ Time's up! The answer was **{question['answer'].title()}**.")

@bot.command(name="guessgame", aliases=["gg"])
async def guessgame_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "guessgame")
    question = random.choice(GUESS_THE_GAME)
    embed = discord.Embed(
        title="🎮 Guess The Game!",
        description=f"{question['clue']}\n\nYou have {FUN_QUIZ_TIMEOUT} seconds!",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)
    def check(m): return m.author != ctx.bot.user and m.channel == ctx.channel
    try:
        msg = await ctx.bot.wait_for("message", check=check, timeout=FUN_QUIZ_TIMEOUT)
        if clean_answer(msg.content) == clean_answer(question["answer"]):
            data = load_data()
            data = ensure_keys(data)
            guild_id = str(ctx.guild.id)
            user_id = str(msg.author.id)
            old_xp = get_user_xp(data, guild_id, user_id)
            set_user_xp(data, guild_id, user_id, old_xp + FUN_QUIZ_XP)
            set_user_points(data, guild_id, user_id, get_user_points(data, guild_id, user_id) + FUN_QUIZ_POINTS)
            save_data(data)
            await check_and_announce_level_up(ctx.guild, msg.author, old_xp, old_xp + FUN_QUIZ_XP, data, guild_id, user_id)
            await ctx.send(embed=discord.Embed(
                title="✅ Correct!",
                description=f"{msg.author.mention} got it! The game was **{question['answer'].title()}**!\n+**{FUN_QUIZ_XP} XP** and +**{FUN_QUIZ_POINTS} points**!",
                color=discord.Color.green()
            ))
        else:
            await ctx.send(f"❌ Wrong! The game was **{question['answer'].title()}**.")
    except:
        await ctx.send(f"⏰ Time's up! The game was **{question['answer'].title()}**.")

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
        await ctx.send("Something went wrong running that command. Please try again.")

# ============================================================
#   RUN BOT
# ============================================================

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise RuntimeError("FATAL: TOKEN environment variable is not set. Set it before starting the bot.")

bot.run(TOKEN)
