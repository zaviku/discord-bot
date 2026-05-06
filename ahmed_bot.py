import discord
from discord.ext import commands, tasks
import json
import os
import re
import shutil
import time
import aiohttp
import random
import string
import asyncio
import xml.etree.ElementTree as ET
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
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(_DATA_DIR, exist_ok=True)
for _fname in ("config.json", "data.json"):
    _src = os.path.join(_APP_DIR, _fname)
    _dst = os.path.join(_DATA_DIR, _fname)
    if not os.path.exists(_dst) and os.path.exists(_src):
        shutil.copy2(_src, _dst)
        print(f"Migrated {_fname} to {_dst}")

TWITCH_CHANNEL  = "ahmed_a_030"
TWITCH_LINK     = "https://www.twitch.tv/ahmed_a_030"
KICK_CHANNEL    = "vexon-gaming"
KICK_LINK       = "https://kick.com/vexon-gaming"
YOUTUBE_LIVE_CHANNEL = "vexonn_gaming"
YOUTUBE_LIVE_LINK    = "https://www.youtube.com/@vexonn_gaming"
LIVE_ANNOUNCE_CHANNEL = "live-announcements"
YOUTUBE_HANDLE = "ahmed_a_030"
YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@ahmed_a_030"
TIKTOK_USERNAME = "vexonn_gaming"
TIKTOK_URL = "https://www.tiktok.com/@vexonn_gaming"
UPLOAD_CHANNEL = "upload-announcement"

# Your Discord user ID — set OWNER_ID as an env var on Railway.
# The bot will DM you whenever something fails silently.
# To find your ID: Discord → Settings → Advanced → Developer Mode ON
# then right-click your name anywhere and click "Copy User ID".
OWNER_ID = int(os.environ.get("OWNER_ID", 0))

# Cooldown tracker for owner DM alerts — prevents spam for repeated errors.
# Key = alert title string, value = last sent timestamp.
_alert_cooldowns: dict = {}
ALERT_COOLDOWN_SECS = 3600  # only DM the same alert type once per hour

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
    "daily_booster":  {"name": "Daily Booster",     "price": 800,  "type": "daily_boost",  "description": "Doubles your next daily reward claim."},
    # Hunting
    "ammo_pack":      {"name": "Ammo Pack",          "price": 200,  "type": "ammo",         "description": "10 shots of ammo for ?hunt. Required to hunt."},
    "hunting_rifle":  {"name": "Hunting Rifle",      "price": 1200, "type": "hunt_rifle",   "description": "Increases max hunt reward by 25%."},
    # Fishing
    "fishing_rod":    {"name": "Fishing Rod",        "price": 500,  "type": "fishing_rod",  "description": "Required to fish. Without it you use bare hands (worse catches)."},
    "bait":           {"name": "Bait Pack",          "price": 150,  "type": "bait",         "description": "5 uses of bait. Guarantees catching something when fishing."},
    "fish_bucket":    {"name": "Fish Bucket",        "price": 400,  "type": "fish_bucket",  "capacity": 10, "description": "Stores up to 10 fish. Sell fish with ?fish sell."},
    # Crime / Beg
    "lucky_charm":    {"name": "Lucky Charm",        "price": 350,  "type": "lucky_charm",  "description": "Doubles success chance on ?crime and ?beg for 1 hour.", "duration": 3600},
    "disguise":       {"name": "Disguise Kit",       "price": 600,  "type": "disguise",     "description": "Halves failure penalty on ?crime for your next attempt."},
    # Scratch
    "scratch_card":   {"name": "Scratch Card",       "price": 100,  "type": "scratch_card", "description": "Scratch to win up to 5x your cost. Try ?scratch."},
    # Adventure
    "adventure_kit":  {"name": "Adventure Kit",      "price": 800,  "type": "adventure_kit","description": "Gives +1 extra life during ?adventure."},
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
    {"word": "Audacious",    "type": "adjective",       "definition": "Showing a willingness to take surprisingly bold risks.",                      "example": "It was an audacious plan that nobody thought would work."},
    {"word": "Belligerent",  "type": "adjective",       "definition": "Hostile and aggressive; eager to fight.",                                    "example": "His belligerent attitude made negotiations impossible."},
    {"word": "Brevity",      "type": "noun",            "definition": "Concise and exact use of words; shortness of time.",                         "example": "The speech was praised for its clarity and brevity."},
    {"word": "Caprice",      "type": "noun",            "definition": "A sudden and unaccountable change of mood or behaviour.",                    "example": "She bought the coat on a caprice, not because she needed it."},
    {"word": "Cogent",       "type": "adjective",       "definition": "Clear, logical, and convincing.",                                            "example": "She made a cogent argument that silenced the critics."},
    {"word": "Contemplate",  "type": "verb",            "definition": "To think about something carefully and at length.",                          "example": "He sat by the window to contemplate his next move."},
    {"word": "Credulous",    "type": "adjective",       "definition": "Having too great a readiness to believe things.",                            "example": "A credulous person is easy to fool with fake news."},
    {"word": "Desolate",     "type": "adjective",       "definition": "Deserted; appearing or feeling very empty and lonely.",                      "example": "The abandoned town felt desolate in the winter rain."},
    {"word": "Eloquent",     "type": "adjective",       "definition": "Fluent or persuasive in speaking or writing.",                               "example": "Her eloquent speech moved the entire crowd."},
    {"word": "Erratic",      "type": "adjective",       "definition": "Not even or regular in pattern; unpredictable.",                             "example": "His erratic behaviour worried his friends."},
    {"word": "Facetious",    "type": "adjective",       "definition": "Treating serious issues with deliberately inappropriate humour.",            "example": "He made a facetious comment during the meeting that annoyed everyone."},
    {"word": "Fallacious",   "type": "adjective",       "definition": "Based on a mistaken belief; misleading.",                                    "example": "His argument was fallacious and easily disproved."},
    {"word": "Fervent",      "type": "adjective",       "definition": "Having or displaying a passionate intensity.",                               "example": "She was a fervent supporter of equal rights."},
    {"word": "Fortitude",    "type": "noun",            "definition": "Courage in pain or adversity.",                                              "example": "He showed great fortitude during his long illness."},
    {"word": "Garrulous",    "type": "adjective",       "definition": "Excessively talkative, especially on trivial matters.",                      "example": "The garrulous host talked for hours without saying much."},
    {"word": "Imperious",    "type": "adjective",       "definition": "Assuming power or authority without justification; domineering.",            "example": "His imperious manner put people off immediately."},
    {"word": "Incredulous",  "type": "adjective",       "definition": "Unwilling or unable to believe something.",                                  "example": "She was incredulous when she heard the news."},
    {"word": "Indolent",     "type": "adjective",       "definition": "Wanting to avoid activity or exertion; lazy.",                               "example": "His indolent attitude cost him the promotion."},
    {"word": "Insolent",     "type": "adjective",       "definition": "Showing a rude and arrogant lack of respect.",                               "example": "The insolent reply earned him a warning from the teacher."},
    {"word": "Languid",      "type": "adjective",       "definition": "Displaying a disinclination to exert oneself.",                              "example": "She felt languid and unmotivated in the summer heat."},
    {"word": "Lucid",        "type": "adjective",       "definition": "Expressed clearly; easy to understand.",                                     "example": "His lucid explanation made the complex topic easy to grasp."},
    {"word": "Magnify",      "type": "verb",            "definition": "To make something seem larger or more important than it really is.",         "example": "The media tends to magnify celebrity scandals."},
    {"word": "Malleable",    "type": "adjective",       "definition": "Easily influenced; able to be shaped or controlled.",                        "example": "Young minds are malleable and shaped by their environment."},
    {"word": "Myopic",       "type": "adjective",       "definition": "Lacking imagination or intellectual insight; short-sighted.",                "example": "His myopic view of the market caused the company to fail."},
    {"word": "Nefarious",    "type": "adjective",       "definition": "Wicked or criminal.",                                                        "example": "The villain's nefarious plans were finally exposed."},
    {"word": "Oblivious",    "type": "adjective",       "definition": "Not aware of or concerned about what is happening around you.",              "example": "She was oblivious to the chaos erupting around her."},
    {"word": "Opulent",      "type": "adjective",       "definition": "Ostentatiously rich and luxurious.",                                         "example": "The hotel lobby was opulent with marble floors and gold fittings."},
    {"word": "Ostentatious", "type": "adjective",       "definition": "Characterised by a showy display intended to impress.",                      "example": "His ostentatious lifestyle made many people uncomfortable."},
    {"word": "Pensive",      "type": "adjective",       "definition": "Engaged in or reflecting deep or serious thought.",                          "example": "She sat pensive and quiet for most of the evening."},
    {"word": "Petulant",     "type": "adjective",       "definition": "Childishly sulky or bad-tempered.",                                          "example": "He gave a petulant response when he didn't get his way."},
    {"word": "Placid",       "type": "adjective",       "definition": "Not easily upset or excited; calm and peaceful.",                            "example": "The placid lake reflected the mountains perfectly."},
    {"word": "Poignant",     "type": "adjective",       "definition": "Evoking a keen sense of sadness or regret.",                                 "example": "The film had a poignant ending that moved everyone to tears."},
    {"word": "Prudent",      "type": "adjective",       "definition": "Acting with care and thought for the future.",                               "example": "It was prudent to save money before taking the risk."},
    {"word": "Raucous",      "type": "adjective",       "definition": "Making or constituting a disturbingly harsh or loud noise.",                 "example": "The raucous crowd celebrated long into the night."},
    {"word": "Sagacious",    "type": "adjective",       "definition": "Having or showing keen mental discernment and good judgement.",              "example": "The sagacious elder gave advice that proved exactly right."},
    {"word": "Sanguine",     "type": "adjective",       "definition": "Optimistic or positive, especially in a difficult situation.",               "example": "Despite setbacks, she remained sanguine about the outcome."},
    {"word": "Sardonic",     "type": "adjective",       "definition": "Grimly mocking or cynical.",                                                 "example": "He gave a sardonic laugh at the irony of the situation."},
    {"word": "Scrutinise",   "type": "verb",            "definition": "To examine or inspect closely and thoroughly.",                              "example": "The auditors scrutinised every line of the financial report."},
    {"word": "Steadfast",    "type": "adjective",       "definition": "Resolutely or dutifully firm and unwavering.",                               "example": "She was steadfast in her support for the cause."},
    {"word": "Superfluous",  "type": "adjective",       "definition": "Unnecessary, especially through being more than enough.",                   "example": "The lengthy introduction felt superfluous to the report."},
    {"word": "Sycophant",    "type": "noun",            "definition": "A person who acts obsequiously to gain advantage.",                          "example": "The boss was surrounded by sycophants who never challenged him."},
    {"word": "Tangible",     "type": "adjective",       "definition": "Perceptible by touch; clear and definite; real.",                           "example": "There was a tangible sense of excitement in the room."},
    {"word": "Trepidation",  "type": "noun",            "definition": "A feeling of fear or anxiety about something that may happen.",              "example": "She approached the stage with trepidation."},
    {"word": "Truculent",    "type": "adjective",       "definition": "Eager or quick to argue or fight; aggressively defiant.",                    "example": "His truculent response shocked the interviewer."},
    {"word": "Turbulent",    "type": "adjective",       "definition": "Characterised by conflict, disorder, or confusion.",                         "example": "It was a turbulent period in the country's history."},
    {"word": "Vacuous",      "type": "adjective",       "definition": "Having or showing a lack of thought or intelligence.",                       "example": "The conversation felt vacuous and pointless."},
    {"word": "Venerable",    "type": "adjective",       "definition": "Accorded a great deal of respect, especially because of age.",               "example": "The venerable professor had taught at the university for decades."},
    {"word": "Vivacious",    "type": "adjective",       "definition": "Attractively lively and animated.",                                          "example": "Her vivacious personality made her the life of every party."},
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
    {"q": "What is the capital of Italy?", "a": "rome", "hints": ["It is in southern Europe", "Famous for the Colosseum", "Also called the Eternal City"]},
    {"q": "What is the chemical symbol for iron?", "a": "fe", "hints": ["It comes from the Latin word", "The symbol is two letters", "Think ferrous"]},
    {"q": "How many sides does a pentagon have?", "a": "5", "hints": ["Less than a hexagon", "More than a square", "The US defense building has this shape"]},
    {"q": "What is the fastest bird in the world?", "a": "peregrine falcon", "hints": ["It is a bird of prey", "It dives to catch food", "It can reach over 300 km/h"]},
    {"q": "What year did the Berlin Wall fall?", "a": "1989", "hints": ["It was in the 1980s", "The Cold War was ending", "German reunification followed"]},
    {"q": "What is the largest organ in the human body?", "a": "skin", "hints": ["You can see it", "It covers your entire body", "It is not an internal organ"]},
    {"q": "What is the capital of Canada?", "a": "ottawa", "hints": ["It is not Toronto", "It is not Vancouver", "It is in Ontario province"]},
    {"q": "How many colours are in a rainbow?", "a": "7", "hints": ["More than five", "Less than nine", "Roy G Biv is a mnemonic"]},
    {"q": "What element has the atomic number 1?", "a": "hydrogen", "hints": ["It is the lightest element", "It makes up most of the sun", "H is its symbol"]},
    {"q": "Who wrote Romeo and Juliet?", "a": "william shakespeare", "hints": ["He was English", "He also wrote Hamlet", "He lived in the 1500s and 1600s"]},
    {"q": "What is the boiling point of water in Celsius?", "a": "100", "hints": ["It is a round number", "Higher than body temperature", "At sea level"]},
    {"q": "What is the most downloaded app of all time?", "a": "tiktok", "hints": ["It is social media", "Short videos", "Very popular with younger people"]},
    {"q": "What is the national animal of Australia?", "a": "kangaroo", "hints": ["It has a pouch", "It hops to move", "It is on the Australian coat of arms"]},
    {"q": "How many minutes are in a full day?", "a": "1440", "hints": ["Multiply hours in a day by 60", "More than 1000", "Less than 2000"]},
    {"q": "What is the name of the galaxy we live in?", "a": "milky way", "hints": ["It sounds like a chocolate bar", "It is a spiral galaxy", "You can see part of it on clear nights"]},
    {"q": "What sport is Serena Williams famous for?", "a": "tennis", "hints": ["It uses a racket", "Played at Wimbledon", "The ball is yellow and round"]},
    {"q": "What is the main ingredient in guacamole?", "a": "avocado", "hints": ["It is a green fruit", "It has a large seed", "Popular in Mexican food"]},
    {"q": "What country is the Amazon rainforest mostly in?", "a": "brazil", "hints": ["It is in South America", "Portuguese is spoken there", "It has the Amazon river"]},
    {"q": "What does CPU stand for?", "a": "central processing unit", "hints": ["It is computer hardware", "The brain of the computer", "Starts with Central"]},
    {"q": "How many teeth does an adult human have?", "a": "32", "hints": ["Including wisdom teeth", "More than 28", "Less than 36"]},
]

recent_trivia = {}

# Categorised trivia for ?trivia [category]
TRIVIA_CATEGORIES = {
    "gaming": [
        {"q": "What year was Minecraft first released publicly?", "a": "2009"},
        {"q": "What company made Fortnite?", "a": "epic games"},
        {"q": "What is the best-selling video game of all time?", "a": "minecraft"},
        {"q": "What console did the original Halo launch on?", "a": "xbox"},
        {"q": "What game features a character named Master Chief?", "a": "halo"},
        {"q": "What company makes the Call of Duty series?", "a": "activision"},
        {"q": "How many stars does it take to unlock a new world in Mario 64?", "a": "70"},
        {"q": "What is the name of the main character in The Legend of Zelda?", "a": "link"},
        {"q": "What game is played on a map called Verdansk?", "a": "warzone"},
        {"q": "What does GTA stand for?", "a": "grand theft auto"},
        {"q": "What game has characters called Among Crewmates and Impostors?", "a": "among us"},
        {"q": "What year was the PlayStation 5 released?", "a": "2020"},
        {"q": "What is the rarest item tier in most games?", "a": "legendary"},
        {"q": "What game features a battle pass with 100 tiers?", "a": "fortnite"},
        {"q": "What animal is Sonic the Hedgehog?", "a": "hedgehog"},
    ],
    "sports": [
        {"q": "How many players are on a standard football (soccer) team?", "a": "11"},
        {"q": "How many points is a touchdown worth in American football?", "a": "6"},
        {"q": "What country invented basketball?", "a": "usa"},
        {"q": "How many sets are in a standard tennis match for men?", "a": "5"},
        {"q": "What sport is played at Wimbledon?", "a": "tennis"},
        {"q": "How many players are on a basketball team?", "a": "5"},
        {"q": "What colour is the centre circle on a snooker table?", "a": "pink"},
        {"q": "What sport uses a shuttlecock?", "a": "badminton"},
        {"q": "How many holes are on a standard golf course?", "a": "18"},
        {"q": "Which country has won the most FIFA World Cups?", "a": "brazil"},
        {"q": "What is the diameter of a basketball hoop in inches?", "a": "18"},
        {"q": "In cricket how many balls are in an over?", "a": "6"},
        {"q": "What sport is Usain Bolt famous for?", "a": "sprinting"},
        {"q": "What sport does Serena Williams play?", "a": "tennis"},
        {"q": "How many players are in a rugby union team?", "a": "15"},
    ],
    "music": [
        {"q": "How many strings does a standard guitar have?", "a": "6"},
        {"q": "What is the most streamed song on Spotify of all time?", "a": "blinding lights"},
        {"q": "What band was Beyonce in before going solo?", "a": "destinys child"},
        {"q": "How many members are in BTS?", "a": "7"},
        {"q": "What does DJ stand for?", "a": "disc jockey"},
        {"q": "What instrument does a pianist play?", "a": "piano"},
        {"q": "What are the four main types of music note duration?", "a": "whole half quarter eighth"},
        {"q": "What country does K-pop come from?", "a": "south korea"},
        {"q": "What is the name of Drakes record label?", "a": "ovo sound"},
        {"q": "How many keys does a standard piano have?", "a": "88"},
        {"q": "What rapper has the most Grammys?", "a": "beyonce"},
        {"q": "What year did Michael Jackson release Thriller?", "a": "1982"},
        {"q": "What music streaming service has the most users?", "a": "spotify"},
        {"q": "How many octaves are on a standard piano?", "a": "7"},
        {"q": "What is the name of Kanye Wests old name?", "a": "ye"},
    ],
    "geography": [
        {"q": "What is the capital of Australia?", "a": "canberra"},
        {"q": "What is the longest river in the world?", "a": "nile"},
        {"q": "What country has the most natural lakes?", "a": "canada"},
        {"q": "What is the smallest country in the world?", "a": "vatican city"},
        {"q": "What is the tallest mountain in the world?", "a": "mount everest"},
        {"q": "What is the capital of Japan?", "a": "tokyo"},
        {"q": "What ocean is the largest?", "a": "pacific"},
        {"q": "How many continents are there?", "a": "7"},
        {"q": "What country is the Amazon rainforest mostly in?", "a": "brazil"},
        {"q": "What is the largest desert in the world?", "a": "sahara"},
        {"q": "What is the capital of Canada?", "a": "ottawa"},
        {"q": "What is the capital of Germany?", "a": "berlin"},
        {"q": "What is the largest country by area?", "a": "russia"},
        {"q": "What sea separates Europe and Africa?", "a": "mediterranean"},
        {"q": "What country has the most people?", "a": "india"},
    ],
    "science": [
        {"q": "What is the chemical symbol for gold?", "a": "au"},
        {"q": "What is the powerhouse of the cell?", "a": "mitochondria"},
        {"q": "How many bones are in the adult human body?", "a": "206"},
        {"q": "What planet is known as the Red Planet?", "a": "mars"},
        {"q": "What gas do plants absorb?", "a": "carbon dioxide"},
        {"q": "What is the boiling point of water in Celsius?", "a": "100"},
        {"q": "What element has atomic number 1?", "a": "hydrogen"},
        {"q": "What is the speed of light in km per second?", "a": "300000"},
        {"q": "What is the largest organ in the human body?", "a": "skin"},
        {"q": "How many hearts does an octopus have?", "a": "3"},
        {"q": "What planet has the most moons?", "a": "saturn"},
        {"q": "What does DNA stand for?", "a": "deoxyribonucleic acid"},
        {"q": "What is the chemical symbol for water?", "a": "h2o"},
        {"q": "What is the hardest natural substance?", "a": "diamond"},
        {"q": "How many chromosomes do humans have?", "a": "46"},
    ],
}
active_trivia = {}   # {guild_id: {answer, hints, hint_index, channel_id, question}}
raid_tracker = {}
# {guild_id: {channel_id: {user_id: [timestamps]}}} — tracks per-channel unique-user activity
message_activity = {}
AUTO_TRIVIA_THRESHOLD = 5    # unique non-bot users in window to trigger auto trivia
AUTO_TRIVIA_WINDOW    = 60   # seconds to count messages in
fun_quiz_activity = {}        # same structure for fun quiz
AUTO_FUN_QUIZ_THRESHOLD = 5  # unique non-bot users to trigger a fun quiz
AUTO_FUN_QUIZ_WINDOW    = 120 # 2 minute window
active_fun_quiz = {}          # {guild_id: True} to prevent overlap

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

# _data_lock guards all file reads/writes so two commands
# running at the same time cannot corrupt data.json.
_data_lock = asyncio.Lock()

def _load_data_sync():
    """Synchronous inner — called only from the executor."""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Data load error: {e}")
    return {}

def _save_data_sync(data):
    """Synchronous inner — called only from the executor."""
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, DATA_FILE)

def load_data():
    """
    Synchronous convenience shim — safe to call from sync helper functions
    and at startup (before the event loop is running).
    All async command code should use load_data_safe() instead.
    """
    return _load_data_sync()

def save_data(data):
    """
    Synchronous convenience shim — safe to call from sync contexts and startup.
    All async command code should use save_data_safe() instead.
    """
    _save_data_sync(data)

async def load_data_safe():
    """
    Async-safe: acquires the data lock then runs the file read in a thread
    executor so the Discord heartbeat is never blocked by disk I/O.
    """
    loop = asyncio.get_event_loop()
    async with _data_lock:
        return await loop.run_in_executor(None, _load_data_sync)

async def save_data_safe(data):
    """
    Async-safe: acquires the data lock then runs the file write in a thread
    executor so the Discord heartbeat is never blocked by disk I/O.
    """
    import copy
    snapshot = copy.deepcopy(data)   # snapshot so callers can modify data freely
    loop = asyncio.get_event_loop()
    async with _data_lock:
        await loop.run_in_executor(None, _save_data_sync, snapshot)

def ensure_keys(data):
    defaults = {
        "xp": {}, "points": {}, "joined_before": [],
        "twitch_live": False, "kick_live": False, "youtube_live": False, "daily_claimed": {},
        "birthdays": {}, "birthday_announced": {},
        "warnings": {}, "promoted_suggestions": [],
        "wotd_used": [], "inventories": {},
        "rps_streaks": {}, "last_robbed": {},
        "vault": {}, "xp_boosts": {},
        "daily_streaks": {}, "timeout_expiry": {}, "tempbans": {}, "saved_roles": {},
        "last_youtube_id": None, "last_tiktok_id": None,
        "message_counts": {}, "trivia_wins": {}, "steal_counts": {},
        "achievements": {}, "suggestions_made": {}, "job_data": {},
        "counting": {}, "fish_buckets": {}, "timezones": {},
        "bios": {}, "titles": {}, "clans": {}, "clan_members": {},
        "partnerships": {}, "partner_requests": {},
        "crafting_materials": {}, "stocks": {}, "stock_portfolio": {},
        "gamble_wins": {},
        "weekly_xp": {}, "weekly_points": {}, "weekly_reset": 0,
        "mod_notes": {}, "automod_stats": {},
        "trivia_streaks": {}, "spin_claimed": {},
        "wordle_state": {}, "blackjack_active": {},
        "clan_wars": {}
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

def xp_needed_for_level(level):
    """XP required to reach a specific level (MEE6-style formula)."""
    return 5 * (level ** 2) + 50 * level + 100

def total_xp_for_level(level):
    """Cumulative XP needed to reach a given level from 0."""
    return sum(xp_needed_for_level(l) for l in range(level))

def get_level(total_xp):
    """Return the level for a given total XP amount."""
    level = 0
    while total_xp >= xp_needed_for_level(level):
        total_xp -= xp_needed_for_level(level)
        level += 1
    return level

def xp_for_next_level(total_xp):
    """XP remaining until the next level-up."""
    level = get_level(total_xp)
    spent = total_xp_for_level(level)
    xp_into_level = total_xp - spent
    needed = xp_needed_for_level(level)
    return needed - xp_into_level

def is_mod(member):
    config = get_config()
    mod_roles = config.get("mod_roles", [])
    perms = member.guild_permissions
    return (
        any(role.name in mod_roles for role in member.roles)
        or perms.administrator
        or perms.manage_messages
        or perms.kick_members
        or perms.ban_members
        or perms.moderate_members
    )

def clean_answer(text):
    return text.lower().strip().translate(str.maketrans("", "", string.punctuation))

def fuzzy_match(user_answer, correct_answer):
    """Return True if the user answer is close enough to the correct answer."""
    u = clean_answer(user_answer)
    c = clean_answer(correct_answer)
    if u == c:
        return True
    # Allow partial match — user answer contains all words of the correct answer
    correct_words = c.split()
    user_words = u.split()
    if all(w in user_words for w in correct_words):
        return True
    # Allow if user answer is contained in correct answer (e.g. "shakespeare" for "william shakespeare")
    if len(u) >= 4 and u in c:
        return True
    # Simple character similarity — allow 1 typo for short words, 2 for longer
    if len(c) <= 5 and len(u) <= 5:
        return False  # short answers must match exactly
    errors = sum(1 for a, b in zip(u.ljust(len(c)), c.ljust(len(u))) if a != b)
    max_errors = 1 if len(c) <= 8 else 2
    return errors <= max_errors

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
        level_channel = discord.utils.get(guild.text_channels, name=get_config().get("level_up_channel", "levelling-announcements"))
        if level_channel:
            await level_channel.send(f"{member.mention} has reached level **{new_level}**!")
        if new_level in LEVEL_ROLES:
            role_name = LEVEL_ROLES[new_level]
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role not in member.roles:
                await member.add_roles(role)
                if new_level == 5:
                    pass  # Level 5 role perms are configured manually in Server Settings

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
#   OWNER DM ALERTS
# ============================================================

async def dm_owner(title: str, detail: str, cooldown: bool = True):
    """
    DM the bot owner (Vexon) whenever something fails silently.
    title    — short summary, e.g. "Twitch check failed"
    detail   — full explanation of what went wrong and what to check
    cooldown — if True, the same alert title is only sent once per hour
               to prevent spam from repeated failures (default: True)
    Set the OWNER_ID environment variable on Railway to your Discord user ID.
    """
    if not OWNER_ID:
        return  # Not configured — skip silently

    # Cooldown check — don't spam the same error every 10 minutes
    if cooldown:
        last_sent = _alert_cooldowns.get(title, 0)
        if time.time() - last_sent < ALERT_COOLDOWN_SECS:
            print(f"dm_owner suppressed (cooldown): {title}")
            return
        _alert_cooldowns[title] = time.time()

    try:
        user = await bot.fetch_user(OWNER_ID)
        if user:
            embed = discord.Embed(
                title=f"⚠️ Bot Alert: {title}",
                description=detail,
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="Vexon's Bot — Automatic Alert")
            await user.send(embed=embed)
    except Exception as e:
        print(f"dm_owner failed: {e}")  # Don't let alert failure break anything


# ============================================================
#   LIVE STREAM CHECKERS  (Twitch · Kick · YouTube Live)
# ============================================================

_twitch_token_cache = {"token": None, "expires_at": 0}

async def get_twitch_token():
    now = time.time()
    if _twitch_token_cache["token"] and now < _twitch_token_cache["expires_at"]:
        return _twitch_token_cache["token"]
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Twitch: TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET not set in environment variables. Cannot check live status.")
        return None
    params = {"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://id.twitch.tv/oauth2/token", params=params) as resp:
                result = await resp.json()
                if "access_token" not in result:
                    print(f"Twitch: Token request failed. Response: {result}")
                    await dm_owner(
                        "Twitch token request failed",
                        f"The bot could not get a Twitch access token.\n\n"
                        f"**Response from Twitch:** `{result}`\n\n"
                        f"**What to check:**\n"
                        f"• Are `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` set correctly on Railway?\n"
                        f"• Go to dev.twitch.tv and confirm your app credentials are still valid."
                    )
                    return None
                token = result["access_token"]
                expires_in = result.get("expires_in", 3600 * 24 * 30)
                _twitch_token_cache["token"] = token
                _twitch_token_cache["expires_at"] = now + expires_in - 300
                print(f"Twitch: Got new access token (expires in {expires_in}s)")
                return token
    except Exception as e:
        print(f"Twitch: Token fetch error: {e}")
        return None

async def check_twitch_live():
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    token = await get_twitch_token()
    if not token:
        return False
    headers = {"Client-ID": client_id, "Authorization": f"Bearer {token}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.twitch.tv/helix/streams?user_login={TWITCH_CHANNEL}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 401:
                    print("Twitch: 401 Unauthorized — token may be invalid, clearing cache")
                    _twitch_token_cache["token"] = None
                    _twitch_token_cache["expires_at"] = 0
                    await dm_owner(
                        "Twitch 401 Unauthorized",
                        "The Twitch API returned **401 Unauthorized**.\n\n"
                        "**What to check:**\n"
                        "• Your `TWITCH_CLIENT_SECRET` may have expired or been regenerated.\n"
                        "• Go to dev.twitch.tv → your app → regenerate the secret, then update Railway."
                    )
                    return False
                if resp.status != 200:
                    print(f"Twitch: API returned HTTP {resp.status}")
                    await dm_owner(
                        f"Twitch API error (HTTP {resp.status})",
                        f"The Twitch streams API returned an unexpected status code: **{resp.status}**\n\n"
                        f"This usually resolves itself. If it keeps happening, check dev.twitch.tv for outages."
                    )
                    return False
                result = await resp.json()
                streams = result.get("data", [])
                is_live = len(streams) > 0
                print(f"Twitch: checked {TWITCH_CHANNEL} — {'LIVE' if is_live else 'offline'}")
                return is_live
    except Exception as e:
        print(f"Twitch: API check error: {e}")
        return False

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
        print(f"Twitch: {TWITCH_CHANNEL} just went live — sending announcements")
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=LIVE_ANNOUNCE_CHANNEL)
            if not channel:
                print(f"Twitch: no #{LIVE_ANNOUNCE_CHANNEL} channel found in {guild.name}")
                continue
            embed = discord.Embed(
                title="Vexon is now LIVE on Twitch!",
                description=f"Come and join the stream!\n\n[Click here to watch]({TWITCH_LINK})",
                color=discord.Color.purple()
            )
            alert_role, _ = await get_or_create_alert_role(
                guild, "Live Alerts", discord.Colour.red()
            )
            embed.set_footer(text="Twitch Notification")
            await channel.send(alert_role.mention, embed=embed)
            print(f"Twitch: announcement sent in {guild.name} #{channel.name}")
    elif not is_live and was_live:
        data["twitch_live"] = False
        save_data(data)
        print(f"Twitch: {TWITCH_CHANNEL} went offline")

@twitch_check_loop.before_loop
async def before_twitch():
    await bot.wait_until_ready()


# ── Kick Live Checker ─────────────────────────────────────────
# Kick has no public API — we scrape the channel page.
# The page contains "is_live":true/false in its JSON data.

async def check_kick_live():
    """Returns True if the Kick channel is currently live."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://kick.com/api/v1/channels/{KICK_CHANNEL}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    print(f"Kick: API returned HTTP {resp.status}")
                    await dm_owner(
                        f"Kick API error (HTTP {resp.status})",
                        f"The Kick channel API returned status **{resp.status}** for `{KICK_CHANNEL}`.\n\n"
                        f"**What to check:**\n"
                        f"• Is your Kick channel name still `{KICK_CHANNEL}`?\n"
                        f"• Check kick.com/api/v1/channels/{KICK_CHANNEL} in your browser."
                    )
                    return False
                data = await resp.json()
                livestream = data.get("livestream")
                is_live = livestream is not None
                print(f"Kick: checked {KICK_CHANNEL} — {'LIVE' if is_live else 'offline'}")
                return is_live
    except Exception as e:
        print(f"Kick: check error: {e}")
        return False

@tasks.loop(minutes=2)
async def kick_check_loop():
    data = load_data()
    data = ensure_keys(data)
    try:
        is_live = await check_kick_live()
    except Exception as e:
        print(f"Kick check error: {e}")
        return
    was_live = data.get("kick_live", False)
    if is_live and not was_live:
        data["kick_live"] = True
        save_data(data)
        print(f"Kick: {KICK_CHANNEL} just went live — sending announcements")
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=LIVE_ANNOUNCE_CHANNEL)
            if not channel:
                continue
            embed = discord.Embed(
                title="Vexon is now LIVE on Kick!",
                description=f"Come and watch the stream!\n\n[Click here to watch]({KICK_LINK})",
                color=discord.Color.green()
            )
            embed.set_footer(text="Kick Notification")
            alert_role, _ = await get_or_create_alert_role(guild, "Live Alerts", discord.Colour.red())
            await channel.send(alert_role.mention, embed=embed)
            print(f"Kick: announcement sent in {guild.name}")
    elif not is_live and was_live:
        data["kick_live"] = False
        save_data(data)
        print(f"Kick: {KICK_CHANNEL} went offline")

@kick_check_loop.before_loop
async def before_kick():
    await bot.wait_until_ready()


# ── YouTube Live Checker ──────────────────────────────────────
# Uses the YouTube Data API v3 search endpoint (requires YOUTUBE_API_KEY env var).
# Falls back gracefully if the key isn't set.

async def check_youtube_live():
    """Returns True if the YouTube channel is currently live streaming."""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    channel_id = os.environ.get("YOUTUBE_CHANNEL_ID")
    if not api_key:
        # No API key — silently skip (don't spam logs)
        return False
    if not channel_id:
        # Try to resolve it the same way the upload checker does
        channel_id = await get_youtube_channel_id()
        if not channel_id:
            return False
    try:
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "eventType": "live",
            "type": "video",
            "key": api_key,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    print(f"YouTube Live: API returned HTTP {resp.status}")
                    await dm_owner(
                        f"YouTube Live API error (HTTP {resp.status})",
                        f"The YouTube Data API returned **{resp.status}** when checking for live streams.\n\n"
                        f"**Common causes:**\n"
                        f"• **403** — API quota exceeded (resets at 8am UK time daily) or key restrictions wrong\n"
                        f"• **400** — `YOUTUBE_API_KEY` may be missing or invalid on Railway\n"
                        f"• **401** — Key may have been deleted from Google Cloud Console"
                    )
                    return False
                result = await resp.json()
                items = result.get("items", [])
                is_live = len(items) > 0
                print(f"YouTube Live: checked {YOUTUBE_LIVE_CHANNEL} — {'LIVE' if is_live else 'offline'}")
                return is_live
    except Exception as e:
        print(f"YouTube Live: check error: {e}")
        return False

@tasks.loop(minutes=15)
async def youtube_live_check_loop():
    data = load_data()
    data = ensure_keys(data)
    try:
        is_live = await check_youtube_live()
    except Exception as e:
        print(f"YouTube Live check error: {e}")
        return
    was_live = data.get("youtube_live", False)
    if is_live and not was_live:
        data["youtube_live"] = True
        save_data(data)
        print(f"YouTube Live: {YOUTUBE_LIVE_CHANNEL} just went live — sending announcements")
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=LIVE_ANNOUNCE_CHANNEL)
            if not channel:
                continue
            embed = discord.Embed(
                title="Vexon is now LIVE on YouTube!",
                description=f"Come and watch the stream!\n\n[Click here to watch]({YOUTUBE_LIVE_LINK})",
                color=discord.Color.red()
            )
            embed.set_footer(text="YouTube Live Notification")
            alert_role, _ = await get_or_create_alert_role(guild, "Live Alerts", discord.Colour.red())
            await channel.send(alert_role.mention, embed=embed)
            print(f"YouTube Live: announcement sent in {guild.name}")
    elif not is_live and was_live:
        data["youtube_live"] = False
        save_data(data)
        print(f"YouTube Live: {YOUTUBE_LIVE_CHANNEL} went offline")

@youtube_live_check_loop.before_loop
async def before_youtube_live():
    await bot.wait_until_ready()


# ============================================================
#   ALERT ROLE HELPER
# ============================================================
# Permissions that match what was configured in the server:
# ON:  view_channel, send_messages, add_reactions, external_emojis,
#      external_stickers, read_message_history, connect, speak,
#      stream (video), use_external_sounds, use_voice_activation,
#      use_application_commands, use_embedded_activities, use_external_apps
# Everything else: OFF

ALERT_ROLE_PERMISSIONS = discord.Permissions(
    view_channel=True,
    send_messages=True,
    add_reactions=True,
    use_external_emojis=True,
    use_external_stickers=True,
    read_message_history=True,
    connect=True,
    speak=True,
    stream=True,
    use_external_sounds=True,
    use_voice_activation=True,
    use_application_commands=True,
    use_embedded_activities=True,
    use_external_apps=True,
)

async def get_or_create_alert_role(guild: discord.Guild, role_name: str, colour: discord.Colour):
    """
    Return (role, was_created) where was_created is True if the role
    was just made, False if it already existed.
    """
    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        role = await guild.create_role(
            name=role_name,
            permissions=ALERT_ROLE_PERMISSIONS,
            colour=colour,
            mentionable=True,
            reason="Auto-created by bot for upload/stream alerts",
        )
        print(f"Created alert role '{role_name}' in {guild.name}")
        return role, True
    return role, False


# ============================================================
#   YOUTUBE UPLOAD CHECKER
# ============================================================
# Strategy (in order):
#   1. Try RSS with channel_id (fastest, no API key)
#   2. Try RSS with username handle (fallback URL format)
#   3. Fall back to YouTube Data API v3 (uses YOUTUBE_API_KEY)
#   4. Back off to 30-min interval after 3 consecutive RSS failures

_yt_rss_fail_count = 0   # consecutive RSS failure counter
_yt_backoff_until   = 0  # timestamp — skip RSS until this time

async def get_youtube_channel_id():
    """Resolve channel ID: env var first, then page scraping."""
    channel_id = os.environ.get("YOUTUBE_CHANNEL_ID")
    if channel_id:
        return channel_id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://www.youtube.com/@{YOUTUBE_HANDLE}",
                headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"},
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                html = await resp.text()
                m = re.search(r'/channel/(UC[A-Za-z0-9_-]{22})', str(resp.url))
                if m:
                    return m.group(1)
        for pat in [r'"channelId"\s*:\s*"(UC[A-Za-z0-9_-]{22})"',
                    r'"externalId"\s*:\s*"(UC[A-Za-z0-9_-]{22})"',
                    r'channel/(UC[A-Za-z0-9_-]{22})']:
            m = re.search(pat, html)
            if m:
                return m.group(1)
    except Exception as e:
        print(f"YouTube: channel ID lookup failed: {e}")
    return None


async def _fetch_rss_url(url: str):
    """Try one RSS URL. Returns list of video dicts or None on failure."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    print(f"YouTube RSS {url[-30:]} → HTTP {resp.status}")
                    return None
                xml_text = await resp.text()
        root = ET.fromstring(xml_text)
        ns   = {"atom": "http://www.w3.org/2005/Atom",
                "yt":   "http://www.youtube.com/xml/schemas/2015"}
        videos = []
        for entry in root.findall("atom:entry", ns):
            vid = entry.find("yt:videoId", ns)
            ttl = entry.find("atom:title",  ns)
            lnk = entry.find("atom:link",   ns)
            if not vid or not ttl or not vid.text or not ttl.text:
                continue
            vid_id    = vid.text
            title     = ttl.text
            link      = lnk.attrib.get("href", f"https://www.youtube.com/watch?v={vid_id}") if lnk is not None else f"https://www.youtube.com/watch?v={vid_id}"
            thumbnail = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
            videos.append({"id": vid_id, "title": title, "link": link, "thumbnail": thumbnail})
        return videos
    except Exception as e:
        print(f"YouTube RSS fetch error: {e}")
        return None


async def _fetch_api_uploads(channel_id: str):
    """Fallback: use YouTube Data API v3 to get latest uploads."""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return None
    try:
        params = {
            "part":       "snippet",
            "channelId":  channel_id,
            "order":      "date",
            "maxResults": "10",
            "type":       "video",
            "key":        api_key,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    print(f"YouTube API fallback error: HTTP {resp.status}")
                    return None
                result = await resp.json()
        videos = []
        for item in result.get("items", []):
            vid_id = item["id"].get("videoId")
            title  = item["snippet"].get("title", "")
            if not vid_id:
                continue
            videos.append({
                "id":        vid_id,
                "title":     title,
                "link":      f"https://www.youtube.com/watch?v={vid_id}",
                "thumbnail": f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
            })
        print(f"YouTube: API fallback returned {len(videos)} entries")
        return videos
    except Exception as e:
        print(f"YouTube API fallback error: {e}")
        return None


async def get_latest_youtube_videos():
    """
    Fetch latest uploads using a three-layer strategy:
      1. RSS (channel_id URL)
      2. RSS (username URL — different endpoint, often works when #1 fails)
      3. YouTube Data API v3 (uses quota but never 404s)
    After 3 RSS failures, backs off to 30-min interval automatically.
    """
    global _yt_rss_fail_count, _yt_backoff_until

    channel_id = await get_youtube_channel_id()
    if not channel_id:
        print("YouTube: could not resolve channel ID")
        return []

    now = time.time()
    rss_blocked = now < _yt_backoff_until

    # ── Layer 1: RSS by channel_id ───────────────────────────
    if not rss_blocked:
        videos = await _fetch_rss_url(
            f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        )
        if videos is not None:
            _yt_rss_fail_count = 0
            print(f"YouTube: RSS (channel_id) returned {len(videos)} entries")
            return videos

    # ── Layer 2: RSS by username handle ─────────────────────
    if not rss_blocked:
        videos = await _fetch_rss_url(
            f"https://www.youtube.com/feeds/videos.xml?user={YOUTUBE_HANDLE}"
        )
        if videos is not None:
            _yt_rss_fail_count = 0
            print(f"YouTube: RSS (user handle) returned {len(videos)} entries")
            return videos

    # Both RSS methods failed — increment failure count
    if not rss_blocked:
        _yt_rss_fail_count += 1
        print(f"YouTube: RSS failed ({_yt_rss_fail_count} consecutive)")
        if _yt_rss_fail_count >= 3:
            _yt_backoff_until = now + 1800  # back off 30 minutes
            print("YouTube: backing off RSS for 30 minutes, switching to API fallback")
            await dm_owner(
                "YouTube RSS unavailable — switched to API fallback",
                f"The YouTube RSS feed has failed **{_yt_rss_fail_count}** times in a row.\n\n"
                f"The bot has automatically switched to using the YouTube Data API for the next 30 minutes.\n"
                f"This uses ~100 API quota units per check. Your daily limit is 10,000 units.\n\n"
                f"RSS will be retried automatically after the backoff period."
            )

    # ── Layer 3: YouTube Data API fallback ──────────────────
    videos = await _fetch_api_uploads(channel_id)
    if videos is not None:
        return videos

    # All three methods failed
    if rss_blocked:
        print("YouTube: API fallback also failed during backoff period")
    else:
        await dm_owner(
            "YouTube upload checker completely failed",
            "Both the RSS feed and the Data API fallback returned no data.\n\n"
            "**Check:**\n"
            "• Is `YOUTUBE_API_KEY` set on Railway?\n"
            "• Has the YouTube Data API quota been exceeded for today?"
        )
    return []

@tasks.loop(minutes=10)
async def youtube_check_loop():
    data = load_data()
    data = ensure_keys(data)
    videos = await get_latest_youtube_videos()
    if not videos:
        return
    last_id = data.get("last_youtube_id")
    if last_id is None:
        data["last_youtube_id"] = videos[0]["id"]
        save_data(data)
        print(f"YouTube: seeded last_id = {videos[0]['id']}")
        return

    new_videos = []
    for v in videos:
        if v["id"] == last_id:
            break
        new_videos.append(v)

    if not new_videos:
        return

    data["last_youtube_id"] = videos[0]["id"]
    save_data(data)
    print(f"YouTube: {len(new_videos)} new video(s) to announce")

    for video in reversed(new_videos):
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
                alert_role, _ = await get_or_create_alert_role(
                    guild, "Upload Alerts", discord.Colour.red()
                )
                await channel.send(f"{alert_role.mention} {video['title']} | {video['link']}", embed=embed)

@youtube_check_loop.before_loop
async def before_youtube():
    await bot.wait_until_ready()

# ============================================================
#   TIKTOK UPLOAD CHECKER
# ============================================================
# TikTok has no public API, so we scrape the profile page
# and look for the latest video ID in the page source.

async def get_latest_tiktok_videos():
    """
    Fetch the latest TikTok videos for the configured account.
    TikTok embeds all page data in a <script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">
    JSON blob. We extract video IDs from there, falling back to regex on raw HTML.
    Returns a list of dicts (newest-first): [{"id": ..., "link": ...}, ...]
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://www.tiktok.com/@{TIKTOK_USERNAME}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                print(f"TikTok: profile page HTTP {resp.status}")
                if resp.status != 200:
                    return []
                html = await resp.text()

        # ── Method 1: extract from the embedded JSON data blob ──────────────
        # TikTok inlines all page data as:
        #   <script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">...</script>
        video_ids = []
        script_match = re.search(
            r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        if script_match:
            try:
                page_data = json.loads(script_match.group(1))
                # Walk the nested structure to find video item lists
                raw_str = json.dumps(page_data)
                video_ids = re.findall(r'"id"\s*:\s*"(\d{17,19})"', raw_str)
            except Exception as parse_err:
                print(f"TikTok: JSON blob parse error: {parse_err}")

        # ── Method 2: SIGI_STATE blob (older TikTok page format) ────────────
        if not video_ids:
            sigi_match = re.search(r'<script[^>]+id="SIGI_STATE"[^>]*>(.*?)</script>', html, re.DOTALL)
            if sigi_match:
                try:
                    raw_str = sigi_match.group(1)
                    video_ids = re.findall(r'"id"\s*:\s*"(\d{17,19})"', raw_str)
                except Exception:
                    pass

        # ── Method 3: raw HTML regex fallback ───────────────────────────────
        if not video_ids:
            patterns = [
                r'video/(\d{17,19})',
                r'"videoId"\s*:\s*"(\d{17,19})"',
                r'"id"\s*:\s*"(\d{17,19})"',
            ]
            for pattern in patterns:
                video_ids = re.findall(pattern, html)
                if video_ids:
                    break

        if not video_ids:
            print(
                f"TikTok: no video IDs found in page (page length: {len(html)}). "
                "TikTok may be serving a bot-detection challenge."
            )
            await dm_owner(
                "TikTok upload check failed",
                f"The bot could not find any video IDs on your TikTok profile page.\n\n"
                f"**Profile checked:** `https://www.tiktok.com/@{TIKTOK_USERNAME}`\n"
                f"**Page size returned:** {len(html)} characters\n\n"
                f"**Most likely cause:** TikTok is serving a bot-detection challenge to the server's IP address. "
                f"This happens intermittently and usually resolves itself within a few hours.\n\n"
                f"If this keeps happening every check, TikTok upload announcements may not be reliable "
                f"until TikTok releases a public API."
            )
            return []

        # Deduplicate while preserving order
        seen = set()
        unique_ids = []
        for vid_id in video_ids:
            if vid_id not in seen:
                seen.add(vid_id)
                unique_ids.append(vid_id)

        print(f"TikTok: found {len(unique_ids)} video ID(s), latest = {unique_ids[0]}")
        return [
            {"id": vid_id, "link": f"https://www.tiktok.com/@{TIKTOK_USERNAME}/video/{vid_id}"}
            for vid_id in unique_ids
        ]  # newest-first (TikTok page order)

    except Exception as e:
        print(f"TikTok fetch error: {e}")
        return []

@tasks.loop(minutes=15)
async def tiktok_check_loop():
    data = load_data()
    data = ensure_keys(data)
    videos = await get_latest_tiktok_videos()
    if not videos:
        return
    last_id = data.get("last_tiktok_id")
    if last_id is None:
        # First run — seed with current newest so we don't spam old videos
        data["last_tiktok_id"] = videos[0]["id"]
        save_data(data)
        print(f"TikTok: seeded last_id = {videos[0]['id']}")
        return

    # Collect every video that came out AFTER the last announced one
    new_videos = []
    for v in videos:
        if v["id"] == last_id:
            break
        new_videos.append(v)

    if not new_videos:
        return  # Nothing new

    # Save newest ID before announcing
    data["last_tiktok_id"] = videos[0]["id"]
    save_data(data)
    print(f"TikTok: {len(new_videos)} new video(s) to announce")

    # Announce oldest-first
    for video in reversed(new_videos):
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
                alert_role, _ = await get_or_create_alert_role(
                    guild, "Upload Alerts", discord.Colour.red()
                )
                await channel.send(alert_role.mention, embed=embed)

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
                            # Mark as announced ONLY after successfully sending
                            data["birthday_announced"][announced_key] = True
                            save_data(data)

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
        # All words used — DM the bot owner and stop until words are added
        for guild in bot.guilds:
            if guild.owner:
                try:
                    await guild.owner.send(
                        "All Word of the Day words have been used up! "
                        "Please add more words to WORD_OF_THE_DAY_LIST in the bot code "
                        "and remove the old entries from \"wotd_used\" in data.json."
                    )
                except discord.Forbidden:
                    pass
        return  # Stop — do not repeat words
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

            # Restore stripped roles
            action_key = f"timeout_{guild_id_str}_{member_id_str}"
            await restore_roles_after_punishment(guild, member, data, action_key)

            # Close the timeout case channel
            if member:
                mention = member.mention
                # Find the channel robustly (same logic as close_case_channel)
                member_id_str_inner = str(member.id)
                category = discord.utils.get(guild.categories, name=CASE_CATEGORY)
                search_space = category.text_channels if category else guild.text_channels
                safe_name = "".join(c if c.isalnum() or c == "-" else "-" for c in member.display_name.lower())
                chan = discord.utils.get(search_space, name=f"timeout-{safe_name}"[:100])
                if not chan and category:
                    for ch in category.text_channels:
                        if ch.name.startswith("timeout-") and ch.topic and member_id_str_inner in ch.topic:
                            chan = ch
                            break
                if chan:
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
                    try:
                        await chan.send(embed=embed)
                        await asyncio.sleep(5)
                        await chan.delete(reason="Timeout expired")
                    except Exception as e:
                        print(f"Could not close timeout channel: {e}")

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
        except asyncio.TimeoutError:
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
        except asyncio.TimeoutError:
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
        except asyncio.TimeoutError:
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
    for tb_key, info in list(expired.items()):
        try:
            # Key is now "guild_id_user_id" — extract user_id from end
            user_id_str = tb_key.split("_", 1)[-1] if "_" in tb_key else tb_key
            guild = bot.get_guild(int(info["guild_id"]))
            if not guild:
                # Guild gone — clean up stale entry instead of leaving it forever
                del data["tempbans"][tb_key]
                changed = True
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
            del data["tempbans"][tb_key]
            changed = True
        except Exception as e:
            print(f"Tempban unban error for {user_id_str}: {e}")
    if changed:
        save_data(data)

@tempban_expire_loop.before_loop
async def before_tempban_expire():
    await bot.wait_until_ready()


# ============================================================
#   AUTO-MODERATION ENGINE
# ============================================================
#
# PUNISHMENT TIERS (auto-applied via existing warning system):
#   1st auto-warn  → message deleted, DM sent, logged
#   2nd auto-warn  → message deleted + 1hr timeout (existing escalation)
#   3rd auto-warn  → message deleted + 5hr timeout
#   INSTANT BAN    → threats, doxxing, illegal activity
#
# To add your own words, add them to CUSTOM_FILTER_WORDS below.
# You do NOT need to add bypass variants — the normaliser handles them.
# ============================================================

# ── Your custom word list ────────────────────────────────────
# Add any words here that aren't already caught by the built-in filters.
CUSTOM_FILTER_WORDS = [
    # Add your own words here, one per line, lowercase:
    # "example",
]

# ── Built-in slur list ───────────────────────────────────────
# Racial, homophobic, transphobic, sexist, ableist slurs.
# Common bypass spellings are caught by the normaliser below.
_SLUR_LIST = [
    # --- Racial ---
    "nigger", "nigga", "nigg", "niga", "negro",
    "chink", "gook", "spic", "spick", "wetback",
    "kike", "hymie", "heeb",
    "raghead", "towelhead", "sandnigger", "camel jockey",
    "zipperhead", "slant", "slope",
    "paki", "coolie",
    "coon", "jigaboo", "porch monkey", "jungle bunny",
    "beaner",
    "gringo",  # included only in hostile-context detection
    # --- Homophobic ---
    "faggot", "fag", "dyke", "queer",  # caught only in slur context
    "homo",
    # --- Transphobic ---
    "tranny", "shemale", "heshe",
    # --- Sexist ---
    "cunt", "whore", "slut", "skank",
    # --- Ableist ---
    "retard", "retarded", "spaz", "spastic",
]

# Combine with custom list
ALL_FILTER_WORDS = list(set(_SLUR_LIST + [w.lower().strip() for w in CUSTOM_FILTER_WORDS if w.strip()]))

# ── Threat / illegal activity keywords ──────────────────────
# Messages containing these in a threatening context → instant ban
_THREAT_PATTERNS = [
    r"\bi\s*will\s*(dox|ddos|swat|hack|grab\s*your\s*ip)\b",
    r"\b(gonna|going\s*to|about\s*to)\s*(dox|ddos|swat|hack)\b",
    r"\bdox(x)?\s*(you|u|him|her|them)\b",
    r"\bswatt?ing\b",
    r"\bddos(ing)?\b",
    r"\bip\s*grab(bing|ber)?\b",
    r"\bi\s*know\s*where\s*you\s*live\b",
    r"\bkill\s*your?self\b",
    r"\bkys\b",
    r"\bgo\s*kill\s*(your)?s(elf|elf)\b",
]

# ── Advertising / invite patterns ───────────────────────────
_INVITE_PATTERN = re.compile(
    r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/[a-zA-Z0-9]+",
    re.IGNORECASE
)
_SCAM_DOMAINS = [
    "free-nitro", "discordnitro", "steamgift", "csgo-skins",
    "freegift", "nitrogift", "discord-gift", "steamtrade",
]

# ── Spam detection ───────────────────────────────────────────
_spam_tracker = {}   # guild_id -> user_id -> [timestamps]
_repeat_tracker = {} # guild_id -> user_id -> [(content, timestamp)]
SPAM_MSG_LIMIT  = 5   # messages within...
SPAM_WINDOW     = 6   # ...6 seconds = spam
REPEAT_LIMIT    = 3   # same message 3 times within...
REPEAT_WINDOW   = 30  # ...30 seconds = spam


def _normalise(text: str) -> str:
    """
    Normalise text to catch common bypass attempts:
    - Strips zero-width characters
    - Collapses repeated characters (nigggg -> nigg)
    - Removes spaces/dots/underscores between letters (n.i.g.g.e.r -> nigger)
    - Maps common leetspeak substitutions
    - Lowercases everything
    """
    import unicodedata
    # Remove zero-width and invisible characters
    text = "".join(c for c in text if unicodedata.category(c) not in ("Cf", "Mn"))
    text = text.lower()
    # Remove spaces/separators between letters (n i g g e r -> nigger)
    text = re.sub(r"(?<=[a-z0-9])[ ._\-]+(?=[a-z0-9])", "", text)
    # Collapse 3+ repeated characters (niiigger -> niiger -> evaluated)
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)
    # Leetspeak map
    leet = {"@": "a", "4": "a", "3": "e", "1": "i", "!": "i",
            "0": "o", "5": "s", "$": "s", "7": "t", "+": "t"}
    text = "".join(leet.get(c, c) for c in text)
    return text


def _contains_slur(text: str):
    """
    Returns (True, matched_word) if the normalised text contains a slur,
    (False, None) otherwise.
    """
    norm = _normalise(text)
    for word in ALL_FILTER_WORDS:
        # Use word-boundary matching where possible
        pattern = r"\b" + re.escape(word) + r"\b"
        if re.search(pattern, norm):
            return True, word
        # Also check without word boundaries for short words that embed in others
        if len(word) <= 4 and word in norm:
            return True, word
    return False, None


def _contains_threat(text: str) -> bool:
    """Returns True if the message contains a credible threat or illegal activity."""
    norm = _normalise(text)
    for pattern in _THREAT_PATTERNS:
        if re.search(pattern, norm):
            return True
    return False


def _contains_invite(text: str) -> bool:
    """Returns True if the message contains an unsolicited Discord invite link."""
    return bool(_INVITE_PATTERN.search(text))


def _contains_scam(text: str) -> bool:
    """Returns True if the message contains known scam domain patterns."""
    text_lower = text.lower()
    return any(domain in text_lower for domain in _SCAM_DOMAINS)


def _is_spam(guild_id: str, user_id: str) -> bool:
    """Returns True if this user is sending too many messages too fast."""
    now = time.time()
    key = f"{guild_id}_{user_id}"
    _spam_tracker.setdefault(key, [])
    _spam_tracker[key] = [t for t in _spam_tracker[key] if now - t <= SPAM_WINDOW]
    _spam_tracker[key].append(now)
    return len(_spam_tracker[key]) >= SPAM_MSG_LIMIT


def _is_repeat_spam(guild_id: str, user_id: str, content: str) -> bool:
    """Returns True if this user is sending the same message repeatedly."""
    now = time.time()
    key = f"{guild_id}_{user_id}"
    _repeat_tracker.setdefault(key, [])
    _repeat_tracker[key] = [(c, t) for c, t in _repeat_tracker[key] if now - t <= REPEAT_WINDOW]
    _repeat_tracker[key].append((content.lower().strip(), now))
    same = sum(1 for c, _ in _repeat_tracker[key] if c == content.lower().strip())
    return same >= REPEAT_LIMIT


def _has_mass_mentions(message: discord.Message) -> bool:
    """Returns True if the message pings 5 or more users/roles."""
    return len(message.mentions) + len(message.role_mentions) >= 5


async def _automod_warn(message: discord.Message, reason: str, rule: str, delete: bool = True):
    """
    Core automod action:
    1. Delete the message (if delete=True)
    2. Add a warning using the existing warning system
    3. DM the user
    4. Log to mod-logs
    5. Notify the owner via DM
    """
    member   = message.author
    guild    = message.guild
    guild_id = str(guild.id)
    user_id  = str(member.id)

    # Mods are exempt from automod
    if is_mod(member):
        return

    # Delete the message first
    if delete:
        try:
            await message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass

    # Add warning to the existing system
    data = load_data()
    data = ensure_keys(data)
    data["warnings"].setdefault(guild_id, {}).setdefault(user_id, [])
    warning_entry = {
        "reason":     f"[AutoMod] {reason}",
        "moderator":  "AutoMod",
        "timestamp":  datetime.now().strftime("%d/%m/%Y %H:%M"),
        "rule":       rule,
    }
    data["warnings"][guild_id][user_id].append(warning_entry)
    total = len(data["warnings"][guild_id][user_id])
    save_data(data)

    # DM the user
    try:
        embed_dm = discord.Embed(
            title="Your message was removed",
            description=(
                f"Your message in **{guild.name}** was removed by AutoMod.\n\n"
                f"**Rule violated:** {rule}\n"
                f"**Reason:** {reason}\n\n"
                f"You now have **{total}** warning(s). Repeated violations will result in timeouts or bans."
            ),
            color=discord.Color.orange()
        )
        await member.send(embed=embed_dm)
    except discord.Forbidden:
        pass  # DMs off — log only

    # Log to mod-logs
    await log_action(guild, "AutoMod Warning", member, guild.me,
                     f"[{rule}] {reason}", f"Total warnings: {total}")

    # Notify owner
    await dm_owner(
        f"AutoMod actioned {member}",
        f"**User:** {member.mention} (`{member.id}`)\n"
        f"**Rule:** {rule}\n"
        f"**Reason:** {reason}\n"
        f"**Channel:** #{message.channel.name}\n"
        f"**Total warnings:** {total}\n"
        f"**Message content:** {message.content[:300]}"
    )

    # Apply escalation based on warning count
    if total == 2:
        try:
            await member.timeout(timedelta(hours=1), reason=f"AutoMod: {reason}")
            await message.channel.send(
                f"{member.mention} has been timed out for **1 hour** for repeated rule violations.",
                delete_after=10
            )
        except discord.Forbidden:
            pass
    elif total == 3:
        try:
            await member.timeout(timedelta(hours=5), reason=f"AutoMod: {reason}")
            await message.channel.send(
                f"{member.mention} has been timed out for **5 hours** for repeated rule violations.",
                delete_after=10
            )
        except discord.Forbidden:
            pass
    elif total == 4:
        try:
            await member.timeout(timedelta(hours=24), reason=f"AutoMod: {reason}")
            await message.channel.send(
                f"{member.mention} has been timed out for **24 hours** for repeated rule violations.",
                delete_after=10
            )
        except discord.Forbidden:
            pass
    elif total >= 5:
        try:
            await guild.ban(member, reason=f"AutoMod: {total} violations — {reason}", delete_message_days=1)
            await message.channel.send(
                f"{member.mention} has been **banned** for reaching {total} violations.",
                delete_after=10
            )
        except discord.Forbidden:
            pass


async def _automod_ban(message: discord.Message, reason: str):
    """Instant ban for serious violations (threats, illegal activity)."""
    member = message.author
    guild  = message.guild

    if is_mod(member):
        return

    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden):
        pass

    try:
        await member.send(
            f"You have been **permanently banned** from **{guild.name}**.\n"
            f"Reason: {reason}"
        )
    except discord.Forbidden:
        pass

    try:
        await guild.ban(member, reason=f"AutoMod (Instant Ban): {reason}", delete_message_days=1)
    except discord.Forbidden:
        pass

    await log_action(guild, "AutoMod Instant Ban", member, guild.me, reason)
    await dm_owner(
        f"AutoMod INSTANT BAN: {member}",
        f"**User:** {member.mention} (`{member.id}`)\n"
        f"**Reason:** {reason}\n"
        f"**Channel:** #{message.channel.name}\n"
        f"**Message:** {message.content[:300]}"
    )


async def run_automod(message: discord.Message) -> bool:
    """
    Run all automod checks on a message.
    Returns True if the message was actioned (so caller can skip XP etc).
    """
    # Never moderate bots or mods
    if message.author.bot or is_mod(message.author):
        return False

    content  = message.content
    guild_id = str(message.guild.id)
    user_id  = str(message.author.id)

    # ── Check 1: Threats / illegal activity → INSTANT BAN ───────
    if _contains_threat(content):
        await _automod_ban(
            message,
            "Threats or illegal activity (doxxing/DDoS/swatting/IP grabbing)"
        )
        return True

    # ── Check 2: Slurs ───────────────────────────────────────────
    found, matched_word = _contains_slur(content)
    if found:
        await _automod_warn(
            message,
            f"Slur detected",
            "No slurs / No hate speech",
        )
        return True

    # ── Check 3: NSFW / scam links ───────────────────────────────
    if _contains_scam(content):
        await _automod_warn(
            message,
            "Known scam domain or suspicious link",
            "No scams or unauthorized advertising",
        )
        return True

    # ── Check 4: Unsolicited Discord invites ─────────────────────
    if _contains_invite(content):
        # Only flag if it looks like advertising (not someone sharing their own server
        # in a context where they were asked). We delete + warn.
        await _automod_warn(
            message,
            "Unsolicited Discord server invite link",
            "No scams or unauthorized advertising",
        )
        return True

    # ── Check 5: Mass mentions ───────────────────────────────────
    if _has_mass_mentions(message):
        await _automod_warn(
            message,
            f"Mass mention ({len(message.mentions) + len(message.role_mentions)} pings)",
            "No spam or mass mentions",
        )
        return True

    # ── Check 6: Message spam ────────────────────────────────────
    if _is_spam(guild_id, user_id):
        await _automod_warn(
            message,
            f"Sending messages too fast",
            "No spam",
        )
        return True

    # ── Check 7: Repeat spam ─────────────────────────────────────
    if _is_repeat_spam(guild_id, user_id, content):
        await _automod_warn(
            message,
            "Sending the same message repeatedly",
            "No spam",
        )
        return True

    return False


@bot.command(name="automod")
async def automod_status_cmd(ctx):
    """Show current automod configuration and status."""
    # Inline mod check — mod_only() decorator can't be used here because
    # this command is defined before mod_only() in the file.
    config    = get_config()
    mod_roles = config.get("mod_roles", [])
    perms     = ctx.author.guild_permissions
    is_a_mod  = (
        any(r.name in mod_roles for r in ctx.author.roles)
        or perms.administrator or perms.manage_messages
        or perms.kick_members  or perms.ban_members
        or perms.moderate_members
    )
    if not is_a_mod:
        await ctx.send("You don't have permission to use this command.", delete_after=5)
        return
    await log_command(ctx.guild, ctx.author, "automod")
    embed = discord.Embed(title="AutoMod Status", color=discord.Color.blurple())
    embed.add_field(
        name="Active Checks",
        value=(
            "✅ Slurs & hate speech\n"
            "✅ Threats & illegal activity (instant ban)\n"
            "✅ Scam links\n"
            "✅ Unsolicited Discord invites\n"
            "✅ Mass mentions (5+)\n"
            "✅ Message spam (5 msgs / 6s)\n"
            "✅ Repeat spam (same msg 3× / 30s)"
        ),
        inline=False
    )
    embed.add_field(
        name="Escalation Thresholds",
        value=(
            "1 violation → Warning + message deleted\n"
            "2 violations → 1 hour timeout\n"
            "3 violations → 5 hour timeout\n"
            "4 violations → 24 hour timeout\n"
            "5+ violations → Ban\n"
            "Threats/illegal → Instant ban"
        ),
        inline=False
    )
    embed.add_field(
        name="Custom Words",
        value=f"{len(CUSTOM_FILTER_WORDS)} custom filter word(s) active" if CUSTOM_FILTER_WORDS else "No custom words added yet",
        inline=False
    )
    embed.add_field(
        name="Exempt",
        value="Mods, Managers, and Ahmed are never actioned by AutoMod",
        inline=False
    )
    await ctx.send(embed=embed)

# ============================================================
#   EVENTS
# ============================================================

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    # Notify owner on startup
    asyncio.create_task(dm_owner(
        "Bot is online",
        f"**Vexon's Bot** has started up successfully.\n"
        f"Logged in as: `{bot.user}`\n"
        f"Guilds: {len(bot.guilds)}",
        cooldown=False  # always notify on restart
    ))
    validate_config()
    # Reset twitch_live on startup — avoids getting stuck if bot restarted
    # mid-stream or after a crash. The first check will re-announce if live.
    data = load_data()
    data = ensure_keys(data)
    data["twitch_live"] = False
    data["kick_live"] = False
    data["youtube_live"] = False
    save_data(data)
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
    # YouTube upload check is manual-only — use ?ytcheck command
    # if not youtube_check_loop.is_running():
    #     youtube_check_loop.start()
    if not tiktok_check_loop.is_running():
        tiktok_check_loop.start()
    if not kick_check_loop.is_running():
        kick_check_loop.start()
    if not youtube_live_check_loop.is_running():
        youtube_live_check_loop.start()
    if not lock_expire_loop.is_running():
        lock_expire_loop.start()
    if not weekly_reset_loop.is_running():
        weekly_reset_loop.start()

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
            get_roles_ch = discord.utils.get(member.guild.text_channels, name=get_config().get("get_roles_channel", "get-roles"))
            roles_mention = get_roles_ch.mention if get_roles_ch else "#get-roles"
            await channel.send(
                f"Welcome {member.mention} to Vexon's Community! "
                f"Please read the rules and get your roles in {roles_mention}. "
                f"Enjoy your stay!"
            )

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    # ── AutoMod — runs before anything else ──────────────────────
    if await run_automod(message):
        return  # Message was actioned — skip XP, trivia, etc.

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
            level_channel = discord.utils.get(message.guild.text_channels, name=get_config().get("level_up_channel", "levelling-announcements"))
            if level_channel:
                await level_channel.send(f"{message.author.mention} has reached level **{new_level}**!")
            if new_level in LEVEL_ROLES:
                role_name = LEVEL_ROLES[new_level]
                role = discord.utils.get(message.guild.roles, name=role_name)
                if role and role not in message.author.roles:
                    await message.author.add_roles(role)

    # Track per-channel unique-user activity for auto-trivia and auto fun quiz
    if not message.author.bot:
        ch_id = str(message.channel.id)

        # --- auto trivia ---
        if guild_id not in message_activity:
            message_activity[guild_id] = {}
        if ch_id not in message_activity[guild_id]:
            message_activity[guild_id][ch_id] = {}
        message_activity[guild_id][ch_id][user_id] = now  # store latest timestamp per user
        # Count unique users who sent a message within the window
        active_users_trivia = [
            uid for uid, ts in message_activity[guild_id][ch_id].items()
            if now - ts <= AUTO_TRIVIA_WINDOW
        ]
        if (len(active_users_trivia) >= AUTO_TRIVIA_THRESHOLD
                and guild_id not in active_trivia):
            message_activity[guild_id][ch_id] = {}  # reset this channel's window
            asyncio.create_task(auto_trivia(message.guild, message.channel))

        # --- auto fun quiz ---
        if guild_id not in fun_quiz_activity:
            fun_quiz_activity[guild_id] = {}
        if ch_id not in fun_quiz_activity[guild_id]:
            fun_quiz_activity[guild_id][ch_id] = {}
        fun_quiz_activity[guild_id][ch_id][user_id] = now
        active_users_quiz = [
            uid for uid, ts in fun_quiz_activity[guild_id][ch_id].items()
            if now - ts <= AUTO_FUN_QUIZ_WINDOW
        ]
        if (len(active_users_quiz) >= AUTO_FUN_QUIZ_THRESHOLD
                and guild_id not in active_fun_quiz
                and guild_id not in active_trivia):
            fun_quiz_activity[guild_id][ch_id] = {}
            asyncio.create_task(auto_fun_quiz(message.guild, message.channel))

    if guild_id in active_trivia:
        trivia = active_trivia[guild_id]
        if message.channel.id == trivia["channel_id"] and not message.author.bot:
            if fuzzy_match(message.content, trivia["answer"]):
                del active_trivia[guild_id]
                data = load_data()
                data = ensure_keys(data)
                # Ensure nested guild/user dicts exist before direct write
                data["xp"].setdefault(guild_id, {})[user_id] = data["xp"].get(guild_id, {}).get(user_id, 0) + TRIVIA_XP_REWARD
                old_xp = data["xp"][guild_id][user_id] - TRIVIA_XP_REWARD
                data["points"].setdefault(guild_id, {})[user_id] = data["points"].get(guild_id, {}).get(user_id, 0) + TRIVIA_POINTS_REWARD
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

    # ── Counting channel handler ──────────────────────────────
    if message.channel.name == COUNTING_CHANNEL:
        data_c = load_data()
        data_c = ensure_keys(data_c)
        gid_c  = str(message.guild.id)
        counting = get_counting(data_c, gid_c)
        current  = counting["current"]
        expected = current + 1
        uid_c    = str(message.author.id)

        try:
            num = int(message.content.strip())
        except ValueError:
            try:
                await message.delete()
            except Exception:
                pass
            await message.channel.send(
                f"{message.author.mention} Only numbers allowed here! The count is still **{current}**.",
                delete_after=5
            )
            await bot.process_commands(message)
            return

        if counting["last_user"] == uid_c:
            try:
                await message.delete()
            except Exception:
                pass
            await message.channel.send(
                f"{message.author.mention} You can't count two in a row! The count is still **{current}**.",
                delete_after=5
            )
            await bot.process_commands(message)
            return

        if num == expected:
            counting["current"] = expected
            counting["last_user"] = uid_c
            counting["scores"][uid_c] = counting["scores"].get(uid_c, 0) + 1
            if expected > counting.get("high_score", 0):
                counting["high_score"] = expected
            save_data(data_c)
            await message.add_reaction("✅")
        else:
            old_count = current
            counting["current"] = 0
            counting["last_user"] = None
            save_data(data_c)
            try:
                await message.delete()
            except Exception:
                pass
            await message.channel.send(
                f"❌ {message.author.mention} ruined the count at **{old_count}**! "
                f"Expected **{expected}** but got **{num}**. Starting over from **1**!"
            )

    # Mystery box tracker — 5 unique users in ≤5s spawns a box
    if not message.author.bot:
        asyncio.create_task(_maybe_spawn_mystery_box(message.channel, guild_id, user_id))

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
        print(f"[ReactionAdd] msg={payload.message_id} emoji={repr(emoji)} matched={role_name}")
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            member = guild.get_member(payload.user_id)
            if not role:
                print(f"[ReactionAdd] role '{role_name}' not found in guild")
            elif not member:
                print(f"[ReactionAdd] member {payload.user_id} not found in guild")
            else:
                await member.add_roles(role)
                print(f"[ReactionAdd] gave {member} the role {role_name}")

    # Continent roles
    continent_msg_id = rr.get("continent_message_id")
    if continent_msg_id and str(payload.message_id) == str(continent_msg_id):
        role_name = CONTINENT_ROLES.get(emoji)
        print(f"[ReactionAdd-Continent] msg={payload.message_id} emoji={repr(emoji)} matched={role_name}")
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.add_roles(role)
                print(f"[ReactionAdd-Continent] gave {member} the role {role_name}")

    # Alert roles
    alert_msg_id = rr.get("alert_message_id")
    if alert_msg_id and str(payload.message_id) == str(alert_msg_id):
        role_name = ALERT_ROLES.get(emoji)
        print(f"[ReactionAdd-Alert] msg={payload.message_id} emoji={repr(emoji)} matched={role_name}")
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.add_roles(role)
                print(f"[ReactionAdd-Alert] gave {member} the role {role_name}")

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

    # Alert roles
    alert_msg_id = rr.get("alert_message_id")
    if alert_msg_id and str(payload.message_id) == str(alert_msg_id):
        role_name = ALERT_ROLES.get(emoji)
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.remove_roles(role)

# ============================================================
#   EXTERNAL MUTE DETECTION (censor bot / other bots)
# ============================================================

@bot.event
async def on_member_update(before, after):
    """
    Fires whenever a member's roles change.
    If the 'Muted' role was added by an external bot (not by this bot),
    create a case channel automatically.
    If it was removed externally, close the case channel.
    """
    mute_role = discord.utils.get(after.guild.roles, name="Muted")
    if not mute_role:
        return

    muted_now    = mute_role in after.roles
    was_muted    = mute_role in before.roles

    if muted_now == was_muted:
        return  # no change to the Muted role

    guild = after.guild

    # Try to find who made the change via audit log
    moderator = guild.me  # default to bot if we can't find the actor
    reason    = "Muted by external moderation"
    try:
        await asyncio.sleep(0.5)  # brief wait so the audit log entry exists
        action = discord.AuditLogAction.member_role_update
        async for entry in guild.audit_logs(limit=5, action=action):
            if entry.target.id == after.id:
                moderator = entry.user
                reason    = entry.reason or reason
                break
    except discord.Forbidden:
        pass  # no audit log permission — fall back to defaults

    if muted_now and not was_muted:
        # Role was just added — only act if it wasn't added by this bot
        if moderator.id == guild.me.id:
            return  # our own ?mute command already handles this

        # Check a case channel doesn't already exist
        data = load_data()
        data = ensure_keys(data)
        action_key = f"muted_{guild.id}_{after.id}"

        # Strip roles and store them for later restoration
        await strip_roles_for_punishment(
            guild, after, data, str(guild.id), str(after.id), action_key
        )
        save_data(data)

        await create_case_channel(
            guild, after, "Muted", reason, moderator, channel_prefix="muted"
        )
        await log_action(guild, "Mute (external)", after, moderator, reason)
        print(f"[ExternalMute] Case channel created for {after} — muted by {moderator}")

    elif was_muted and not muted_now:
        # Role was just removed — only act if it wasn't removed by this bot
        if moderator.id == guild.me.id:
            return  # our own ?unmute command already handles this

        # Restore roles and close channel
        data = load_data()
        data = ensure_keys(data)
        action_key = f"muted_{guild.id}_{after.id}"
        await restore_roles_after_punishment(guild, after, data, action_key)
        save_data(data)

        await close_case_channel(guild, after, channel_prefix="muted")
        await log_action(guild, "Unmute (external)", after, moderator, reason)
        print(f"[ExternalUnmute] Case channel closed for {after} — unmuted by {moderator}")

# ============================================================
#   USER COMMANDS
# ============================================================

@bot.command(name="help")
async def help_command(ctx):
    await log_command(ctx.guild, ctx.author, "help")
    senior_roles   = ["Managers", "Ahmed"]
    user_is_mod    = is_mod(ctx.author)
    user_is_senior = (
        any(r.name in senior_roles for r in ctx.author.roles)
        or ctx.author.guild_permissions.administrator
    )
    await ctx.send(
        embed=_help_home_embed(user_is_mod, user_is_senior),
        view=HelpView(ctx.author.id, user_is_mod, user_is_senior)
    )


# ── Help data ────────────────────────────────────────────────
# Each category is (button_label, emoji, embed_content)
# Regular user categories
_HELP_CATEGORIES = {
    "Levels & XP": (
        "📊", discord.Color.blue(),
        "`?level` — Your level, XP, and progress\n"
        "`?level @user` — Check another user's level\n"
        "`?leaderboard [xp|points|streak|trivia|steals|rps]` — Leaderboards (alias: `?lb`)\n"
        "`?profile` — Your full profile: economy, roles, stats\n"
        "`?profile @user` — View another user's profile\n"
        "`?achieve` — Your unlocked achievements (aliases: `?achievements`, `?badges`)"
    ),
    "Economy": (
        "💰", discord.Color.green(),
        "`?daily` — Claim daily reward (24h cooldown, streak bonus)\n"
        "`?gamble [amount]` — Gamble your points\n"
        "`?steal @user` — Steal points (5h cooldown)\n"
        "`?rob @user` — High-risk robbery (bigger reward, bigger penalty)\n"
        "`?pay @user [amount]` — Transfer points to someone\n"
        "`?beg` — Beg for points (60s cooldown)\n"
        "`?crime` — Attempt a crime for a reward or penalty\n"
        "`?spin` — Daily free spin wheel (once per day)\n"
        "`?highlow [amount]` — Guess higher or lower (alias: `?hl`)\n"
        "`?stocks` — View the stock market\n"
        "`?buystock [TICKER] [shares]` — Buy shares\n"
        "`?sellstock [TICKER] [shares]` — Sell shares\n"
        "`?baltop` — Points-only leaderboard\n"
        "`?weekly` — Weekly XP leaderboard (resets Monday)\n"
        "`?rank` — Your exact XP rank position\n"
        "`?streak` — Your daily streak and next bonus tier\n"
        "`?cooldowns` — See all your active cooldowns (alias: `?cd`)\n\n"
        "**📅 Daily Streak Tiers**\n"
        "3+ days → **1.5×** | 7+ → **2.0×** | 14+ → **2.5×** | 30+ → **3.0×**"
    ),
    "Shop": (
        "🛒", discord.Color.orange(),
        "`?shop` — Browse the shop by category\n"
        "`?buy [item_id]` — Purchase an item\n"
        "`?inventory` — View your inventory (alias: `?inv`)\n\n"
        "**💼 Jobs**\n"
        "`?jobs` — Browse available jobs\n"
        "`?choosejob [job]` — Pick your job\n"
        "`?work` — Do a shift mini-game (1h cooldown)"
    ),
    "Activities": (
        "🌿", discord.Color.teal(),
        "`?hunt` — Go hunting (may find crafting materials!)\n"
        "`?fish` — Go fishing (may find crafting materials!)\n"
        "`?fishbucket` — View your fish bucket (alias: `?bucket`)\n"
        "`?fishsell` — Sell all fish in your bucket\n"
        "`?scratch` — Scratch a card to win up to 5× cost\n"
        "`?adventure` — Embark on a random adventure\n"
        "`?materials` — View your crafting materials (alias: `?mats`)\n"
        "`?craft` — View all crafting recipes\n"
        "`?craft [item]` — Craft an item from materials"
    ),
    "Mini-Games": (
        "🎮", discord.Color.purple(),
        "`?rps [rock/paper/scissors]` — Rock Paper Scissors\n"
        "`?8ball [question]` — Ask the magic 8-ball\n"
        "`?coinflip [amount]` — Flip vs bot | `?coinflip @user` — vs someone (alias: `?cf`)\n"
        "`?duel @user [amount]` — Secret RPS duel for points\n"
        "`?battle @user [amount]` — HP-based battle with crits\n"
        "`?slots [amount]` — Spin the slot machine (jackpots up to 50×!)\n"
        "`?blackjack [amount]` — Play blackjack vs the bot (alias: `?bj`)\n"
        "`?wordle` — Daily 5-letter word puzzle (same word for everyone)\n"
        "`?wordle [word]` — Submit a guess"
    ),
    "Community": (
        "👤", discord.Color.blurple(),
        "`?birthday DD/MM` — Register your birthday\n"
        "`?timezone set [location]` — Set your timezone (alias: `?tz`)\n"
        "`?timezone` — View your current timezone & local time\n"
        "`?setbio [text]` — Set your profile bio (max 150 chars)\n"
        "`?settitle` — Equip an achievement title on your profile\n"
        "`?clan create/join/leave/info/top` — Clan system\n"
        "`?clanwar [clan name]` — Declare war on another clan\n"
        "`?clanwar join` — Fight in your clan's active war\n"
        "`?partner @user` — Propose a partnership\n"
        "`?partner` — View your partnership stats & bonus\n"
        "`?unpartner` — End your partnership\n"
        "`?trade @user [item] for [item]` — Propose an item trade\n"
        "`?gift @user [item]` — Gift an item from your inventory"
    ),
}

# Mod-only category
_HELP_MOD = (
    "🛡️", discord.Color.red(),
    "`?raid` — Start a boss raid (everyone attacks with `?attack`)\n"
    "`?lock` — Lock this channel\n"
    "`?lock 2h / 30m / 1d` — Lock for a duration\n"
    "`?lock 28th 8:00 AM BST` — Lock until a date/time\n"
    "`?unlock` — Unlock this channel\n"
    "`?lockcategory` — Lock all channels in this category\n"
    "`?clearchannel` — Recreate channel (purges all messages)\n"
    "`?slowmode [seconds]` — Set channel slowmode (0 to remove)\n"
    "`?automod` — View automod status and thresholds\n"
    "`?note @user [text]` — Add a private mod note\n"
    "`?history @user` — Full mod history (warns, notes, automod)\n"
    "`?modstats` — AutoMod statistics and top offenders\n"
    "`?warn @user [rule/reason]` — Warn (use rule number 1-14)\n"
    "`?warnings @user` — View warning history\n"
    "`?clearwarnings @user` — Clear all warnings\n"
    "`?timeout @user [mins] [reason]` — Timeout a member\n"
    "`?untimeout @user` — Remove a timeout early\n"
    "`?mute @user [reason]` — Mute a member\n"
    "`?unmute @user` — Unmute a member\n"
    "`?tempban @user [days] [reason]` — Temp-ban (auto-unbans)\n"
    "`?purge [amount]` — Delete up to 100 messages\n"
    "`?hotdrop [amount]` — Drop points for first claimer\n"
    "`?startmarket` — Start the stock market (one-time)\n"
    "`?resetuploads` — Reset upload announcement tracking"
)

# Senior mod-only category
_HELP_SENIOR = (
    "👑", discord.Color.gold(),
    "`?ban @user [reason]` — Permanent ban\n"
    "`?softban @user [reason]` — Ban + unban to wipe recent messages\n"
    "`?unban @user` — Unban a member\n"
    "`?announce [message]` — Post a server announcement\n"
    "`?giveaway [duration] [winners] [prize]` — Start a giveaway\n"
    "`?reroll [message_id]` — Reroll a giveaway winner\n"
    "`?setuproles` — Post the reaction roles message\n"
    "`?setupalertroles` — Create Live Alerts & Upload Alerts roles"
)


def _help_home_embed(is_mod: bool, is_senior: bool) -> discord.Embed:
    if is_senior:
        desc  = "You are viewing this as a **Senior Moderator**."
        color = discord.Color.gold()
    elif is_mod:
        desc  = "You are viewing this as a **Moderator**."
        color = discord.Color.red()
    else:
        desc  = "Select a category below to browse commands."
        color = discord.Color.purple()

    embed = discord.Embed(
        title="📖 Help — Vexon's Bot",
        description=desc + "\n\nSelect a category using the buttons below.",
        color=color
    )
    embed.set_footer(text="Prefix for all commands is ?")
    return embed


def _help_category_embed(label: str, emoji: str, color: discord.Color, body: str) -> discord.Embed:
    return discord.Embed(
        title=f"{emoji} {label}",
        description=body,
        color=color
    )


class HelpView(discord.ui.View):
    def __init__(self, author_id: int, is_mod: bool, is_senior: bool):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.is_mod    = is_mod
        self.is_senior = is_senior

        # Add regular user category buttons (row 0 and 1)
        for i, (label, (emoji, color, body)) in enumerate(_HELP_CATEGORIES.items()):
            row = 0 if i < 4 else 1
            self.add_item(HelpCategoryButton(
                label=label, emoji=emoji, color=color, body=body,
                author_id=author_id, row=row
            ))

        # Add mod button if applicable (row 2)
        if is_mod:
            emoji, color, body = _HELP_MOD
            self.add_item(HelpCategoryButton(
                label="Mod Commands", emoji=emoji, color=color, body=body,
                author_id=author_id, row=2,
                style=discord.ButtonStyle.danger
            ))

        # Add senior button if applicable (row 2)
        if is_senior:
            emoji, color, body = _HELP_SENIOR
            self.add_item(HelpCategoryButton(
                label="Senior Mod", emoji=emoji, color=color, body=body,
                author_id=author_id, row=2,
                style=discord.ButtonStyle.danger
            ))


class HelpCategoryButton(discord.ui.Button):
    def __init__(self, label, emoji, color, body, author_id, row,
                 style=discord.ButtonStyle.secondary):
        super().__init__(
            label=label, emoji=emoji,
            style=style, row=row
        )
        self.cat_label  = label
        self.cat_emoji  = emoji
        self.cat_color  = color
        self.cat_body   = body
        self.author_id  = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This menu is not for you. Run `?help` yourself!", ephemeral=True
            )
            return
        embed = _help_category_embed(
            self.cat_label, self.cat_emoji, self.cat_color, self.cat_body
        )
        await interaction.response.edit_message(
            embed=embed,
            view=HelpBackView(self.author_id, self.view.is_mod, self.view.is_senior)
        )


class HelpBackView(discord.ui.View):
    def __init__(self, author_id: int, is_mod: bool, is_senior: bool):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.is_mod    = is_mod
        self.is_senior = is_senior

    @discord.ui.button(label="← Back to Categories", style=discord.ButtonStyle.primary, row=0)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This menu is not for you!", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            embed=_help_home_embed(self.is_mod, self.is_senior),
            view=HelpView(self.author_id, self.is_mod, self.is_senior)
        )


@bot.command(name="level")
async def level_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    await log_command(ctx.guild, ctx.author, "level", f"on {member.display_name}")
    data = load_data()
    data = ensure_keys(data)
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
    data = ensure_keys(data)
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
    now = discord.utils.utcnow()
    created = member.created_at.strftime("%d %b %Y")
    joined = member.joined_at.strftime("%d %b %Y") if member.joined_at else "Unknown"
    account_age = (now - member.created_at).days
    server_age = (now - member.joined_at).days if member.joined_at else 0
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
    description_lines = [
        f"{ctx.author.mention} claimed their daily reward!\n",
        f"**Day Streak:** {current_streak}",
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

    max_steal = max(1, max_steal)  # guard: randint(1,0) raises ValueError
    stolen = random.randint(1, max_steal)

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

SERVER_RULES = {
    1: "Be respectful",
    2: "No hate speech or discrimination",
    3: "No slurs",
    4: "Do not bypass moderation or filters",
    5: "No controversial or disruptive topics",
    6: "No offensive jokes",
    7: "No false accusations",
    8: "No threats or illegal activity",
    9: "No NSFW or illegal content",
    10: "No scams, selling, or unauthorized advertising",
    11: "Do not beg for roles or staff decisions",
    12: "Follow voice chat rules",
    13: "Staff decisions are final",
    14: "Having a role does not exempt you",
}

@bot.command(name="warn")
@mod_only()
async def warn_cmd(ctx, member: discord.Member, rule_or_reason: str = None, *, extra: str = ""):
    """
    ?warn @user [reason]
    ?warn @user [rule number] [optional extra reason]
    e.g. ?warn @user 3
    e.g. ?warn @user 3 repeated offence
    """
    await log_command(ctx.guild, ctx.author, "warn", f"on {member.display_name}")
    # Determine reason — check if first arg is a rule number
    reason = "No reason provided"
    rule_ref = ""
    if rule_or_reason:
        if rule_or_reason.isdigit() and int(rule_or_reason) in SERVER_RULES:
            rule_num = int(rule_or_reason)
            rule_ref = f"Rule {rule_num}: {SERVER_RULES[rule_num]}"
            reason = rule_ref + (f" — {extra}" if extra else "")
        else:
            reason = rule_or_reason + (f" {extra}" if extra else "")
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
    # Warning escalation — 3 / 5 / 7 / 9 / 10
    escalation_msg = None
    if total_warnings == 3:
        await member.timeout(timedelta(hours=1), reason="Auto: 3 warnings")
        action_key = f"timeout_{ctx.guild.id}_{member.id}"
        await strip_roles_for_punishment(ctx.guild, member, data, guild_id, user_id, action_key)
        expiry_ts = int(time.time()) + 3600
        data["timeout_expiry"][f"{ctx.guild.id}_{member.id}"] = expiry_ts
        save_data(data)
        await create_case_channel(ctx.guild, member, "Timed Out", "3 warnings reached", ctx.guild.me,
            duration=f"1 hour — ends <t:{expiry_ts}:R>", channel_prefix="timeout")
        escalation_msg = f"⚠️ {member.mention} has reached **3 warnings** — timed out for **1 hour**."
    elif total_warnings == 5:
        await member.timeout(timedelta(hours=5), reason="Auto: 5 warnings")
        action_key = f"timeout_{ctx.guild.id}_{member.id}"
        await strip_roles_for_punishment(ctx.guild, member, data, guild_id, user_id, action_key)
        expiry_ts = int(time.time()) + 18000
        data["timeout_expiry"][f"{ctx.guild.id}_{member.id}"] = expiry_ts
        save_data(data)
        await create_case_channel(ctx.guild, member, "Timed Out", "5 warnings reached", ctx.guild.me,
            duration=f"5 hours — ends <t:{expiry_ts}:R>", channel_prefix="timeout")
        escalation_msg = f"⚠️ {member.mention} has reached **5 warnings** — timed out for **5 hours**."
    elif total_warnings == 7:
        await member.timeout(timedelta(hours=10), reason="Auto: 7 warnings")
        action_key = f"timeout_{ctx.guild.id}_{member.id}"
        await strip_roles_for_punishment(ctx.guild, member, data, guild_id, user_id, action_key)
        expiry_ts = int(time.time()) + 36000
        data["timeout_expiry"][f"{ctx.guild.id}_{member.id}"] = expiry_ts
        save_data(data)
        await create_case_channel(ctx.guild, member, "Timed Out", "7 warnings reached", ctx.guild.me,
            duration=f"10 hours — ends <t:{expiry_ts}:R>", channel_prefix="timeout")
        escalation_msg = f"⚠️ {member.mention} has reached **7 warnings** — timed out for **10 hours**."
    elif total_warnings == 9:
        await member.timeout(timedelta(hours=24), reason="Auto: 9 warnings")
        action_key = f"timeout_{ctx.guild.id}_{member.id}"
        await strip_roles_for_punishment(ctx.guild, member, data, guild_id, user_id, action_key)
        expiry_ts = int(time.time()) + 86400
        data["timeout_expiry"][f"{ctx.guild.id}_{member.id}"] = expiry_ts
        save_data(data)
        await create_case_channel(ctx.guild, member, "Timed Out", "9 warnings reached", ctx.guild.me,
            duration=f"24 hours — ends <t:{expiry_ts}:R>", channel_prefix="timeout")
        escalation_msg = f"⚠️ {member.mention} has reached **9 warnings** — timed out for **24 hours**."
    elif total_warnings >= 10:
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if mute_role and mute_role not in member.roles:
            await member.add_roles(mute_role, reason="Auto: 10+ warnings")
            action_key = f"muted_{ctx.guild.id}_{member.id}"
            await strip_roles_for_punishment(ctx.guild, member, data, guild_id, user_id, action_key)
            save_data(data)
            await create_case_channel(ctx.guild, member, "Muted", "10+ warnings reached", ctx.guild.me, channel_prefix="muted")
            escalation_msg = f"🔇 {member.mention} has reached **10 warnings** and has been permanently **muted**."

    await ctx.send(f"{member.mention} has been warned. They now have **{total_warnings}** warning(s). Reason: {reason}")
    if escalation_msg:
        await ctx.send(escalation_msg)
    await log_action(ctx.guild, "Warning", member, ctx.author, reason)
    bot_log = discord.utils.get(ctx.guild.text_channels, name=BOT_LOGS_CHANNEL)
    if bot_log:
        embed = discord.Embed(title="Warning Issued", description=f"{member.mention} warned by {ctx.author.mention}", color=discord.Color.orange())
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Total Warnings", value=str(total_warnings))
        if escalation_msg:
            embed.add_field(name="Auto-Escalation", value=escalation_msg, inline=False)
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

async def run_trivia(guild, trivia_channel, question, is_auto=False):
    """Core trivia runner with 3 hints. Used by both ?trivia and auto-trivia."""
    guild_id = str(guild.id)
    hints = question.get("hints", [])
    label = "Auto Trivia!" if is_auto else "Trivia Time!"
    embed = discord.Embed(
        title=label,
        description=(
            f"{question['q']}\n\n"
            f"First to answer wins **{TRIVIA_XP_REWARD} XP** and **{TRIVIA_POINTS_REWARD} points**!\n"
            f"Hints will appear if nobody answers. You have {TRIVIA_TIMEOUT} seconds!"
        ),
        color=discord.Color.blue()
    )
    await trivia_channel.send(embed=embed)

    hint_index = [0]  # mutable so the message listener below can advance it

    def wrong_answer_check(m):
        return (
            m.channel == trivia_channel
            and not m.author.bot
            and guild_id in active_trivia
            and not fuzzy_match(m.content, question["a"])
        )

    deadline = asyncio.get_event_loop().time() + TRIVIA_TIMEOUT
    while guild_id in active_trivia:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            await asyncio.wait_for(
                bot.wait_for("message", check=wrong_answer_check),
                timeout=remaining
            )
            # Someone answered wrongly — give next hint if available
            if hints and hint_index[0] < len(hints):
                await trivia_channel.send(f"💡 **Hint {hint_index[0]+1}:** {hints[hint_index[0]]}")
                hint_index[0] += 1
        except asyncio.TimeoutError:
            break  # time ran out

    if guild_id in active_trivia:
        del active_trivia[guild_id]
        await trivia_channel.send(f"⏰ Time is up! The answer was **{question['a'].title()}**.")

AUTO_TRIVIA_CHANNELS = ["lounge", "bot-commands"]  # checked in order, uses most active

def get_most_active_channel(guild, channel_names):
    """Return the first channel from channel_names that exists in the guild."""
    for name in channel_names:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch:
            return ch
    return None

async def auto_trivia(guild, trigger_channel=None):
    """Automatically fires a trivia question in the channel that triggered it."""
    guild_id = str(guild.id)
    if guild_id in active_trivia:
        return
    trivia_channel = trigger_channel or get_most_active_channel(guild, AUTO_TRIVIA_CHANNELS)
    if not trivia_channel:
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
    active_trivia[guild_id] = {
        "answer": question["a"],
        "channel_id": trivia_channel.id,
        "hints": question.get("hints", []),
    }
    await run_trivia(guild, trivia_channel, question, is_auto=True)

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
UNVERIFIED_CATEGORY = "Unverified"       # Hidden from member during punishment


# ============================================================
#   ROLE SAVE / RESTORE HELPERS
# ============================================================

ROLES_TO_NEVER_RESTORE = {"Muted", "Timed Out"}  # never re-added on restore

async def strip_roles_for_punishment(guild, member, data, guild_id, user_id, action_key):
    """
    Remove ALL assignable roles (including Verified).
    Saves the removed role IDs to data so they can be restored later.
    action_key is a unique string like "muted_123456" or "timeout_123456".
    """
    roles_to_remove = [
        r for r in member.roles
        if r.name != "@everyone"
        and r.name not in ROLES_TO_NEVER_RESTORE
        and not r.managed           # skip integration-managed roles
        and r < guild.me.top_role   # skip roles above the bot
    ]
    if not roles_to_remove:
        return
    # Store role IDs before removing
    if "saved_roles" not in data:
        data["saved_roles"] = {}
    data["saved_roles"][action_key] = [r.id for r in roles_to_remove]
    try:
        await member.remove_roles(*roles_to_remove, reason="Punishment: roles stripped")
    except discord.Forbidden:
        print(f"Could not strip roles from {member}: missing permissions")

    # Hide the Unverified category so they cannot access verification or ticket channels
    unverified_cat = discord.utils.get(guild.categories, name=UNVERIFIED_CATEGORY)
    if unverified_cat:
        try:
            await unverified_cat.set_permissions(member, view_channel=False, reason="Punishment: hide Unverified")
        except discord.Forbidden:
            print(f"Could not hide Unverified category from {member}")

async def restore_roles_after_punishment(guild, member, data, action_key):
    """
    Re-adds the roles that were stripped during punishment.
    Cleans up the saved_roles entry afterwards.
    """
    saved = data.get("saved_roles", {}).get(action_key, [])
    if not saved:
        return
    roles_to_add = []
    for role_id in saved:
        role = guild.get_role(role_id)
        if role and role.name not in ROLES_TO_NEVER_RESTORE and role < guild.me.top_role:
            roles_to_add.append(role)
    if roles_to_add:
        try:
            await member.add_roles(*roles_to_add, reason="Punishment lifted: roles restored")
        except discord.Forbidden:
            print(f"Could not restore roles for {member}: missing permissions")
    data.get("saved_roles", {}).pop(action_key, None)

    # Remove the Unverified category overwrite so normal access resumes
    unverified_cat = discord.utils.get(guild.categories, name=UNVERIFIED_CATEGORY)
    if unverified_cat:
        try:
            await unverified_cat.set_permissions(member, overwrite=None, reason="Punishment lifted: restore Unverified access")
        except discord.Forbidden:
            print(f"Could not restore Unverified category for {member}")

async def create_case_channel(guild, member, action_type, reason, moderator, duration=None, channel_prefix="case"):
    """
    Creates a private read-only channel for the punished member inside
    the existing '#4 | Timeouts/Muted' category.
    - The member can see it but NOT send messages.
    - Mod, Managers, and Ahmed (owner role) can see and send.
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

    # Build explicit overwrites so:
    #   @everyone     → cannot see the channel at all
    #   the member    → can read but not send messages (their case only)
    #   mod roles     → can see and talk
    #   bot           → can see and talk (needed to post the embed)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me:           discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        member: discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=False,
            create_public_threads=False,
            create_private_threads=False,
            send_messages_in_threads=False,
            add_reactions=False,
            attach_files=True,
            embed_links=False,
            use_external_emojis=False,
            use_external_stickers=False,
        ),
    }
    # Give mod roles view + send access
    for role_name in mod_role_names:
        mod_role = discord.utils.get(guild.roles, name=role_name)
        if mod_role:
            overwrites[mod_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    # Managers and Ahmed (owner role) explicitly
    for special in ("Managers", "Ahmed"):
        r = discord.utils.get(guild.roles, name=special)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    if guild.owner:
        overwrites[guild.owner] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites, topic=str(member.id))

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
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Case opened by {moderator.display_name}")
    await channel.send(embed=embed)
    return channel


async def close_case_channel(guild, member, channel_prefix="case"):
    """
    Finds and deletes the case channel for a member.
    Searches the Timeouts/Muted category for any channel whose name starts with
    '<prefix>-' and contains the member's ID or username fragment, so we are not
    fragile to display-name changes or Discord normalisation differences.
    """
    member_id_str = str(member.id)
    category = discord.utils.get(guild.categories, name=CASE_CATEGORY)
    search_space = category.text_channels if category else guild.text_channels

    # Try exact computed name first
    safe_name = "".join(c if c.isalnum() or c == "-" else "-" for c in member.display_name.lower())
    exact_name = f"{channel_prefix}-{safe_name}"[:100]
    channel = discord.utils.get(search_space, name=exact_name)

    # Fallback: any channel in the category whose topic contains the member ID
    if not channel and category:
        for ch in category.text_channels:
            if ch.name.startswith(f"{channel_prefix}-") and (
                ch.topic and member_id_str in ch.topic
            ):
                channel = ch
                break

    # Last resort: first channel in category starting with prefix-
    if not channel and category:
        for ch in category.text_channels:
            if ch.name.startswith(f"{channel_prefix}-"):
                # Check pinned/recent messages for a mention of this member
                try:
                    async for msg in ch.history(limit=5):
                        if member_id_str in msg.content:
                            channel = ch
                            break
                except Exception:
                    pass
                if channel:
                    break

    if channel:
        try:
            await channel.send(
                f"{member.mention} your punishment has been lifted. This channel will now be deleted."
            )
            await asyncio.sleep(5)
            await channel.delete(reason="Punishment lifted")
        except Exception as e:
            print(f"close_case_channel error: {e}")


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

        # Strip all roles except Verified and save them for restoration
        action_key = f"timeout_{ctx.guild.id}_{member.id}"
        await strip_roles_for_punishment(ctx.guild, member, data, str(ctx.guild.id), str(member.id), action_key)
        save_data(data)

        # Build Discord timestamps — these show in the user's local timezone automatically
        ends_at_display   = f"<t:{expiry_ts}:F>"   # e.g. "Tuesday, 1 April 2025 at 17:35"
        ends_at_relative  = f"<t:{expiry_ts}:R>"   # e.g. "in 10 minutes"

        # Create the private case channel in the Timeouts/Muted category
        await create_case_channel(
            ctx.guild, member, "Timed Out", reason, ctx.author,
            duration=f"{minutes} minute(s)", channel_prefix="timeout"
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


@bot.command(name="untimeout")
@mod_only()
async def untimeout_cmd(ctx, member: discord.Member):
    await log_command(ctx.guild, ctx.author, "untimeout", f"on {member.display_name}")
    try:
        # Remove Discord native timeout
        await member.timeout(None, reason=f"Timeout removed by {ctx.author}")

        # Remove Timed Out role
        timeout_role = discord.utils.get(ctx.guild.roles, name="Timed Out")
        if timeout_role and timeout_role in member.roles:
            await member.remove_roles(timeout_role, reason="Timeout removed manually")

        # Restore stripped roles
        data = load_data()
        data = ensure_keys(data)
        action_key = f"timeout_{ctx.guild.id}_{member.id}"
        await restore_roles_after_punishment(ctx.guild, member, data, action_key)

        # Clear stored expiry
        expiry_key = f"{ctx.guild.id}_{member.id}"
        data.get("timeout_expiry", {}).pop(expiry_key, None)
        save_data(data)

        # Close the case channel
        await close_case_channel(ctx.guild, member, channel_prefix="timeout")

        await ctx.send(f"{member.mention}'s timeout has been removed.")
        await log_action(ctx.guild, "Untimeout", member, ctx.author, "Manual removal")
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
            await ctx.send(
                "Could not find a role called **Muted**. "
                "Create it in Server Settings > Roles, then deny Send Messages in every channel for that role."
            )
            return
        if mute_role in member.roles:
            await ctx.send(f"{member.mention} is already muted.")
            return

        await member.add_roles(mute_role, reason=reason)

        # Strip all roles except Verified and save them for restoration
        data = load_data()
        data = ensure_keys(data)
        action_key = f"muted_{ctx.guild.id}_{member.id}"
        await strip_roles_for_punishment(ctx.guild, member, data, str(ctx.guild.id), str(member.id), action_key)
        save_data(data)

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

            # Restore the roles that were stripped when they were muted
            data = load_data()
            data = ensure_keys(data)
            action_key = f"muted_{ctx.guild.id}_{member.id}"
            await restore_roles_after_punishment(ctx.guild, member, data, action_key)
            save_data(data)

            # Close the muted- channel
            await close_case_channel(ctx.guild, member, channel_prefix="muted")

            await ctx.send(f"{member.mention} has been unmuted. Their roles have been restored.")
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
        # Ban first — only record in data if it actually succeeds
        await member.ban(reason=f"Temp-ban ({days}d) by {ctx.author}", delete_message_days=0)
        tb_key = f"{ctx.guild.id}_{member.id}"
        data["tempbans"][tb_key] = {
            "guild_id": str(ctx.guild.id),
            "unban_ts": unban_ts,
            "reason": reason,
            "mod": str(ctx.author)
        }
        save_data(data)
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

# Name of the role and channel used for the soft-ban system
BANNED_ROLE_NAME = "Banned"
BANNED_CHANNEL_NAME = "tickets"  # the only channel they can see
BANNED_CHANNEL_CATEGORY = "Tickets"  # category that channel lives in

@bot.command(name="ban")
@mod_only()
async def ban_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    """Soft-ban: strips all roles, applies Banned role, only #tickets visible. Keeps them in server."""
    await log_command(ctx.guild, ctx.author, "ban", f"on {member.display_name}")
    senior_roles = ["Managers", "Ahmed"]
    if not any(r.name in senior_roles for r in ctx.author.roles) and not ctx.author.guild_permissions.administrator:
        await ctx.send("Only **Managers** and the **Ahmed** role can use this command.")
        return
    try:
        # Get or create the Banned role
        ban_role = discord.utils.get(ctx.guild.roles, name=BANNED_ROLE_NAME)
        if not ban_role:
            ban_role = await ctx.guild.create_role(
                name=BANNED_ROLE_NAME,
                color=discord.Color.dark_red(),
                reason="Auto-created for soft-ban system"
            )
        if ban_role in member.roles:
            await ctx.send(f"{member.mention} is already banned.")
            return

        # Save and strip all roles
        data = load_data()
        data = ensure_keys(data)
        action_key = f"banned_{ctx.guild.id}_{member.id}"
        await strip_roles_for_punishment(ctx.guild, member, data, str(ctx.guild.id), str(member.id), action_key)
        save_data(data)

        # Apply Banned role
        await member.add_roles(ban_role, reason=f"Banned by {ctx.author} — {reason}")

        # Deny the Banned role from seeing everything, then allow only #tickets
        # First: deny view on every category and channel for the Banned role
        for cat in ctx.guild.categories:
            if cat.name != BANNED_CHANNEL_CATEGORY:
                try:
                    await cat.set_permissions(ban_role, view_channel=False, reason="Banned role lockout")
                except discord.Forbidden:
                    pass
        for ch in ctx.guild.channels:
            if not hasattr(ch, "category") or (ch.category and ch.category.name != BANNED_CHANNEL_CATEGORY):
                try:
                    await ch.set_permissions(ban_role, view_channel=False, reason="Banned role lockout")
                except discord.Forbidden:
                    pass

        # Allow the Banned role to see and send in #tickets only
        tickets_ch = discord.utils.get(ctx.guild.text_channels, name=BANNED_CHANNEL_NAME)
        if tickets_ch:
            await tickets_ch.set_permissions(ban_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                create_public_threads=False,
                create_private_threads=False,
                add_reactions=False,
                attach_files=False,
                embed_links=False,
            )

        # DM the member
        try:
            await member.send(
                f"You have been banned in **{ctx.guild.name}**.\n"
                f"**Reason:** {reason}\n"
                f"You can only access the **#tickets** channel. "
                f"If you believe this is a mistake, open a ticket there."
            )
        except discord.Forbidden:
            pass

        embed = discord.Embed(
            title="Member Banned",
            description=(
                f"**Member:** {member.mention}\n"
                f"**Banned by:** {ctx.author.mention}\n"
                f"**Reason:** {reason}\n\n"
                f"They have been restricted to **#tickets** only and cannot see other channels."
            ),
            color=discord.Color.dark_red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        await log_action(ctx.guild, "Ban (Soft)", member, ctx.author, reason)
    except discord.Forbidden:
        await ctx.send("I do not have permission to do that.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")

@bot.command(name="unban")
@mod_only()
async def unban_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    """Remove the Banned role and restore the member's roles."""
    await log_command(ctx.guild, ctx.author, "unban", f"on {member.display_name}")
    senior_roles = ["Managers", "Ahmed"]
    if not any(r.name in senior_roles for r in ctx.author.roles) and not ctx.author.guild_permissions.administrator:
        await ctx.send("Only **Managers** and the **Ahmed** role can unban members.")
        return
    ban_role = discord.utils.get(ctx.guild.roles, name=BANNED_ROLE_NAME)
    if not ban_role or ban_role not in member.roles:
        await ctx.send(f"{member.mention} is not banned.")
        return
    try:
        await member.remove_roles(ban_role, reason=f"Unbanned by {ctx.author}")
        data = load_data()
        data = ensure_keys(data)
        action_key = f"banned_{ctx.guild.id}_{member.id}"
        await restore_roles_after_punishment(ctx.guild, member, data, action_key)
        save_data(data)
        await ctx.send(f"{member.mention} has been unbanned and their roles have been restored.")
        await log_action(ctx.guild, "Unban", member, ctx.author, reason)
    except discord.Forbidden:
        await ctx.send("I do not have permission to unban that member.")
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

ALERT_ROLES = {
    "🔴": "Live Alerts",
    "📹": "Upload Alerts",
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

    # ---- Alert roles ----
    for emoji, role_name in ALERT_ROLES.items():
        await get_or_create_alert_role(
            ctx.guild, role_name,
            discord.Colour.red()
        )  # return value unused here

    alert_desc = (
        "React below to choose which notifications you want to receive.\n\n"
        "**\U0001f514 Notification Roles**\n"
        "\U0001f534 \u2014 **Live Alerts** \u2014 Get pinged when Vexon goes live on Twitch, Kick or YouTube\n"
        "\U0001f4f9 \u2014 **Upload Alerts** \u2014 Get pinged when Vexon uploads to YouTube or TikTok\n\n"
        "You can remove your reaction at any time to remove the role."
    )
    embed_alerts = discord.Embed(title="🔔 Notification Alerts", description=alert_desc, color=discord.Color.gold())
    msg_alerts = await channel.send(embed=embed_alerts)
    for emoji in ALERT_ROLES.keys():
        await msg_alerts.add_reaction(emoji)

    config["reaction_roles"]["alert_message_id"] = str(msg_alerts.id)
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

FUN_QUIZ_TYPES = ["lyric", "moviequote", "emoji", "guessgame"]

async def run_fun_quiz_in_channel(channel, quiz_type):
    """Run a fun quiz question in the given channel, award XP/points to first correct answer."""
    guild_id = str(channel.guild.id)
    active_fun_quiz[guild_id] = True
    try:
        if quiz_type == "lyric":
            question = random.choice(LYRIC_QUIZ)
            title = "🎵 Auto: Name That Song!"
            desc = f'*"{question["lyric"]}"*\n\nWhat song is this? **{FUN_QUIZ_TIMEOUT}s**!'
            color = discord.Color.purple()
            check_fn = lambda m, q=question: fuzzy_match(m.content, q["answer"])
            reveal_fn = lambda q=question: f'**{q["answer"].title()}** by **{q["artist"]}**'
        elif quiz_type == "moviequote":
            question = random.choice(MOVIE_QUOTES)
            title = "🎬 Auto: Name That Movie!"
            desc = f'*"{question["quote"]}"* — *{question["character"]}*\n\nWhat movie? **{FUN_QUIZ_TIMEOUT}s**!'
            color = discord.Color.red()
            check_fn = lambda m, q=question: fuzzy_match(m.content, q["answer"])
            reveal_fn = lambda q=question: f'**{q["answer"].title()}**'
        elif quiz_type == "emoji":
            question = random.choice(EMOJI_PUZZLES)
            title = "🧩 Auto: Emoji Puzzle!"
            desc = f'**{question["puzzle"]}**\n*Hint: {question["hint"]}*\n\nWhat is it? **{FUN_QUIZ_TIMEOUT}s**!'
            color = discord.Color.teal()
            check_fn = lambda m, q=question: fuzzy_match(m.content, q["answer"])
            reveal_fn = lambda q=question: f'**{q["answer"].title()}**'
        else:
            question = random.choice(GUESS_THE_GAME)
            title = "🎮 Auto: Guess The Game!"
            desc = f'{question["clue"]}\n\n**{FUN_QUIZ_TIMEOUT}s** to answer!'
            color = discord.Color.blue()
            check_fn = lambda m, q=question: fuzzy_match(m.content, q["answer"])
            reveal_fn = lambda q=question: f'**{q["answer"].title()}**'

        embed = discord.Embed(title=title, description=desc, color=color)
        await channel.send(embed=embed)
        def check(m): return m.author != channel.guild.me and m.channel == channel and check_fn(m)
        try:
            msg = await bot.wait_for("message", check=check, timeout=FUN_QUIZ_TIMEOUT)
            data = load_data()
            data = ensure_keys(data)
            uid = str(msg.author.id)
            gid = guild_id
            old_xp = get_user_xp(data, gid, uid)
            set_user_xp(data, gid, uid, old_xp + FUN_QUIZ_XP)
            set_user_points(data, gid, uid, get_user_points(data, gid, uid) + FUN_QUIZ_POINTS)
            save_data(data)
            await check_and_announce_level_up(channel.guild, msg.author, old_xp, old_xp + FUN_QUIZ_XP, data, gid, uid)
            await channel.send(embed=discord.Embed(title="✅ Correct!",
                description=f"{msg.author.mention} got it! The answer was {reveal_fn()}!\n+**{FUN_QUIZ_XP} XP** +**{FUN_QUIZ_POINTS} pts**",
                color=discord.Color.green()))
        except asyncio.TimeoutError:
            await channel.send(f"⏰ Time's up! The answer was {reveal_fn()}.")
    finally:
        active_fun_quiz.pop(guild_id, None)

async def auto_fun_quiz(guild, trigger_channel):
    """Pick a random fun quiz type and run it in the channel that triggered it."""
    ch = trigger_channel or get_most_active_channel(guild, ["lounge", "bot-commands"])
    quiz_type = random.choice(FUN_QUIZ_TYPES)
    await run_fun_quiz_in_channel(ch, quiz_type)

@bot.command(name="lyric")
async def lyric_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "lyric")
    question = random.choice(LYRIC_QUIZ)
    embed = discord.Embed(
        title="🎵 Name That Song!",
        description=f"*\"{question['lyric']}\"*\n\nWhat song is this from? You have {FUN_QUIZ_TIMEOUT} seconds!\n\n💬 **Just type your answer in the chat!**",
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
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ Time's up! The song was **{question['answer'].title()}** by **{question['artist']}**.")

@bot.command(name="moviequote", aliases=["quote"])
async def moviequote_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "moviequote")
    question = random.choice(MOVIE_QUOTES)
    embed = discord.Embed(
        title="🎬 Name That Movie!",
        description=f"*\"{question['quote']}\"*\n— *{question['character']}*\n\nWhat movie is this from? You have {FUN_QUIZ_TIMEOUT} seconds!\n\n💬 **Just type your answer in the chat!**",
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
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ Time's up! The answer was **{question['answer'].title()}**.")

@bot.command(name="emojipuzzle", aliases=["emoji"])
async def emojipuzzle_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "emojipuzzle")
    question = random.choice(EMOJI_PUZZLES)
    embed = discord.Embed(
        title="🧩 Emoji Puzzle!",
        description=f"**{question['puzzle']}**\n\n*Hint: {question['hint']}*\n\nWhat movie/show is this? You have {FUN_QUIZ_TIMEOUT} seconds!\n\n💬 **Just type your answer in the chat!**",
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
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ Time's up! The answer was **{question['answer'].title()}**.")

@bot.command(name="guessgame", aliases=["gg"])
async def guessgame_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "guessgame")
    question = random.choice(GUESS_THE_GAME)
    embed = discord.Embed(
        title="🎮 Guess The Game!",
        description=f"{question['clue']}\n\nYou have {FUN_QUIZ_TIMEOUT} seconds!\n\n💬 **Just type your answer in the chat!**",
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
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ Time's up! The game was **{question['answer'].title()}**.")


@bot.command(name="resetuploads")
@mod_only()
async def resetuploads_cmd(ctx, platform: str = "all"):
    """Clear stored upload IDs so the next video gets announced. Platform: youtube, tiktok, or all."""
    await log_command(ctx.guild, ctx.author, "resetuploads", platform)
    data = load_data()
    data = ensure_keys(data)
    platform = platform.lower()
    cleared = []
    if platform in ("youtube", "all"):
        data["last_youtube_id"] = None
        cleared.append("YouTube")
    if platform in ("tiktok", "all"):
        data["last_tiktok_id"] = None
        cleared.append("TikTok")
    if not cleared:
        await ctx.send("Unknown platform. Use `youtube`, `tiktok`, or `all`.")
        return
    save_data(data)
    await ctx.send(f"Reset upload tracking for: **{', '.join(cleared)}**. The next video found will be announced.")

@bot.command(name="setupalertroles")
@mod_only()
async def setupalertroles_cmd(ctx):
    """Create (or verify) the Twitch Alerts and Upload Alerts roles with the correct permissions."""
    await log_command(ctx.guild, ctx.author, "setupalertroles")
    created = []
    existed = []
    live_role, live_created = await get_or_create_alert_role(ctx.guild, "Live Alerts", discord.Colour.red())
    (created if live_created else existed).append(live_role.mention)

    upload_role, upload_created = await get_or_create_alert_role(ctx.guild, "Upload Alerts", discord.Colour.red())
    (created if upload_created else existed).append(upload_role.mention)

    lines = []
    if created:
        lines.append(f"✅ **Created:** {', '.join(created)}")
    if existed:
        lines.append(f"ℹ️ **Already existed:** {', '.join(existed)}")
    lines.append("\nMembers can self-assign these roles to receive stream/upload pings.")
    embed = discord.Embed(
        title="🔔 Alert Roles Ready",
        description="\n".join(lines),
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# ============================================================
#   ERROR HANDLING
# ============================================================


# ============================================================
#   INTERACTIVE SHOP (discord.ui.View with buttons + select)
# ============================================================

SHOP_CATEGORIES = {
    "🛡️ Shields":      ["shield_30m", "shield_1h", "shield_5h", "shield_10h", "shield_1d", "shield_3d", "shield_7d"],
    "⚡ XP Boosts":    ["xp_boost_1h", "xp_boost_24h"],
    "🎒 Economy":      ["point_vault", "robbery_kit", "steal_insurance", "daily_booster", "lucky_charm", "disguise", "scratch_card"],
    "🎣 Fishing":      ["fishing_rod", "bait", "fish_bucket"],
    "🏹 Hunting":      ["ammo_pack", "hunting_rifle"],
    "🗺️ Adventure":    ["adventure_kit"],
}

class ShopCategoryView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.author_id = author_id
        for cat in SHOP_CATEGORIES:
            self.add_item(ShopCategoryButton(cat, author_id))

class ShopCategoryButton(discord.ui.Button):
    def __init__(self, category, author_id):
        super().__init__(label=category, style=discord.ButtonStyle.secondary)
        self.category = category
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return
        item_keys = SHOP_CATEGORIES[self.category]
        items = {k: SHOP_ITEMS[k] for k in item_keys if k in SHOP_ITEMS}
        embed = discord.Embed(title=f"Shop — {self.category}", color=discord.Color.blue())
        for key, item in items.items():
            price_str = f"**{item['price']} pts**"
            extra = ""
            if item.get("duration"):
                h = item["duration"] // 3600
                m = (item["duration"] % 3600) // 60
                extra = f" | {h}h {m}m" if h else f" | {m}m"
            embed.add_field(
                name=f"{item['name']} — {price_str}{extra}",
                value=f"{item['description']}\n`?buy {key}`",
                inline=False
            )
        embed.set_footer(text="To buy an item, type: ?buy {item_id}  •  e.g. ?buy shield_1h")
        back_view = BackToShopView(self.author_id)
        await interaction.response.edit_message(embed=embed, view=back_view)

class BackToShopView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.author_id = author_id

    @discord.ui.button(label="← Back to Categories", style=discord.ButtonStyle.primary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return
        embed = discord.Embed(
            title="🛒 Shop",
            description="Select a category below to browse items.\n\nTo buy: `?buy <item_id>`",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=ShopCategoryView(self.author_id))

@bot.command(name="shop")
async def shop_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "shop")
    embed = discord.Embed(
        title="🛒 Shop",
        description="Select a category below to browse items.\n\nTo buy an item: `?buy <item_id>`",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=ShopCategoryView(ctx.author.id))

@bot.command(name="buy")
async def buy_cmd(ctx, item_id: str = None):
    await log_command(ctx.guild, ctx.author, "buy", item_id or "")
    if not item_id or item_id not in SHOP_ITEMS:
        await ctx.send("Invalid item ID. Use `?shop` to browse items.")
        return
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    user_id  = str(ctx.author.id)
    item = SHOP_ITEMS[item_id]
    current_pts = get_user_points(data, guild_id, user_id)
    if current_pts < item["price"]:
        needed = item["price"] - current_pts
        await ctx.send(
            f"💸 Low amount of points. You need **{needed} more points** to purchase **{item['name']}** (costs {item['price']})."
        )
        return
    set_user_points(data, guild_id, user_id, current_pts - item["price"])
    add_to_inventory(data, guild_id, user_id, item_id)
    if item["type"] == "vault":
        current_vault = get_vault(data, guild_id, user_id)
        set_vault(data, guild_id, user_id, current_vault + item["capacity"])
    save_data(data)
    await check_and_grant_achievements(ctx.guild, ctx.author, data, guild_id, user_id, ctx.channel)
    embed = discord.Embed(
        title="✅ Purchase Successful!",
        description=f"You bought **{item['name']}** for **{item['price']} points**!\n{item['description']}",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Remaining balance: {get_user_points(data, guild_id, user_id)} points")
    await ctx.send(embed=embed)

# ============================================================
#   BEG
# ============================================================

BEG_OUTCOMES = [
    ("A kind stranger gave you some coins. Every little helps!",         True,  (10, 80)),
    ("Someone tossed you a coin and said 'get a job'.",                  True,  (5,  50)),
    ("A passing dog looked at you with more pity than the humans did.",  True,  (15, 60)),
    ("You played sad music and people actually paid you.",               True,  (20, 100)),
    ("A child gave you their pocket money. You feel terrible.",          True,  (10, 40)),
    ("Everyone ignored you. Not a single coin.",                         False, (0, 0)),
    ("Someone laughed at you and walked away.",                          False, (0, 0)),
    ("A pigeon stole the coin someone threw. Rough day.",                False, (0, 0)),
    ("You tripped over your own sign. No coins.",                        False, (0, 0)),
]
BEG_COOLDOWN = 60

beg_cooldowns = {}

@bot.command(name="beg")
async def beg_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "beg")
    uid = str(ctx.author.id)
    now = time.time()
    if uid in beg_cooldowns and now - beg_cooldowns[uid] < BEG_COOLDOWN:
        remaining = int(BEG_COOLDOWN - (now - beg_cooldowns[uid]))
        await ctx.send(f"You need to wait **{remaining}s** before begging again.")
        return
    beg_cooldowns[uid] = now
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)

    has_charm = has_item(data, guild_id, uid, "lucky_charm")
    if has_charm:
        outcome = random.choice([o for o in BEG_OUTCOMES if o[1]])
    else:
        outcome = random.choice(BEG_OUTCOMES)

    msg, success, (mn, mx) = outcome
    if success:
        earned = random.randint(mn, mx)
        set_user_points(data, guild_id, uid, get_user_points(data, guild_id, uid) + earned)
        save_data(data)
        embed = discord.Embed(description=f"🙏 {msg}\n\n+**{earned} points**", color=discord.Color.green())
    else:
        embed = discord.Embed(description=f"😞 {msg}", color=discord.Color.red())
    await ctx.send(embed=embed)

# ============================================================
#   CRIME
# ============================================================

CRIMES = [
    {"name": "Pickpocketing",    "success": 0.65, "reward": (80, 250),  "fail_loss": (20, 80),  "success_msg": "You slipped your hand into someone's pocket and pulled out {earned} points.", "fail_msg": "You were caught pickpocketing and fined {lost} points."},
    {"name": "Shoplifting",      "success": 0.55, "reward": (100, 350), "fail_loss": (30, 120), "success_msg": "You walked out with goods worth {earned} points. Clean getaway.", "fail_msg": "The security guard caught you. You were fined {lost} points."},
    {"name": "Graffiti",         "success": 0.70, "reward": (50, 180),  "fail_loss": (15, 60),  "success_msg": "You tagged the wall and ran. The art was actually pretty good. +{earned} points.", "fail_msg": "You got caught tagging and had to pay a {lost} point fine to clean it up."},
    {"name": "Hacking",          "success": 0.45, "reward": (200, 600), "fail_loss": (50, 200), "success_msg": "You broke into a poorly secured system and siphoned {earned} points worth of data.", "fail_msg": "Your IP got traced. You had to bribe someone {lost} points to stay quiet."},
    {"name": "Identity Fraud",   "success": 0.40, "reward": (300, 800), "fail_loss": (80, 300), "success_msg": "You pulled off the fraud and pocketed {earned} points before disappearing.", "fail_msg": "You were caught and had to pay {lost} points in penalties."},
    {"name": "Counterfeit Goods","success": 0.60, "reward": (120, 400), "fail_loss": (40, 150), "success_msg": "Your knock-off goods sold well. Earned {earned} points and vanished.", "fail_msg": "Trading standards busted you. Fined {lost} points."},
]
CRIME_COOLDOWN = 300

crime_cooldowns = {}

@bot.command(name="crime")
async def crime_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "crime")
    uid = str(ctx.author.id)
    now = time.time()
    if uid in crime_cooldowns and now - crime_cooldowns[uid] < CRIME_COOLDOWN:
        remaining = int(CRIME_COOLDOWN - (now - crime_cooldowns[uid]))
        next_ts = int(crime_cooldowns[uid] + CRIME_COOLDOWN)
        await ctx.send(f"You need to lay low. Crime available <t:{next_ts}:R>.")
        return
    crime_cooldowns[uid] = now
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)

    crime = random.choice(CRIMES)
    has_charm = has_item(data, guild_id, uid, "lucky_charm")
    has_disguise = has_item(data, guild_id, uid, "disguise")
    success_chance = crime["success"]
    if has_charm:
        success_chance = min(0.95, success_chance + 0.20)
    success = random.random() < success_chance

    if success:
        earned = random.randint(*crime["reward"])
        set_user_points(data, guild_id, uid, get_user_points(data, guild_id, uid) + earned)
        save_data(data)
        embed = discord.Embed(
            title=f"🦹 {crime['name']} — Success",
            description=crime["success_msg"].format(earned=earned),
            color=discord.Color.green()
        )
        embed.set_footer(text=f"+{earned} points")
    else:
        lost = random.randint(*crime["fail_loss"])
        if has_disguise:
            lost = lost // 2
            remove_item_by_type(data, guild_id, uid, "disguise")
        set_user_points(data, guild_id, uid, max(0, get_user_points(data, guild_id, uid) - lost))
        save_data(data)
        embed = discord.Embed(
            title=f"🚨 {crime['name']} — Caught",
            description=crime["fail_msg"].format(lost=lost),
            color=discord.Color.red()
        )
        embed.set_footer(text=f"-{lost} points{' (Disguise reduced penalty)' if has_disguise else ''}")
    await ctx.send(embed=embed)

# ============================================================
#   HUNT
# ============================================================

HUNT_ANIMALS = [
    {"name": "Rabbit",      "emoji": "🐇", "rarity": "common",    "reward": (30, 80)},
    {"name": "Deer",        "emoji": "🦌", "rarity": "common",    "reward": (50, 120)},
    {"name": "Fox",         "emoji": "🦊", "rarity": "uncommon",  "reward": (80, 200)},
    {"name": "Wild Boar",   "emoji": "🐗", "rarity": "uncommon",  "reward": (100, 250)},
    {"name": "Bear",        "emoji": "🐻", "rarity": "rare",      "reward": (200, 500)},
    {"name": "Wolf",        "emoji": "🐺", "rarity": "rare",      "reward": (180, 450)},
    {"name": "Dragon",      "emoji": "🐉", "rarity": "legendary", "reward": (800, 2000)},
    {"name": "Nothing",     "emoji": "🌿", "rarity": "miss",      "reward": (0, 0)},
]
HUNT_WEIGHTS = [30, 25, 15, 12, 8, 7, 1, 10]  # must sum to 108 here (adjustable)
HUNT_COOLDOWN = 120

hunt_cooldowns = {}

@bot.command(name="hunt")
async def hunt_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "hunt")
    uid = str(ctx.author.id)
    now = time.time()
    if uid in hunt_cooldowns and now - hunt_cooldowns[uid] < HUNT_COOLDOWN:
        next_ts = int(hunt_cooldowns[uid] + HUNT_COOLDOWN)
        await ctx.send(f"You need to wait before hunting again. Ready <t:{next_ts}:R>.")
        return
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)

    # Check ammo
    ammo_items = [e for e in data.get("inventories", {}).get(guild_id, {}).get(uid, [])
                  if e["item_id"] == "ammo_pack"]
    if not ammo_items:
        await ctx.send("You have no ammo! Buy an **Ammo Pack** from `?shop` → Hunting.")
        return

    # Consume 1 ammo charge (each pack = 10 shots stored as count)
    inv = data["inventories"][guild_id][uid]
    for entry in inv:
        if entry["item_id"] == "ammo_pack":
            entry["shots"] = entry.get("shots", 10) - 1
            if entry["shots"] <= 0:
                inv.remove(entry)
            break

    hunt_cooldowns[uid] = now
    has_rifle = has_item(data, guild_id, uid, "hunting_rifle")

    animal = random.choices(HUNT_ANIMALS, weights=HUNT_WEIGHTS, k=1)[0]
    if animal["rarity"] == "miss":
        save_data(data)
        await ctx.send(embed=discord.Embed(
            title="🌿 You Found Nothing",
            description="You searched the woods but came back empty-handed.",
            color=discord.Color.greyple()
        ))
        return

    mn, mx = animal["reward"]
    if has_rifle:
        mx = int(mx * 1.25)
    earned = random.randint(mn, mx)
    set_user_points(data, guild_id, uid, get_user_points(data, guild_id, uid) + earned)

    # Chance to find crafting materials while hunting
    mat_text = ""
    hunt_mat_chances = [
        ("animal_hide", 0.60), ("bone_fragment", 0.35),
        ("rare_feather", 0.15 if animal["rarity"] in ("rare","legendary") else 0.05),
    ]
    for mat, chance in hunt_mat_chances:
        if random.random() < chance:
            add_material(data, guild_id, uid, mat, 1)
            mat_text += f"\n🧰 Found **{CRAFT_MATERIALS[mat]}**!"

    save_data(data)

    rarity_colours = {"common": discord.Color.green(), "uncommon": discord.Color.blue(),
                      "rare": discord.Color.purple(), "legendary": discord.Color.gold()}
    embed = discord.Embed(
        title=f"{animal['emoji']} You caught a {animal['name']}!",
        description=f"Rarity: **{animal['rarity'].title()}**\n\n+**{earned} points**{' (Rifle bonus)' if has_rifle else ''}{mat_text}",
        color=rarity_colours.get(animal["rarity"], discord.Color.green())
    )
    await ctx.send(embed=embed)

# ============================================================
#   SCRATCH CARD
# ============================================================

SCRATCH_SYMBOLS = ["🍒", "🍋", "🍊", "⭐", "💎", "🎰"]
SCRATCH_MULTIPLIERS = {
    ("💎","💎","💎"): 10,
    ("⭐","⭐","⭐"): 5,
    ("🎰","🎰","🎰"): 8,
    ("🍒","🍒","🍒"): 3,
    ("🍊","🍊","🍊"): 2.5,
    ("🍋","🍋","🍋"): 2,
}

@bot.command(name="scratch")
async def scratch_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "scratch")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    uid = str(ctx.author.id)

    if not has_item(data, guild_id, uid, "scratch_card"):
        await ctx.send("You don't have a Scratch Card! Buy one from `?shop` → Economy.")
        return

    remove_item_by_type(data, guild_id, uid, "scratch_card")
    card_cost = SHOP_ITEMS["scratch_card"]["price"]

    row1 = [random.choice(SCRATCH_SYMBOLS) for _ in range(3)]
    row2 = [random.choice(SCRATCH_SYMBOLS) for _ in range(3)]
    row3 = [random.choice(SCRATCH_SYMBOLS) for _ in range(3)]

    won = 0
    win_line = None
    for row in [row1, row2, row3]:
        key = tuple(row)
        if key in SCRATCH_MULTIPLIERS:
            mult = SCRATCH_MULTIPLIERS[key]
            won = int(card_cost * mult)
            win_line = f"{'  '.join(row)} — **{mult}x** = **{won} points**!"
            break

    if won:
        set_user_points(data, guild_id, uid, get_user_points(data, guild_id, uid) + won)
    save_data(data)

    board = (
        f"{'  '.join(row1)}\n"
        f"{'  '.join(row2)}\n"
        f"{'  '.join(row3)}"
    )
    embed = discord.Embed(
        title="🎟️ Scratch Card",
        description=board,
        color=discord.Color.gold() if won else discord.Color.greyple()
    )
    if won:
        embed.add_field(name="🎉 Winner!", value=win_line, inline=False)
    else:
        embed.add_field(name="No match", value="Better luck next time!", inline=False)
    await ctx.send(embed=embed)

# ============================================================
#   ADVENTURE (multi-step text adventure with buttons)
# ============================================================

ADVENTURE_STAGES = [
    {
        "desc": "You stand at the entrance of a dark forest. Two paths lie ahead.",
        "choices": [
            {"label": "Take the left path", "outcome": "safe",   "msg": "The left path was quiet. You found an old chest! +{r} points."},
            {"label": "Take the right path","outcome": "risky",  "msg": "The right path had a monster. You fought it off and grabbed {r} points from its hoard."},
        ]
    },
    {
        "desc": "You reach a river. A rickety bridge and a boat are your options.",
        "choices": [
            {"label": "Cross the bridge",   "outcome": "safe",   "msg": "The bridge held. A merchant rewarded your bravery with {r} points."},
            {"label": "Take the boat",      "outcome": "risky",  "msg": "The river was fast but you made it. The current swept a coin bag to you. +{r} points."},
        ]
    },
    {
        "desc": "You find an ancient temple. A guardian stands at the door.",
        "choices": [
            {"label": "Offer a gift",       "outcome": "safe",   "msg": "The guardian accepted your offering and let you through. Inside: {r} points."},
            {"label": "Sneak past",         "outcome": "risky",  "msg": "You nearly got caught but grabbed {r} points from the altar before running."},
        ]
    },
]

class AdventureView(discord.ui.View):
    def __init__(self, author_id, stage, total, guild_id, has_kit):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.stage = stage
        self.total = total
        self.guild_id = guild_id
        self.has_kit = has_kit
        stage_data = ADVENTURE_STAGES[stage]
        for choice in stage_data["choices"]:
            self.add_item(AdventureChoiceButton(choice, author_id, stage, total, guild_id, has_kit))

class AdventureChoiceButton(discord.ui.Button):
    def __init__(self, choice, author_id, stage, total, guild_id, has_kit):
        super().__init__(label=choice["label"], style=discord.ButtonStyle.primary)
        self.choice = choice
        self.author_id = author_id
        self.stage = stage
        self.total = total
        self.guild_id = guild_id
        self.has_kit = has_kit

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This is not your adventure.", ephemeral=True)
            return

        is_risky = self.choice["outcome"] == "risky"
        if is_risky:
            success = random.random() < (0.65 if self.has_kit else 0.55)
            if not success:
                # Failed risky choice — adventure ends
                embed = discord.Embed(
                    title="💀 Adventure Over",
                    description=f"You made a risky move and it cost you. The adventure ends here.\n\nTotal earned: **{self.total} points**",
                    color=discord.Color.red()
                )
                data = load_data()
                data = ensure_keys(data)
                uid = str(interaction.user.id)
                set_user_points(data, self.guild_id, uid, get_user_points(data, self.guild_id, uid) + self.total)
                save_data(data)
                await interaction.response.edit_message(embed=embed, view=None)
                return

        reward = random.randint(80, 250) if not is_risky else random.randint(150, 400)
        new_total = self.total + reward
        msg = self.choice["msg"].format(r=reward)
        next_stage = self.stage + 1

        if next_stage >= len(ADVENTURE_STAGES):
            # Adventure complete
            bonus = 200 if self.has_kit else 0
            final = new_total + bonus
            data = load_data()
            data = ensure_keys(data)
            uid = str(interaction.user.id)
            set_user_points(data, self.guild_id, uid, get_user_points(data, self.guild_id, uid) + final)
            save_data(data)
            embed = discord.Embed(
                title="🏆 Adventure Complete!",
                description=(
                    f"{msg}\n\n"
                    f"You made it through all three stages!\n"
                    f"{'Adventure Kit bonus: +200 points!\n' if bonus else ''}"
                    f"**Total earned: {final} points**"
                ),
                color=discord.Color.gold()
            )
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            next_data = ADVENTURE_STAGES[next_stage]
            embed = discord.Embed(
                title=f"🗺️ Adventure — Stage {next_stage + 1}/{len(ADVENTURE_STAGES)}",
                description=f"{msg}\n\nRunning total: **{new_total} points**\n\n---\n{next_data['desc']}",
                color=discord.Color.blue()
            )
            view = AdventureView(self.author_id, next_stage, new_total, self.guild_id, self.has_kit)
            await interaction.response.edit_message(embed=embed, view=view)

adventure_cooldowns = {}
ADVENTURE_COOLDOWN = 3600

@bot.command(name="adventure")
async def adventure_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "adventure")
    uid = str(ctx.author.id)
    now = time.time()
    if uid in adventure_cooldowns and now - adventure_cooldowns[uid] < ADVENTURE_COOLDOWN:
        next_ts = int(adventure_cooldowns[uid] + ADVENTURE_COOLDOWN)
        await ctx.send(f"You need to rest after your last adventure. Ready <t:{next_ts}:R>.")
        return
    adventure_cooldowns[uid] = now
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    has_kit = has_item(data, guild_id, uid, "adventure_kit")
    if has_kit:
        remove_item_by_type(data, guild_id, uid, "adventure_kit")
        save_data(data)

    stage_data = ADVENTURE_STAGES[0]
    embed = discord.Embed(
        title=f"🗺️ Adventure — Stage 1/{len(ADVENTURE_STAGES)}",
        description=f"{stage_data['desc']}{'\n\n*Adventure Kit equipped — bonus life active!*' if has_kit else ''}",
        color=discord.Color.blue()
    )
    view = AdventureView(ctx.author.id, 0, 0, guild_id, has_kit)
    await ctx.send(embed=embed, view=view)

# ============================================================
#   FISHING SYSTEM
# ============================================================

FISH_TYPES = [
    {"name": "Old Boot",       "emoji": "👟", "rarity": "junk",      "value": 0,    "weight": 20},
    {"name": "Sardine",        "emoji": "🐟", "rarity": "common",    "value": 15,   "weight": 25},
    {"name": "Carp",           "emoji": "🐠", "rarity": "common",    "value": 20,   "weight": 20},
    {"name": "Bass",           "emoji": "🐡", "rarity": "uncommon",  "value": 45,   "weight": 15},
    {"name": "Trout",          "emoji": "🎣", "rarity": "uncommon",  "value": 60,   "weight": 10},
    {"name": "Salmon",         "emoji": "🍣", "rarity": "rare",      "value": 120,  "weight": 6},
    {"name": "Tuna",           "emoji": "🐟", "rarity": "rare",      "value": 180,  "weight": 3},
    {"name": "Swordfish",      "emoji": "🗡️", "rarity": "epic",      "value": 400,  "weight": 1},
]

FISH_LOCATIONS = {
    "Wily River":    {"desc": "A gentle river with small common fish.",          "fish_types": ["junk","common"]},
    "Crystal Lake":  {"desc": "A calm lake. Good for uncommon catches.",         "fish_types": ["common","uncommon"]},
    "Deep Ocean":    {"desc": "Rough waters. High risk, high reward.",           "fish_types": ["uncommon","rare","epic"]},
    "Secret Cove":   {"desc": "Hidden spot. Rare fish lurk here.",              "fish_types": ["rare","epic"]},
}

FISH_COOLDOWN = 90

fish_cooldowns = {}

def get_fish_for_location(location_name, has_bait):
    loc = FISH_LOCATIONS[location_name]
    allowed = loc["fish_types"]
    pool = [f for f in FISH_TYPES if f["rarity"] in allowed]
    if has_bait and "junk" in allowed:
        pool = [f for f in pool if f["rarity"] != "junk"]
    weights = [f["weight"] for f in pool]
    return random.choices(pool, weights=weights, k=1)[0]

class FishLocationView(discord.ui.View):
    def __init__(self, author_id, guild_id, has_rod, has_bait):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.guild_id = guild_id
        self.has_rod = has_rod
        self.has_bait = has_bait
        for loc in FISH_LOCATIONS:
            self.add_item(FishLocationButton(loc, author_id, guild_id, has_rod, has_bait))

class FishLocationButton(discord.ui.Button):
    def __init__(self, location, author_id, guild_id, has_rod, has_bait):
        super().__init__(label=location, style=discord.ButtonStyle.secondary)
        self.location = location
        self.author_id = author_id
        self.guild_id = guild_id
        self.has_rod = has_rod
        self.has_bait = has_bait

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This is not your fishing session.", ephemeral=True)
            return

        uid = str(interaction.user.id)
        now = time.time()
        fish_cooldowns[uid] = now

        data = load_data()
        data = ensure_keys(data)

        # Use bait if available
        if self.has_bait:
            inv = data["inventories"].get(self.guild_id, {}).get(uid, [])
            for entry in inv:
                if entry["item_id"] == "bait":
                    entry["uses"] = entry.get("uses", 5) - 1
                    if entry["uses"] <= 0:
                        inv.remove(entry)
                    break

        fish = get_fish_for_location(self.location, self.has_bait)
        loc_info = FISH_LOCATIONS[self.location]

        if fish["rarity"] == "junk":
            embed = discord.Embed(
                title=f"🎣 Fishing at {self.location}",
                description=f"You caught... {fish['emoji']} **{fish['name']}**. Threw it back.",
                color=discord.Color.greyple()
            )
        else:
            rod_bonus = 1.15 if self.has_rod else 1.0
            value = int(fish["value"] * rod_bonus)

            # Add to fish bucket if player has one
            has_bucket = has_item(data, self.guild_id, uid, "fish_bucket")
            fish_key = f"{fish['name'].lower().replace(' ','_')}"
            if has_bucket:
                bucket = data.setdefault("fish_buckets", {}).setdefault(self.guild_id, {}).setdefault(uid, {})
                bucket[fish_key] = bucket.get(fish_key, {"name": fish["name"], "emoji": fish["emoji"], "value": fish["value"], "count": 0})
                bucket[fish_key]["count"] += 1

            set_user_points(data, self.guild_id, uid, get_user_points(data, self.guild_id, uid) + value)
            rarity_colours = {"common": discord.Color.green(), "uncommon": discord.Color.blue(),
                              "rare": discord.Color.purple(), "epic": discord.Color.gold()}
            embed = discord.Embed(
                title=f"🎣 Fishing at {self.location}",
                description=(
                    f"You caught {fish['emoji']} **{fish['name']}**!\n"
                    f"Rarity: **{fish['rarity'].title()}**\n"
                    f"Value: **+{value} points**{' (Rod bonus)' if self.has_rod else ''}\n"
                    f"{'Stored in fish bucket.' if has_bucket else 'Sold immediately.'}"
                ),
                color=rarity_colours.get(fish["rarity"], discord.Color.green())
            )

        save_data(data)
        await interaction.response.edit_message(embed=embed, view=None)

@bot.command(name="fish")
async def fish_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "fish")
    uid = str(ctx.author.id)
    now = time.time()
    if uid in fish_cooldowns and now - fish_cooldowns[uid] < FISH_COOLDOWN:
        next_ts = int(fish_cooldowns[uid] + FISH_COOLDOWN)
        await ctx.send(f"Your line is still in the water. Fish again <t:{next_ts}:R>.")
        return

    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    has_rod  = has_item(data, guild_id, uid, "fishing_rod")
    has_bait = has_item(data, guild_id, uid, "bait")

    embed = discord.Embed(
        title="🎣 Go Fishing",
        description=(
            f"**Equipment:** {'🎣 Fishing Rod' if has_rod else '🤲 Bare Hands (buy a rod for better catches)'}\n"
            f"**Bait:** {'✅ Yes (no junk catches)' if has_bait else '❌ None (junk possible)'}\n\n"
            f"Choose your fishing location below:"
        ),
        color=discord.Color.blue()
    )
    view = FishLocationView(ctx.author.id, guild_id, has_rod, has_bait)
    await ctx.send(embed=embed, view=view)

@bot.command(name="fishbucket", aliases=["bucket"])
async def fishbucket_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "fishbucket")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    uid = str(ctx.author.id)
    bucket = data.get("fish_buckets", {}).get(guild_id, {}).get(uid, {})
    if not bucket:
        await ctx.send("Your fish bucket is empty. Go fishing with `?fish`!")
        return
    embed = discord.Embed(title="🪣 Your Fish Bucket", color=discord.Color.blue())
    total_value = 0
    for fish_key, fish_data in bucket.items():
        count = fish_data["count"]
        val = fish_data["value"] * count
        total_value += val
        embed.add_field(
            name=f"{fish_data['emoji']} {fish_data['name']} ×{count}",
            value=f"Worth {val} points",
            inline=True
        )
    embed.set_footer(text=f"Total bucket value: {total_value} points — use ?fishsell to sell all")
    await ctx.send(embed=embed)

@bot.command(name="fishsell")
async def fishsell_cmd(ctx):
    await log_command(ctx.guild, ctx.author, "fishsell")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    uid = str(ctx.author.id)
    bucket = data.get("fish_buckets", {}).get(guild_id, {}).get(uid, {})
    if not bucket:
        await ctx.send("Your fish bucket is empty.")
        return
    total = sum(f["value"] * f["count"] for f in bucket.values())
    data["fish_buckets"][guild_id][uid] = {}
    set_user_points(data, guild_id, uid, get_user_points(data, guild_id, uid) + total)
    save_data(data)
    await ctx.send(embed=discord.Embed(
        title="🐟 Fish Sold!",
        description=f"You sold all your fish for **{total} points**!",
        color=discord.Color.green()
    ))


# ============================================================
#   POLLS
# ============================================================

@bot.command(name="poll")
@mod_only()
async def poll_cmd(ctx, *, args: str = None):
    """
    ?poll [question]              — yes/no poll
    ?poll [question] | opt1 | opt2 ... — multi-choice poll (up to 9 options)
    """
    await log_command(ctx.guild, ctx.author, "poll", args or "")
    if not args:
        await ctx.send("Usage: `?poll What is your favourite colour?` or `?poll Question | Option 1 | Option 2`")
        return

    parts = [p.strip() for p in args.split("|")]
    question = parts[0]
    options  = parts[1:] if len(parts) > 1 else []

    if len(options) > 9:
        await ctx.send("You can have a maximum of 9 options.")
        return

    if not options:
        # Simple yes/no poll
        embed = discord.Embed(
            title="📊 Poll",
            description=question,
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Poll by {ctx.author.display_name}")
        try:
            await ctx.message.delete()
        except Exception:
            pass
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        await msg.add_reaction("🤷")
    else:
        NUMBER_EMOJIS = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
        desc = question + "\n\n"
        for i, opt in enumerate(options):
            desc += f"{NUMBER_EMOJIS[i]} {opt}\n"
        embed = discord.Embed(
            title="📊 Poll",
            description=desc,
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Poll by {ctx.author.display_name}")
        try:
            await ctx.message.delete()
        except Exception:
            pass
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            await msg.add_reaction(NUMBER_EMOJIS[i])


# ============================================================
#   COUNTING GAME
# ============================================================

COUNTING_CHANNEL = "counting"
# In-memory state — also persisted to data.json under "counting"
# Structure: data["counting"][guild_id] = {
#   "current": int, "last_user": str, "high_score": int, "scores": {user_id: int}
# }

def get_counting(data, guild_id):
    if "counting" not in data:
        data["counting"] = {}
    if guild_id not in data["counting"]:
        data["counting"][guild_id] = {"current": 0, "last_user": None, "high_score": 0, "scores": {}}
    return data["counting"][guild_id]

# Counting is handled inside on_message — we patch it in below via a flag
_COUNTING_HANDLER_REGISTERED = True  # marker so we know it's built-in to on_message

@bot.command(name="countingtop")
async def countingtop_cmd(ctx):
    """Show the counting high score and top contributors."""
    await log_command(ctx.guild, ctx.author, "countingtop")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    counting = get_counting(data, guild_id)
    scores = counting.get("scores", {})
    high_score = counting.get("high_score", 0)
    current = counting.get("current", 0)

    embed = discord.Embed(title="🔢 Counting Leaderboard", color=discord.Color.gold())
    embed.add_field(name="Current Count", value=str(current), inline=True)
    embed.add_field(name="All-Time High", value=str(high_score), inline=True)

    if scores:
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        desc = ""
        for rank, (uid, count) in enumerate(sorted_scores, 1):
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"
            medal = medals.get(rank, f"**{rank}.**")
            desc += f"{medal} {name} — **{count}** numbers counted\n"
        embed.add_field(name="Top Counters", value=desc, inline=False)
    else:
        embed.add_field(name="Top Counters", value="No one has counted yet!", inline=False)

    await ctx.send(embed=embed)

@bot.command(name="countingreset")
@mod_only()
async def countingreset_cmd(ctx):
    """Mod only — reset the counting channel back to 0."""
    await log_command(ctx.guild, ctx.author, "countingreset")
    data = load_data()
    data = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    counting = get_counting(data, guild_id)
    counting["current"] = 0
    counting["last_user"] = None
    save_data(data)
    await ctx.send("🔢 Counting has been reset to **0**. Start from 1!")


# ============================================================
#   8BALL
# ============================================================

EIGHTBALL_RESPONSES = [
    # Positive
    ("It is certain.", discord.Color.green()),
    ("Without a doubt.", discord.Color.green()),
    ("Yes, definitely.", discord.Color.green()),
    ("You may rely on it.", discord.Color.green()),
    ("As I see it, yes.", discord.Color.green()),
    ("Most likely.", discord.Color.green()),
    ("Outlook good.", discord.Color.green()),
    ("Signs point to yes.", discord.Color.green()),
    # Neutral
    ("Reply hazy, try again.", discord.Color.gold()),
    ("Ask again later.", discord.Color.gold()),
    ("Better not tell you now.", discord.Color.gold()),
    ("Cannot predict now.", discord.Color.gold()),
    ("Concentrate and ask again.", discord.Color.gold()),
    # Negative
    ("Don't count on it.", discord.Color.red()),
    ("My reply is no.", discord.Color.red()),
    ("My sources say no.", discord.Color.red()),
    ("Outlook not so good.", discord.Color.red()),
    ("Very doubtful.", discord.Color.red()),
]

@bot.command(name="8ball", aliases=["eightball"])
async def eightball_cmd(ctx, *, question: str = None):
    await log_command(ctx.guild, ctx.author, "8ball", question or "")
    if not question:
        await ctx.send("Ask me a question! e.g. `?8ball Will I win today?`")
        return
    response, color = random.choice(EIGHTBALL_RESPONSES)
    embed = discord.Embed(color=color)
    embed.add_field(name="🎱 Question", value=question, inline=False)
    embed.add_field(name="Answer", value=f"**{response}**", inline=False)
    embed.set_footer(text=f"Asked by {ctx.author.display_name}")
    await ctx.send(embed=embed)


# ============================================================
#   COINFLIP
# ============================================================

coinflip_pending = {}  # guild_id: {challenger_id, challenged_id, amount, message_id}
COINFLIP_TIMEOUT = 60  # seconds for challenged user to accept

class CoinflipChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, challenged: discord.Member, amount: int, guild_id: str):
        super().__init__(timeout=COINFLIP_TIMEOUT)
        self.challenger = challenger
        self.challenged = challenged
        self.amount = amount
        self.guild_id = guild_id
        self.resolved = False

    async def _resolve(self, interaction: discord.Interaction, accepted: bool):
        if self.resolved:
            return
        self.resolved = True
        self.stop()

        if not accepted:
            await interaction.response.edit_message(
                content=f"❌ {self.challenged.mention} declined the coinflip challenge.",
                embed=None, view=None
            )
            return

        # Both agreed — flip the coin (truly random, 50/50)
        result = random.choice(["heads", "tails"])
        winner_choice = random.choice(["heads", "tails"])  # challenger picks randomly (bot decides)
        challenger_wins = (winner_choice == result)
        winner = self.challenger if challenger_wins else self.challenged
        loser  = self.challenged if challenger_wins else self.challenger

        data = load_data()
        data = ensure_keys(data)
        uid_w = str(winner.id)
        uid_l = str(loser.id)

        winner_pts = get_user_points(data, self.guild_id, uid_w)
        loser_pts  = get_user_points(data, self.guild_id, uid_l)
        actual_amount = min(self.amount, loser_pts)  # can't lose more than you have

        set_user_points(data, self.guild_id, uid_w, winner_pts + actual_amount)
        set_user_points(data, self.guild_id, uid_l, loser_pts  - actual_amount)
        save_data(data)

        coin_emoji = "🪙 HEADS" if result == "heads" else "🪙 TAILS"
        embed = discord.Embed(
            title=f"🪙 Coinflip Result — {coin_emoji}",
            description=(
                f"The coin landed on **{result.upper()}**!\n\n"
                f"🏆 **{winner.display_name}** wins **{actual_amount} points**!\n"
                f"💸 {loser.display_name} loses {actual_amount} points."
            ),
            color=discord.Color.gold()
        )
        await interaction.response.edit_message(content=None, embed=embed, view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message("This challenge isn't for you!", ephemeral=True)
            return
        await self._resolve(interaction, accepted=True)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message("This challenge isn't for you!", ephemeral=True)
            return
        await self._resolve(interaction, accepted=False)

    async def on_timeout(self):
        self.resolved = True
        # Edit the message to show it expired if we can find it
        # (interaction reference not stored, so we just mark resolved)


@bot.command(name="coinflip", aliases=["cf"])
async def coinflip_cmd(ctx, target: discord.Member = None, amount: int = None):
    """
    ?coinflip [amount]          — flip vs the bot
    ?coinflip @user [amount]    — challenge another member
    """
    await log_command(ctx.guild, ctx.author, "coinflip")
    guild_id = str(ctx.guild.id)
    uid = str(ctx.author.id)

    # vs bot
    if target is None or target.bot:
        if amount is None or amount <= 0:
            await ctx.send("Specify an amount! e.g. `?coinflip 100` or `?coinflip @user 100`")
            return
        data = load_data()
        data = ensure_keys(data)
        pts = get_user_points(data, guild_id, uid)
        if pts < amount:
            await ctx.send(f"You only have **{pts} points**. You can't bet more than you have.")
            return

        # Truly random — bot picks heads or tails randomly, then coin flips randomly
        bot_choice = random.choice(["heads", "tails"])
        result     = random.choice(["heads", "tails"])
        user_wins  = (bot_choice != result)  # user wins if bot guessed wrong

        if user_wins:
            set_user_points(data, guild_id, uid, pts + amount)
            outcome_text = f"The coin landed on **{result.upper()}** — the bot guessed wrong!\n🏆 You win **{amount} points**!"
            color = discord.Color.green()
        else:
            set_user_points(data, guild_id, uid, pts - amount)
            outcome_text = f"The coin landed on **{result.upper()}** — the bot guessed right!\n💸 You lose **{amount} points**."
            color = discord.Color.red()
        save_data(data)

        embed = discord.Embed(
            title="🪙 Coinflip vs Bot",
            description=outcome_text,
            color=color
        )
        embed.set_footer(text=f"Balance: {get_user_points(data, guild_id, uid)} points")
        await ctx.send(embed=embed)
        return

    # vs user
    if target.id == ctx.author.id:
        await ctx.send("You can't challenge yourself!")
        return
    if amount is None or amount <= 0:
        await ctx.send("Specify an amount! e.g. `?coinflip @user 100`")
        return

    data = load_data()
    data = ensure_keys(data)
    challenger_pts  = get_user_points(data, guild_id, uid)
    challenged_pts  = get_user_points(data, guild_id, str(target.id))

    if challenger_pts < amount:
        await ctx.send(f"You only have **{challenger_pts} points**.")
        return
    if challenged_pts < amount:
        await ctx.send(f"{target.display_name} only has **{challenged_pts} points** and can't cover the bet.")
        return

    embed = discord.Embed(
        title="🪙 Coinflip Challenge!",
        description=(
            f"{ctx.author.mention} is challenging {target.mention} to a coinflip!\n\n"
            f"**Bet:** {amount} points\n\n"
            f"{target.mention}, do you accept? You have {COINFLIP_TIMEOUT} seconds."
        ),
        color=discord.Color.gold()
    )
    view = CoinflipChallengeView(ctx.author, target, amount, guild_id)
    await ctx.send(embed=embed, view=view)


# ============================================================
#   GIVEAWAY  (Managers + Ahmed/Vexon only)
# ============================================================

GIVEAWAY_EMOJI = "🎉"
active_giveaways = {}  # message_id -> {guild_id, channel_id, prize, end_time, winners}

def is_giveaway_host(member: discord.Member) -> bool:
    """Only Managers and Ahmed (Vexon) can host giveaways."""
    allowed = {"Managers", "Ahmed"}
    return (
        any(r.name in allowed for r in member.roles)
        or member.guild_permissions.administrator
    )

@bot.command(name="giveaway")
async def giveaway_cmd(ctx, duration: str = None, winners: str = None, *, prize: str = None):
    """
    ?giveaway [duration] [winners] [prize]
    Duration: 30s, 5m, 2h, 1d
    Winners: 1w, 2w etc.
    Example: ?giveaway 1h 1w Nitro Classic
    """
    await log_command(ctx.guild, ctx.author, "giveaway", f"{duration} {winners} {prize}")

    if not is_giveaway_host(ctx.author):
        await ctx.send("Only **Managers** and **Ahmed** can start giveaways.")
        return

    if not duration or not winners or not prize:
        await ctx.send(
            "Usage: `?giveaway [duration] [winners] [prize]`\n"
            "Example: `?giveaway 1h 1w Free Nitro`\n"
            "Duration: `30s` `5m` `2h` `1d` | Winners: `1w` `2w` etc."
        )
        return

    # Parse duration
    time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    try:
        unit = duration[-1].lower()
        value = int(duration[:-1])
        if unit not in time_units or value <= 0:
            raise ValueError
        seconds = value * time_units[unit]
    except (ValueError, IndexError):
        await ctx.send("Invalid duration. Use `30s`, `5m`, `2h`, `1d`, etc.")
        return

    if seconds < 10:
        await ctx.send("Minimum duration is 10 seconds.")
        return
    if seconds > 7 * 86400:
        await ctx.send("Maximum duration is 7 days.")
        return

    # Parse winner count
    try:
        winner_count = int(winners.rstrip("w").rstrip("W"))
        if winner_count < 1 or winner_count > 20:
            raise ValueError
    except (ValueError, AttributeError):
        await ctx.send("Invalid winner count. Use `1w`, `2w`, etc.")
        return

    end_time = int(time.time()) + seconds
    end_display = f"<t:{end_time}:R>"

    embed = discord.Embed(
        title=f"🎉 GIVEAWAY — {prize}",
        description=(
            f"React with {GIVEAWAY_EMOJI} to enter!\n\n"
            f"**Ends:** {end_display}\n"
            f"**Winners:** {winner_count}\n"
            f"**Hosted by:** {ctx.author.mention}"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Ends at")
    embed.timestamp = discord.utils.utcnow() + timedelta(seconds=seconds)

    msg = await ctx.send(embed=embed)
    await msg.add_reaction(GIVEAWAY_EMOJI)

    active_giveaways[str(msg.id)] = {
        "guild_id":    str(ctx.guild.id),
        "channel_id":  str(ctx.channel.id),
        "prize":       prize,
        "end_time":    end_time,
        "winner_count": winner_count,
        "host_id":     str(ctx.author.id),
        "message_id":  str(msg.id),
    }

    # Schedule the end
    asyncio.create_task(_end_giveaway_after(msg.id, ctx.channel.id, ctx.guild.id, seconds, prize, winner_count, ctx.author))

async def _end_giveaway_after(msg_id, channel_id, guild_id, seconds, prize, winner_count, host):
    await asyncio.sleep(seconds)
    guild   = bot.get_guild(guild_id)
    if not guild:
        return
    channel = guild.get_channel(channel_id)
    if not channel:
        return
    try:
        msg = await channel.fetch_message(msg_id)
    except Exception:
        return

    # Collect entrants (exclude the bot)
    entrants = []
    for reaction in msg.reactions:
        if str(reaction.emoji) == GIVEAWAY_EMOJI:
            async for user in reaction.users():
                if not user.bot:
                    entrants.append(user)
            break

    active_giveaways.pop(str(msg_id), None)

    if not entrants:
        await channel.send(f"🎉 The giveaway for **{prize}** ended but nobody entered. 😢")
        return

    actual_winners = random.sample(entrants, min(winner_count, len(entrants)))
    winner_mentions = ", ".join(w.mention for w in actual_winners)

    # Edit original embed
    embed = discord.Embed(
        title=f"🎉 GIVEAWAY ENDED — {prize}",
        description=(
            f"**Winner(s):** {winner_mentions}\n"
            f"**Hosted by:** {host.mention}"
        ),
        color=discord.Color.greyple()
    )
    await msg.edit(embed=embed)
    await channel.send(
        f"🎉 Congratulations {winner_mentions}! You won **{prize}**!\n"
        f"Contact {host.mention} to claim your prize."
    )

@bot.command(name="reroll")
async def reroll_cmd(ctx, message_id: str = None):
    """Reroll a giveaway winner. Managers + Ahmed only."""
    if not is_giveaway_host(ctx.author):
        await ctx.send("Only **Managers** and **Ahmed** can reroll giveaways.")
        return
    if not message_id:
        await ctx.send("Provide the message ID of the giveaway. `?reroll [message_id]`")
        return
    try:
        msg = await ctx.channel.fetch_message(int(message_id))
    except Exception:
        await ctx.send("Couldn't find that message in this channel.")
        return

    entrants = []
    for reaction in msg.reactions:
        if str(reaction.emoji) == GIVEAWAY_EMOJI:
            async for user in reaction.users():
                if not user.bot:
                    entrants.append(user)
            break

    if not entrants:
        await ctx.send("No valid entrants found.")
        return

    new_winner = random.choice(entrants)
    await ctx.send(f"🎉 The new winner is {new_winner.mention}! Congratulations!")


# ============================================================
#   UNIQUE: DUEL  (1v1 RPS for points)
# ============================================================

class DuelView(discord.ui.View):
    """Challenger picks, then challenged picks — result revealed simultaneously."""
    MOVES = {"🪨": "rock", "📄": "paper", "✂️": "scissors"}
    BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

    def __init__(self, challenger: discord.Member, challenged: discord.Member, amount: int, guild_id: str):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.challenged = challenged
        self.amount     = amount
        self.guild_id   = guild_id
        self.picks      = {}   # user_id -> move string

    async def _pick(self, interaction: discord.Interaction, move: str):
        uid = interaction.user.id
        if uid not in (self.challenger.id, self.challenged.id):
            await interaction.response.send_message("You're not in this duel!", ephemeral=True)
            return
        if uid in self.picks:
            await interaction.response.send_message("You already picked!", ephemeral=True)
            return
        self.picks[uid] = move
        await interaction.response.send_message(f"You chose **{move}**! Waiting for the other player…", ephemeral=True)

        if len(self.picks) == 2:
            await self._resolve(interaction)

    async def _resolve(self, interaction: discord.Interaction):
        self.stop()
        c_move = self.picks[self.challenger.id]
        d_move = self.picks[self.challenged.id]

        if c_move == d_move:
            result = "It's a tie! No points exchanged."
            color  = discord.Color.gold()
            winner = loser = None
        elif self.BEATS[c_move] == d_move:
            winner, loser = self.challenger, self.challenged
            result = f"🏆 **{self.challenger.display_name}** wins **{self.amount} points**!"
            color  = discord.Color.green()
        else:
            winner, loser = self.challenged, self.challenger
            result = f"🏆 **{self.challenged.display_name}** wins **{self.amount} points**!"
            color  = discord.Color.green()

        if winner and loser:
            data = load_data()
            data = ensure_keys(data)
            wid, lid = str(winner.id), str(loser.id)
            loser_pts = get_user_points(data, self.guild_id, lid)
            actual = min(self.amount, loser_pts)
            set_user_points(data, self.guild_id, wid, get_user_points(data, self.guild_id, wid) + actual)
            set_user_points(data, self.guild_id, lid, loser_pts - actual)
            save_data(data)

        embed = discord.Embed(
            title="⚔️ Duel Result",
            description=(
                f"{self.challenger.mention} chose **{c_move}**\n"
                f"{self.challenged.mention} chose **{d_move}**\n\n"
                f"{result}"
            ),
            color=color
        )
        await interaction.message.edit(embed=embed, view=None)

    async def on_timeout(self):
        self.stop()
        # If only one or neither player picked, no points are exchanged

    @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.secondary)
    async def rock_btn(self, interaction, button): await self._pick(interaction, "rock")
    @discord.ui.button(emoji="📄", style=discord.ButtonStyle.secondary)
    async def paper_btn(self, interaction, button): await self._pick(interaction, "paper")
    @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.secondary)
    async def scissors_btn(self, interaction, button): await self._pick(interaction, "scissors")


@bot.command(name="duel")
async def duel_cmd(ctx, target: discord.Member = None, amount: int = None):
    """Challenge another member to an RPS duel for points."""
    await log_command(ctx.guild, ctx.author, "duel")
    if not target or target.bot or target.id == ctx.author.id:
        await ctx.send("Challenge a real member! e.g. `?duel @user 100`")
        return
    if not amount or amount <= 0:
        await ctx.send("Specify a bet amount! e.g. `?duel @user 100`")
        return

    guild_id = str(ctx.guild.id)
    data = load_data()
    data = ensure_keys(data)

    c_pts = get_user_points(data, guild_id, str(ctx.author.id))
    d_pts = get_user_points(data, guild_id, str(target.id))

    if c_pts < amount:
        await ctx.send(f"You only have **{c_pts} points**.")
        return
    if d_pts < amount:
        await ctx.send(f"{target.display_name} only has **{d_pts} points** and can't cover the bet.")
        return

    embed = discord.Embed(
        title="⚔️ RPS Duel Challenge!",
        description=(
            f"{ctx.author.mention} challenges {target.mention} to a duel!\n\n"
            f"**Bet:** {amount} points\n\n"
            f"Both players — pick your move using the buttons below!\n"
            f"*Your pick is hidden until both have chosen.*"
        ),
        color=discord.Color.orange()
    )
    view = DuelView(ctx.author, target, amount, guild_id)
    await ctx.send(embed=embed, view=view)


# ============================================================
#   UNIQUE: HOTDROP  (random point drop for first claimer)
# ============================================================

hotdrop_active = {}  # guild_id -> message_id

@bot.command(name="hotdrop")
@mod_only()
async def hotdrop_cmd(ctx, amount: int = None):
    """
    Mod drops a random point prize — first member to claim it wins!
    ?hotdrop [amount]
    """
    await log_command(ctx.guild, ctx.author, "hotdrop", str(amount or ""))
    guild_id = str(ctx.guild.id)

    if guild_id in hotdrop_active:
        await ctx.send("There's already an active hotdrop! Let someone claim it first.")
        return
    if not amount or amount <= 0:
        await ctx.send("Specify an amount! e.g. `?hotdrop 500`")
        return

    embed = discord.Embed(
        title="💰 HOT DROP!",
        description=(
            f"**{amount} points** have been dropped!\n\n"
            f"Click the button below to claim them!\n"
            f"*First person to click wins — no double dipping!*"
        ),
        color=discord.Color.gold()
    )

    class HotdropView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=120)
            self.claimed = False

        @discord.ui.button(label=f"💰 Claim {amount} Points!", style=discord.ButtonStyle.green)
        async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.claimed:
                await interaction.response.send_message("Already claimed!", ephemeral=True)
                return
            if interaction.user.bot:
                return
            self.claimed = True
            self.stop()
            hotdrop_active.pop(guild_id, None)

            data = load_data()
            data = ensure_keys(data)
            uid = str(interaction.user.id)
            set_user_points(data, guild_id, uid, get_user_points(data, guild_id, uid) + amount)
            save_data(data)

            win_embed = discord.Embed(
                title="💰 Hot Drop Claimed!",
                description=f"🏃 {interaction.user.mention} was fastest and claimed **{amount} points**!",
                color=discord.Color.green()
            )
            button.disabled = True
            button.label = f"Claimed by {interaction.user.display_name}"
            await interaction.response.edit_message(embed=win_embed, view=self)

        async def on_timeout(self):
            hotdrop_active.pop(guild_id, None)

    view = HotdropView()
    msg = await ctx.send(embed=embed, view=view)
    hotdrop_active[guild_id] = str(msg.id)


# ============================================================
#   ROLEINFO — Vexon (Ahmed) only, not in ?help
# ============================================================

# Human-readable names for every Discord permission field
PERM_LABELS = {
    "administrator":              "Administrator",
    "manage_guild":               "Manage Server",
    "manage_roles":               "Manage Roles",
    "manage_channels":            "Manage Channels",
    "manage_messages":            "Manage Messages",
    "manage_threads":             "Manage Threads & Posts",
    "manage_webhooks":            "Manage Webhooks",
    "manage_emojis_and_stickers": "Manage Expressions (Emojis/Stickers)",
    "manage_events":              "Manage Events",
    "manage_nicknames":           "Manage Nicknames",
    "kick_members":               "Kick Members",
    "ban_members":                "Ban Members",
    "moderate_members":           "Timeout Members",
    "deafen_members":             "Deafen Members",
    "move_members":               "Move Members",
    "mute_members":               "Mute Members (Voice)",
    "view_audit_log":             "View Audit Log",
    "view_guild_insights":        "View Server Insights",
    "view_channel":               "View Channels",
    "send_messages":              "Send Messages",
    "send_messages_in_threads":   "Send Messages in Threads",
    "create_public_threads":      "Create Public Threads",
    "create_private_threads":     "Create Private Threads",
    "embed_links":                "Embed Links",
    "attach_files":               "Attach Files",
    "add_reactions":              "Add Reactions",
    "use_external_emojis":        "Use External Emojis",
    "use_external_stickers":      "Use External Stickers",
    "mention_everyone":           "Mention @everyone / @here",
    "read_message_history":       "Read Message History",
    "send_tts_messages":          "Send TTS Messages",
    "use_slash_commands":         "Use Application Commands",
    "request_to_speak":           "Request to Speak (Stage)",
    "connect":                    "Connect (Voice)",
    "speak":                      "Speak (Voice)",
    "stream":                     "Video / Stream",
    "use_voice_activation":       "Use Voice Activity",
    "priority_speaker":           "Priority Speaker",
    "use_external_sounds":        "Use External Sounds",
    "use_soundboard":             "Use Soundboard",
    "create_events":              "Create Events",
    "change_nickname":            "Change Own Nickname",
    "use_embedded_activities":    "Use Activities",
    "use_external_apps":          "Use External Apps",
    "bypass_slowmode":            "Bypass Slowmode",
}

# Permissions so common that showing them adds no useful info
# (every meaningful role has these, so they are noise)
PERM_SKIP = {
    "view_channel",
    "send_messages",
    "read_message_history",
    "add_reactions",
    "use_external_emojis",
    "use_external_stickers",
    "use_slash_commands",
    "connect",
    "speak",
    "stream",
    "use_voice_activation",
    "use_external_sounds",
    "use_embedded_activities",
    "use_external_apps",
    "change_nickname",
    "embed_links",
}

def get_role_notable_perms(role: discord.Role, everyone_role: discord.Role) -> dict:
    """
    Return a dict of permission_name -> True/False for permissions that:
      1. Are DIFFERENT from the @everyone baseline, OR
      2. Are explicitly set to True on this role (regardless of @everyone)
    We filter out the very common ones (PERM_SKIP) to keep output clean.
    """
    notable = {}
    everyone_perms = dict(everyone_role.permissions)
    role_perms     = dict(role.permissions)

    for perm_name, role_value in role_perms.items():
        if perm_name in PERM_SKIP:
            continue
        everyone_value = everyone_perms.get(perm_name, False)
        # Include if: role explicitly grants it (True), or it differs from @everyone
        if role_value or role_value != everyone_value:
            notable[perm_name] = role_value

    return notable


@bot.command(name="roleinfo")
async def roleinfo_cmd(ctx):
    """
    Scans every role in the server and posts a formatted breakdown
    showing what permissions each role grants (or denies).
    Only Ahmed (Vexon) can use this. Not listed in ?help.
    """
    # Only the Ahmed role (Vexon) can run this
    if not any(r.name == "Ahmed" for r in ctx.author.roles) and not ctx.author.guild_permissions.administrator:
        await ctx.send("Only **Ahmed** can use this command.", delete_after=5)
        return

    guild = ctx.guild
    everyone_role = guild.default_role

    # Sort roles by position (highest first, skip @everyone and bot-managed roles)
    roles_to_show = [
        r for r in sorted(guild.roles, key=lambda x: x.position, reverse=True)
        if not r.is_default()           # skip @everyone
        and not r.managed               # skip bot-managed (integration) roles
        and r.name != "@everyone"
    ]

    # Filter to only roles that have at least one notable permission
    roles_with_perms = []
    for role in roles_to_show:
        notable = get_role_notable_perms(role, everyone_role)
        if notable:  # only include if it grants or denies something meaningful
            roles_with_perms.append((role, notable))

    if not roles_with_perms:
        await ctx.send("No roles with notable permissions found.")
        return

    await ctx.send(
        f"📋 **Role Permissions Overview** — {len(roles_with_perms)} roles with notable perms\n"
        f"*Roles with no extra permissions (Level 1, Male, Female, Verified, etc.) are hidden automatically.*"
    )

    # Send one embed per role (batch them to avoid rate limits)
    for role, notable in roles_with_perms:
        granted = [PERM_LABELS.get(k, k.replace("_", " ").title()) for k, v in notable.items() if v]
        denied  = [PERM_LABELS.get(k, k.replace("_", " ").title()) for k, v in notable.items() if not v]

        desc_parts = []
        if granted:
            desc_parts.append("✅ **Granted**\n" + "\n".join(f"  • {p}" for p in sorted(granted)))
        if denied:
            desc_parts.append("❌ **Denied / Removed**\n" + "\n".join(f"  • {p}" for p in sorted(denied)))

        if not desc_parts:
            continue

        embed = discord.Embed(
            title=f"{role.name}",
            description="\n\n".join(desc_parts),
            color=role.color if role.color.value != 0 else discord.Color.light_grey()
        )
        embed.set_footer(text=f"Role ID: {role.id} • Position: {role.position}")
        await ctx.send(embed=embed)
        await asyncio.sleep(0.4)  # small delay to avoid Discord rate limits

# ============================================================
#   ANNOUNCE  (Ahmed + Managers only)
# ============================================================

ANNOUNCE_CHANNEL = "announcements"

def is_announce_host(member: discord.Member) -> bool:
    allowed = {"Managers", "Ahmed"}
    return (
        any(r.name in allowed for r in member.roles)
        or member.guild_permissions.administrator
    )

@bot.command(name="announce")
async def announce_cmd(ctx, *, message: str = None):
    """
    Post a formatted announcement in #announcements.
    Ahmed and Managers only. The command message is deleted.
    Usage: ?announce Yoo, next stream is ...
    """
    if not is_announce_host(ctx.author):
        await ctx.send("Only **Managers** and **Ahmed** can post announcements.", delete_after=5)
        return

    if not message:
        await ctx.send("Please include your announcement text! e.g. `?announce Yoo, next stream is...`", delete_after=8)
        return

    channel = discord.utils.get(ctx.guild.text_channels, name=ANNOUNCE_CHANNEL)
    if not channel:
        await ctx.send(f"Could not find **#{ANNOUNCE_CHANNEL}**. Make sure the channel exists.", delete_after=8)
        return

    # Delete the command message so the channel looks clean
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    await channel.send(
        f"@everyone\n\n"
        f"{message}\n\n"
        f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        f"\u2014 {ctx.author.display_name}"
    )
    await log_command(ctx.guild, ctx.author, "announce", message[:50] + "..." if len(message) > 50 else message)


# ============================================================
#   TIMEZONE  (all users)
# ============================================================

# Common timezone aliases so users can type natural names
TIMEZONE_ALIASES = {
    # UK / Ireland
    "bst": "Europe/London",
    "gmt": "Europe/London",
    "uk": "Europe/London",
    "london": "Europe/London",
    "ireland": "Europe/Dublin",

    # US
    "est": "America/New_York",
    "eastern": "America/New_York",
    "new york": "America/New_York",
    "cst": "America/Chicago",
    "central": "America/Chicago",
    "chicago": "America/Chicago",
    "mst": "America/Denver",
    "mountain": "America/Denver",
    "pst": "America/Los_Angeles",
    "pacific": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
    "california": "America/Los_Angeles",

    # Europe
    "cet": "Europe/Paris",
    "west": "Europe/Lisbon",
    "lisbon": "Europe/Lisbon",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "amsterdam": "Europe/Amsterdam",
    "madrid": "Europe/Madrid",
    "rome": "Europe/Rome",
    "istanbul": "Europe/Istanbul",
    "athens": "Europe/Athens",
    "moscow": "Europe/Moscow",
    "msk": "Europe/Moscow",

    # Middle East / Gulf
    "dubai": "Asia/Dubai",
    "gst": "Asia/Dubai",
    "uae": "Asia/Dubai",
    "riyadh": "Asia/Riyadh",
    "saudi": "Asia/Riyadh",

    # Asia
    "ist": "Asia/Kolkata",
    "india": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
    "pakistan": "Asia/Karachi",
    "pkt": "Asia/Karachi",
    "bangladesh": "Asia/Dhaka",
    "nepal": "Asia/Kathmandu",
    "sri lanka": "Asia/Colombo",
    "singapore": "Asia/Singapore",
    "sgt": "Asia/Singapore",
    "malaysia": "Asia/Kuala_Lumpur",
    "jakarta": "Asia/Jakarta",
    "china": "Asia/Shanghai",
    "cst china": "Asia/Shanghai",
    "japan": "Asia/Tokyo",
    "jst": "Asia/Tokyo",
    "korea": "Asia/Seoul",
    "kst": "Asia/Seoul",

    # Australia
    "aest": "Australia/Sydney",
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "brisbane": "Australia/Brisbane",
    "perth": "Australia/Perth",
    "awst": "Australia/Perth",
    "adelaide": "Australia/Adelaide",

    # Africa
    "cairo": "Africa/Cairo",
    "eat": "Africa/Nairobi",
    "nairobi": "Africa/Nairobi",
    "nigeria": "Africa/Lagos",
    "ghana": "Africa/Accra",
    "south africa": "Africa/Johannesburg",
    "sast": "Africa/Johannesburg",

    # Americas other
    "toronto": "America/Toronto",
    "mexico": "America/Mexico_City",
    "brazil": "America/Sao_Paulo",
    "sao paulo": "America/Sao_Paulo",
    "argentina": "America/Argentina/Buenos_Aires",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "colombia": "America/Bogota",

    # UTC
    "utc": "UTC",
}

def resolve_timezone(tz_input: str):
    """
    Try to resolve a user-supplied string to a valid IANA timezone key.
    Returns the IANA string, or None if unresolvable.
    """
    import zoneinfo
    raw = tz_input.strip().lower()

    # 1. Check alias map
    if raw in TIMEZONE_ALIASES:
        return TIMEZONE_ALIASES[raw]

    # 2. Try direct IANA lookup (e.g. "Europe/London", "America/New_York")
    try:
        zoneinfo.ZoneInfo(tz_input.strip())
        return tz_input.strip()
    except (zoneinfo.ZoneInfoNotFoundError, KeyError, Exception):
        pass

    # 3. Try capitalising each word (e.g. "europe/london" -> "Europe/London")
    capitalised = "/".join(part.capitalize() for part in tz_input.strip().split("/"))
    try:
        zoneinfo.ZoneInfo(capitalised)
        return capitalised
    except Exception:
        pass

    return None

def get_current_time_in_tz(tz_str: str) -> str:
    """Return a formatted current-time string for the given IANA tz."""
    import zoneinfo
    try:
        tz = zoneinfo.ZoneInfo(tz_str)
        now = datetime.now(tz)
        return now.strftime("%I:%M %p, %A %d %B %Y")
    except Exception:
        return "Unknown"

@bot.command(name="timezone", aliases=["tz"])
async def timezone_cmd(ctx, action: str = None, *, location: str = None):
    """
    ?timezone set [location]  — save your timezone
    ?timezone                 — view your current timezone
    ?timezone @user           — view another user's timezone
    """
    await log_command(ctx.guild, ctx.author, "timezone", f"{action or ''} {location or ''}".strip())

    data = load_data()
    data = ensure_keys(data)
    if "timezones" not in data:
        data["timezones"] = {}

    uid = str(ctx.author.id)

    # --- ?timezone (no args) or ?timezone @user ---
    if action is None:
        tz_str = data["timezones"].get(uid)
        if not tz_str:
            await ctx.send(
                f"⚠️ {ctx.author.mention}: Your timezone has not been set yet. "
                f"Use `?timezone set (location)` to set it.\n\n"
                f"Examples: `?timezone set BST` · `?timezone set London` · `?timezone set Europe/London`"
            )
        else:
            current = get_current_time_in_tz(tz_str)
            embed = discord.Embed(
                title=f"🕐 {ctx.author.display_name}'s Timezone",
                description=f"**Timezone:** `{tz_str}`\n**Current time:** {current}",
                color=discord.Color.blurple()
            )
            await ctx.send(embed=embed)
        return

    # --- ?timezone @user (mentions someone) ---
    if action.startswith("<@") and ctx.message.mentions:
        target = ctx.message.mentions[0]
        tz_str = data["timezones"].get(str(target.id))
        if not tz_str:
            await ctx.send(f"{target.display_name} hasn't set their timezone yet.")
        else:
            current = get_current_time_in_tz(tz_str)
            embed = discord.Embed(
                title=f"🕐 {target.display_name}'s Timezone",
                description=f"**Timezone:** `{tz_str}`\n**Current time:** {current}",
                color=discord.Color.blurple()
            )
            await ctx.send(embed=embed)
        return

    # --- ?timezone set [location] ---
    if action.lower() == "set":
        if not location:
            await ctx.send(
                "Please provide a location! e.g.\n"
                "`?timezone set BST` · `?timezone set London` · `?timezone set Europe/London`"
            )
            return

        resolved = resolve_timezone(location)
        if not resolved:
            await ctx.send(
                f"❌ Couldn't recognise **{location}** as a timezone.\n"
                f"Try a city name (e.g. `London`, `Dubai`, `New York`) "
                f"or an IANA timezone (e.g. `Europe/London`, `America/New_York`)."
            )
            return

        data["timezones"][uid] = resolved
        save_data(data)

        current = get_current_time_in_tz(resolved)
        embed = discord.Embed(
            title="✅ Timezone Set!",
            description=(
                f"Your timezone has been set to **{resolved}**.\n"
                f"Current time for you: **{current}**"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    # Fallback — treat `action` as the timezone directly
    # e.g. ?timezone BST  (user forgot "set")
    combined = f"{action} {location}".strip() if location else action
    resolved = resolve_timezone(combined)
    if resolved:
        data["timezones"][uid] = resolved
        save_data(data)
        current = get_current_time_in_tz(resolved)
        embed = discord.Embed(
            title="✅ Timezone Set!",
            description=(
                f"Your timezone has been set to **{resolved}**.\n"
                f"Current time for you: **{current}**"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(
            f"❌ Couldn't recognise **{combined}** as a timezone.\n"
            f"Use `?timezone set London` or `?timezone set Europe/London`."
        )


# ============================================================
#   CHANNEL LOCK / UNLOCK
# ============================================================

# In-memory store of locked channels so the auto-unlock loop knows what to check
# Structure: { guild_id: { channel_id: { "unlock_at": float|None, "overwrites": {...} } } }
locked_channels = {}

def _parse_lock_duration(args: str):
    """
    Parse a lock duration/datetime from a string.
    Supports:
      - "5 hours", "30 minutes", "2h", "45m", "1d"
      - "28th 8:00 AM BST", "28 8:00 AM", "28th 20:00 UTC"
      - "2024-05-28 08:00 BST"
    Returns (unlock_timestamp: float, display_str: str, tz_str: str) or raises ValueError.
    """
    import re, zoneinfo
    from datetime import datetime, timezone, timedelta

    if not args:
        raise ValueError("no args")

    now_utc = datetime.now(timezone.utc)
    raw     = args.strip().lower()

    # ── 1. Relative duration: "5h", "5 hours", "30m", "30 minutes", "2d" ──
    rel_match = re.match(r"^(\d+)\s*(h(?:ours?)?|m(?:in(?:utes?)?)?|d(?:ays?)?)$", raw)
    if rel_match:
        val  = int(rel_match.group(1))
        unit = rel_match.group(2)[0]
        seconds = {"h": 3600, "m": 60, "d": 86400}[unit]
        unlock_ts = now_utc.timestamp() + val * seconds
        unit_name = {"h": f"{val} hour{'s' if val!=1 else ''}",
                     "m": f"{val} minute{'s' if val!=1 else ''}",
                     "d": f"{val} day{'s' if val!=1 else ''}"}[unit]
        return unlock_ts, unit_name, "UTC"

    # ── 2. Absolute datetime: "28th 8:00 AM BST", "28 20:00 UTC", etc. ──
    # Extract timezone suffix
    tz_str  = "UTC"
    tz_iata = "UTC"
    tz_pattern = re.compile(
        r"\b(bst|gmt|utc|est|pst|cst|mst|ist|gst|cet|msk|jst|kst|sgt|aest|awst|nzst|sast|eat)$",
        re.IGNORECASE
    )
    tz_match = tz_pattern.search(raw)
    if tz_match:
        tz_str  = tz_match.group(1).upper()
        raw     = raw[:tz_match.start()].strip()
        tz_iata = resolve_timezone(tz_str) or "UTC"

    # Try to parse the remaining date/time string
    # Normalise ordinals: "28th" -> "28", "1st" -> "1"
    raw_norm = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", raw)

    # Build candidate format strings — 12-hour clock only, AM/PM required
    fmt_candidates = [
        "%d %I:%M %p",     # 28 8:00 AM
        "%d %I %p",        # 28 8 AM  (no minutes)
        "%d %B %I:%M %p",  # 28 May 8:00 AM
        "%d %B %I %p",     # 28 May 8 AM
        "%Y-%m-%d %I:%M %p", # 2026-05-28 08:00 AM
        "%d/%m/%Y %I:%M %p", # 28/05/2026 08:00 AM
    ]

    parsed_dt = None
    for fmt in fmt_candidates:
        try:
            parsed_dt = datetime.strptime(raw_norm, fmt)
            break
        except ValueError:
            continue

    if not parsed_dt:
        raise ValueError(f"Could not parse datetime: {args!r}")

    # If no year/month in format, use current year/month
    try:
        tz_obj  = zoneinfo.ZoneInfo(tz_iata)
    except Exception:
        tz_obj  = timezone.utc
    now_local = datetime.now(tz_obj)

    full_dt = parsed_dt.replace(
        year  = parsed_dt.year  if parsed_dt.year  > 1900 else now_local.year,
        month = parsed_dt.month if parsed_dt.month != 1   else now_local.month,
        tzinfo=tz_obj,
    )

    # If the computed time is in the past (e.g. "28th" but today is 30th),
    # roll forward to next month
    if full_dt <= now_utc:
        if full_dt.month == 12:
            full_dt = full_dt.replace(year=full_dt.year+1, month=1)
        else:
            full_dt = full_dt.replace(month=full_dt.month+1)

    display = full_dt.strftime("%d %B %Y at %I:%M %p") + f" {tz_str}"
    return full_dt.timestamp(), display, tz_iata


async def _do_lock(channel: discord.TextChannel, guild, locker: discord.Member):
    """
    Lock a channel: deny send_messages for @everyone and all non-mod roles.
    Saves the previous overwrites so unlock can restore them exactly.
    """
    guild_id = str(guild.id)
    ch_id    = str(channel.id)

    # Snapshot current overwrites so we can restore them on unlock
    snapshot = {}
    for target, overwrite in channel.overwrites.items():
        snapshot[str(target.id)] = {
            "type":            "role" if isinstance(target, discord.Role) else "member",
            "send_messages":   overwrite.send_messages,
            "add_reactions":   overwrite.add_reactions,
            "create_public_threads": overwrite.create_public_threads,
            "create_private_threads": overwrite.create_private_threads,
        }

    locked_channels.setdefault(guild_id, {})[ch_id] = {
        "unlock_at":  None,  # set by caller if timed
        "overwrites": snapshot,
    }

    # Apply lock: deny sending for @everyone
    everyone = guild.default_role
    ow = channel.overwrites_for(everyone)
    ow.send_messages             = False
    ow.add_reactions             = False
    ow.create_public_threads     = False
    ow.create_private_threads    = False
    await channel.set_permissions(everyone, overwrite=ow, reason=f"Channel locked by {locker}")

    # For any other non-mod role that has explicit send_messages=True, also deny
    for role in guild.roles:
        if role == everyone or role.managed:
            continue
        if role.name in {"Ahmed", "Managers"} or is_mod_role(role):
            continue
        existing = channel.overwrites_for(role)
        if existing.send_messages is True:
            existing.send_messages          = False
            existing.add_reactions          = False
            existing.create_public_threads  = False
            existing.create_private_threads = False
            await channel.set_permissions(role, overwrite=existing, reason="Channel locked")


def is_mod_role(role: discord.Role) -> bool:
    """Return True if this role is a known mod role."""
    from discord import Permissions
    return (
        role.name in {"Ahmed", "Managers", "Mods", "Moderator", "Moderators"}
        or role.permissions.manage_messages
        or role.permissions.kick_members
        or role.permissions.administrator
    )


async def _do_unlock(channel: discord.TextChannel, guild, unlocker=None):
    """
    Unlock a channel: restore previous overwrites exactly.
    """
    guild_id = str(guild.id)
    ch_id    = str(channel.id)

    entry    = locked_channels.get(guild_id, {}).get(ch_id)
    reason   = f"Channel unlocked{f' by {unlocker}' if unlocker else ' (auto)'}"

    # Restore @everyone send_messages to previous value (or neutral)
    everyone = guild.default_role
    ow       = channel.overwrites_for(everyone)
    if entry and str(everyone.id) in entry["overwrites"]:
        snap = entry["overwrites"][str(everyone.id)]
        ow.send_messages          = snap["send_messages"]
        ow.add_reactions          = snap["add_reactions"]
        ow.create_public_threads  = snap["create_public_threads"]
        ow.create_private_threads = snap["create_private_threads"]
    else:
        ow.send_messages          = None  # reset to inherit
        ow.add_reactions          = None
        ow.create_public_threads  = None
        ow.create_private_threads = None

    await channel.set_permissions(everyone, overwrite=ow, reason=reason)

    # Restore any other roles we explicitly denied
    for role in guild.roles:
        if role == everyone or role.managed or is_mod_role(role):
            continue
        if entry and str(role.id) in entry["overwrites"]:
            snap     = entry["overwrites"][str(role.id)]
            existing = channel.overwrites_for(role)
            existing.send_messages          = snap["send_messages"]
            existing.add_reactions          = snap["add_reactions"]
            existing.create_public_threads  = snap["create_public_threads"]
            existing.create_private_threads = snap["create_private_threads"]
            await channel.set_permissions(role, overwrite=existing, reason=reason)

    # Clean up state
    locked_channels.get(guild_id, {}).pop(ch_id, None)


@tasks.loop(seconds=30)
async def lock_expire_loop():
    """Auto-unlock channels whose timer has expired."""
    now = time.time()
    for guild_id, channels in list(locked_channels.items()):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        for ch_id, entry in list(channels.items()):
            unlock_at = entry.get("unlock_at")
            if unlock_at and now >= unlock_at:
                channel = guild.get_channel(int(ch_id))
                if channel:
                    await _do_unlock(channel, guild)
                    await channel.send(
                        "This channel has been automatically unlocked."
                    )
                else:
                    locked_channels.get(guild_id, {}).pop(ch_id, None)

@lock_expire_loop.before_loop
async def before_lock_expire():
    await bot.wait_until_ready()


@bot.command(name="lock")
@mod_only()
async def lock_cmd(ctx, *, args: str = None):
    """
    Lock the current channel.
      ?lock                     — lock indefinitely
      ?lock 2h / 30m / 1d      — lock for a duration
      ?lock 28th 8:00 AM BST   — lock until a specific date/time
    """
    await log_command(ctx.guild, ctx.author, "lock", args or "")
    guild_id = str(ctx.guild.id)
    ch_id    = str(ctx.channel.id)

    # Already locked?
    if guild_id in locked_channels and ch_id in locked_channels[guild_id]:
        await ctx.send("This channel is already locked. Use `?unlock` to unlock it.")
        return

    unlock_ts      = None
    duration_label = None
    tz_used        = None

    if args:
        try:
            unlock_ts, duration_label, tz_used = _parse_lock_duration(args)
        except ValueError:
            await ctx.send(
                "Couldn't parse that. Examples:\n"
                "`?lock 2h` · `?lock 30m` · `?lock 1d`\n"
                "`?lock 28th 8:00 AM BST` · `?lock 28th 9:30 PM UTC`"
            )
            return

    await _do_lock(ctx.channel, ctx.guild, ctx.author)

    # Store unlock timestamp
    if unlock_ts:
        locked_channels[guild_id][ch_id]["unlock_at"] = unlock_ts

    # Build the public lock message
    if unlock_ts and duration_label and tz_used:
        # Discord timestamp shows in each user's local time automatically
        disc_ts    = f"<t:{int(unlock_ts)}:F>"   # full date/time
        disc_rel   = f"<t:{int(unlock_ts)}:R>"   # relative ("in 2 hours")

        # Also show in their personal timezone if they have one set
        data = load_data()
        data = ensure_keys(data)
        uid  = str(ctx.author.id)
        personal_tz = data.get("timezones", {}).get(uid)

        tz_note = ""
        if personal_tz:
            personal_time = get_current_time_in_tz.__wrapped__(unlock_ts, personal_tz) \
                if hasattr(get_current_time_in_tz, "__wrapped__") \
                else _ts_in_tz(unlock_ts, personal_tz)
            tz_note = f"\n*(That's **{personal_time}** in your timezone)*"

        await ctx.send(
            f"🔒 This channel is now locked and will be moderated by mods.\n"
            f"It will unlock automatically {disc_rel} ({disc_ts}).{tz_note}\n\n"
            f"*Use `?tz` to see what time that is for you.*"
        )
    else:
        await ctx.send(
            "🔒 This channel is now locked and will be moderated by mods. "
            "It will be unlocked soon."
        )
    await log_action(ctx.guild, "Lock", None, ctx.author,
                     f"Locked #{ctx.channel.name}" + (f" until {duration_label}" if duration_label else ""))


@bot.command(name="unlock")
@mod_only()
async def unlock_cmd(ctx):
    """Unlock the current channel."""
    await log_command(ctx.guild, ctx.author, "unlock")
    guild_id = str(ctx.guild.id)
    ch_id    = str(ctx.channel.id)

    if guild_id not in locked_channels or ch_id not in locked_channels[guild_id]:
        await ctx.send("This channel is not locked.")
        return

    await _do_unlock(ctx.channel, ctx.guild, ctx.author)
    await ctx.send("🔓 This channel has been unlocked.")
    await log_action(ctx.guild, "Unlock", None, ctx.author, f"Unlocked #{ctx.channel.name}")


def _ts_in_tz(timestamp: float, tz_str: str) -> str:
    """Format a Unix timestamp in a given IANA timezone."""
    try:
        import zoneinfo
        from datetime import datetime
        tz  = zoneinfo.ZoneInfo(tz_str)
        dt  = datetime.fromtimestamp(timestamp, tz=tz)
        return dt.strftime("%I:%M %p, %d %B %Y")
    except Exception:
        return "unknown time"


# ============================================================
#   MANUAL YOUTUBE CHECK  (?ytcheck) — Managers + Ahmed only
# ============================================================

@bot.command(name="ytcheck")
async def ytcheck_cmd(ctx):
    """Manually trigger the YouTube RSS upload check. Managers + Ahmed only."""
    senior = {"Managers", "Ahmed"}
    if not any(r.name in senior for r in ctx.author.roles) and not ctx.author.guild_permissions.administrator:
        await ctx.send("Only **Managers** and **Ahmed** can use this command.", delete_after=5)
        return

    await log_command(ctx.guild, ctx.author, "ytcheck")
    status_msg = await ctx.send("🔍 Checking YouTube for new uploads...")

    global _yt_rss_fail_count, _yt_backoff_until
    # Reset backoff so the manual check always tries RSS first
    _yt_rss_fail_count = 0
    _yt_backoff_until  = 0

    videos = await get_latest_youtube_videos()

    if not videos:
        await status_msg.edit(content="❌ Could not fetch YouTube videos. Check Railway logs for details.")
        return

    data = load_data()
    data = ensure_keys(data)
    last_id = data.get("last_youtube_id")

    if last_id is None:
        data["last_youtube_id"] = videos[0]["id"]
        save_data(data)
        await status_msg.edit(content=f"✅ First run — seeded with latest video: **{videos[0]['title']}**\nFuture uploads will now be announced.")
        return

    new_videos = []
    for v in videos:
        if v["id"] == last_id:
            break
        new_videos.append(v)

    if not new_videos:
        await status_msg.edit(content=f"✅ No new uploads found. Latest video already announced: **{videos[0]['title']}**")
        return

    data["last_youtube_id"] = videos[0]["id"]
    save_data(data)

    await status_msg.edit(content=f"✅ Found **{len(new_videos)}** new video(s) — announcing now...")

    announced = 0
    for video in reversed(new_videos):
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
                alert_role, _ = await get_or_create_alert_role(
                    guild, "Upload Alerts", discord.Colour.red()
                )
                await channel.send(f"{alert_role.mention} {video['title']} | {video['link']}", embed=embed)
                announced += 1

    await status_msg.edit(content=f"✅ Done — announced **{len(new_videos)}** video(s) in **{announced}** channel(s).")

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
        await dm_owner(
            f"Unhandled command error: {type(error).__name__}",
            f"**Command:** `{ctx.command}` used by **{ctx.author}** in **#{ctx.channel.name}**\n\n"
            f"**Error type:** `{type(error).__name__}`\n"
            f"**Detail:** {str(error)[:800]}",
            cooldown=False  # each command crash is unique
        )


# ============================================================
#   BATTLE SYSTEM  (?battle — HP + crits + attack phases)
# ============================================================

BATTLE_BASE_HP     = 100
BATTLE_ATK_MIN     = 10
BATTLE_ATK_MAX     = 25
BATTLE_CRIT_CHANCE = 0.15
BATTLE_CRIT_MULT   = 2.0

class BattleAcceptView(discord.ui.View):
    def __init__(self, challenger, challenged, amount, guild_id):
        super().__init__(timeout=30)
        self.challenger = challenger
        self.challenged = challenged
        self.amount     = amount
        self.guild_id   = guild_id
        self.done       = False

    @discord.ui.button(label="Accept!", style=discord.ButtonStyle.green)
    async def accept_btn(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message("This is not your battle!", ephemeral=True)
            return
        if self.done:
            return
        self.done = True
        self.stop()
        await self._run_battle(interaction)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline_btn(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message("Not your battle!", ephemeral=True)
            return
        self.done = True
        self.stop()
        await interaction.response.edit_message(content=f"The challenge was declined.", embed=None, view=None)

    async def _run_battle(self, interaction: discord.Interaction):
        await interaction.response.defer()
        c_hp = BATTLE_BASE_HP
        d_hp = BATTLE_BASE_HP
        log  = []
        for _ in range(30):
            if c_hp <= 0 or d_hp <= 0:
                break
            for attacker, defender, side in [(self.challenger, self.challenged, "d"), (self.challenged, self.challenger, "c")]:
                if c_hp <= 0 or d_hp <= 0:
                    break
                atk  = random.randint(BATTLE_ATK_MIN, BATTLE_ATK_MAX)
                crit = random.random() < BATTLE_CRIT_CHANCE
                if crit:
                    atk = int(atk * BATTLE_CRIT_MULT)
                if side == "d":
                    d_hp = max(0, d_hp - atk)
                    remaining = d_hp
                else:
                    c_hp = max(0, c_hp - atk)
                    remaining = c_hp
                crit_tag = " CRIT!" if crit else ""
                log.append(f"**{attacker.display_name}** hits **{atk}**{crit_tag} -> {defender.display_name}: **{remaining} HP**")
        shown = "\n".join(log[-8:])
        if c_hp > d_hp:
            winner, loser = self.challenger, self.challenged
        elif d_hp > c_hp:
            winner, loser = self.challenged, self.challenger
        else:
            winner = loser = None
        if winner:
            data = load_data()
            data = ensure_keys(data)
            wid, lid = str(winner.id), str(loser.id)
            loser_pts = get_user_points(data, self.guild_id, lid)
            prize = min(self.amount, loser_pts)
            set_user_points(data, self.guild_id, wid, get_user_points(data, self.guild_id, wid) + prize)
            set_user_points(data, self.guild_id, lid, loser_pts - prize)
            save_data(data)
            result = f"**{winner.display_name}** wins **{prize:,} points**!"
            color  = discord.Color.green()
        else:
            result = "Draw! No points exchanged."
            color  = discord.Color.gold()
        embed = discord.Embed(
            title="Battle Over!",
            description=f"{shown}\n\n{result}",
            color=color
        )
        embed.add_field(name="Final HP", value=f"{self.challenger.display_name}: **{c_hp}**\n{self.challenged.display_name}: **{d_hp}**")
        await interaction.message.edit(embed=embed, view=None)

    async def on_timeout(self):
        self.done = True

@bot.command(name="battle")
async def battle_cmd(ctx, target: discord.Member = None, amount: int = None):
    """HP-based battle with crits. ?battle @user [amount]"""
    await log_command(ctx.guild, ctx.author, "battle")
    if not target or target.bot or target.id == ctx.author.id:
        await ctx.send("Challenge someone! e.g. `?battle @user 200`")
        return
    if not amount or amount <= 0:
        await ctx.send("Specify a bet! e.g. `?battle @user 200`")
        return
    guild_id = str(ctx.guild.id)
    data = load_data()
    data = ensure_keys(data)
    c_pts = get_user_points(data, guild_id, str(ctx.author.id))
    d_pts = get_user_points(data, guild_id, str(target.id))
    if c_pts < amount:
        await ctx.send(f"You only have **{c_pts:,} points**.")
        return
    if d_pts < amount:
        await ctx.send(f"{target.display_name} only has **{d_pts:,} points**.")
        return
    embed = discord.Embed(
        title="Battle Challenge!",
        description=(
            f"{ctx.author.mention} challenges {target.mention}!\n\n"
            f"**Bet:** {amount:,} points | **HP:** {BATTLE_BASE_HP} each\n"
            f"{target.mention} — accept within 30 seconds."
        ),
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed, view=BattleAcceptView(ctx.author, target, amount, guild_id))


# ============================================================
#   SLOTS  (?slots [amount])
# ============================================================

SLOT_SYMBOLS = ["cherry","lemon","orange","grapes","star","diamond","seven"]
SLOT_EMOJIS  = {"cherry":"🍒","lemon":"🍋","orange":"🍊","grapes":"🍇","star":"⭐","diamond":"💎","seven":"7️⃣"}
SLOT_WEIGHTS = [30, 25, 20, 15, 5, 4, 1]
SLOT_PAYOUTS = {
    ("seven","seven","seven"):    50,
    ("diamond","diamond","diamond"): 20,
    ("star","star","star"):       10,
    ("grapes","grapes","grapes"):  5,
    ("orange","orange","orange"):  4,
    ("lemon","lemon","lemon"):     3,
    ("cherry","cherry","cherry"):  2,
}
SLOTS_COOLDOWN = 30
slots_cooldowns = {}

@bot.command(name="slots")
async def slots_cmd(ctx, amount: int = None):
    """Spin the slot machine! ?slots [amount]"""
    await log_command(ctx.guild, ctx.author, "slots")
    guild_id = str(ctx.guild.id)
    uid = str(ctx.author.id)
    now = time.time()
    if not amount or amount <= 0:
        await ctx.send("Specify a bet! e.g. `?slots 100`")
        return
    cd_key = f"{guild_id}_{uid}"
    if cd_key in slots_cooldowns and now - slots_cooldowns[cd_key] < SLOTS_COOLDOWN:
        rem = int(SLOTS_COOLDOWN - (now - slots_cooldowns[cd_key]))
        await ctx.send(f"Cooldown: **{rem}s** remaining.", delete_after=5)
        return
    data = load_data()
    data = ensure_keys(data)
    pts = get_user_points(data, guild_id, uid)
    if pts < amount:
        await ctx.send(f"You only have **{pts:,} points**.")
        return
    slots_cooldowns[cd_key] = now
    result = random.choices(SLOT_SYMBOLS, weights=SLOT_WEIGHTS, k=3)
    rt     = tuple(result)
    mult   = SLOT_PAYOUTS.get(rt, 0)
    label  = ""
    if mult > 0:
        if rt == ("seven","seven","seven"):
            label = "JACKPOT!!!"
        elif rt == ("diamond","diamond","diamond"):
            label = "DIAMOND WIN!"
        else:
            label = "Three of a kind!"
    elif result[0]==result[1] or result[1]==result[2] or result[0]==result[2]:
        mult  = 0.5
        label = "Two of a kind — half back!"
    else:
        label = "No match."
    winnings = int(amount * mult)
    net      = winnings - amount
    new_pts  = max(0, pts - amount + winnings)
    set_user_points(data, guild_id, uid, new_pts)
    if net > 0:
        data.setdefault("gamble_wins", {}).setdefault(guild_id, {})[uid] = \
            data.get("gamble_wins", {}).get(guild_id, {}).get(uid, 0) + 1
    save_data(data)
    slot_str = f"[ {SLOT_EMOJIS[result[0]]} | {SLOT_EMOJIS[result[1]]} | {SLOT_EMOJIS[result[2]]} ]"
    color    = discord.Color.green() if net > 0 else (discord.Color.gold() if net == 0 else discord.Color.red())
    net_str  = f"+**{net:,}**" if net >= 0 else f"-**{abs(net):,}**"
    embed = discord.Embed(
        title="Slot Machine",
        description=f"## {slot_str}\n\n{label}\n{net_str} points  |  Balance: **{new_pts:,}**",
        color=color
    )
    await ctx.send(embed=embed)


# ============================================================
#   BOSS RAID  (?raid to start, ?attack to hit)
# ============================================================

RAID_BOSSES = [
    {"name":"The Shadow Dragon","emoji":"🐉","hp":5000,"pool":10000},
    {"name":"Cyber Overlord",   "emoji":"🤖","hp":3000,"pool":6000},
    {"name":"Ancient Titan",    "emoji":"🗿","hp":4000,"pool":8000},
    {"name":"Void Serpent",     "emoji":"🐍","hp":3500,"pool":7000},
    {"name":"Storm Colossus",   "emoji":"⛈️", "hp":4500,"pool":9000},
]
active_raids = {}

@bot.command(name="raid")
@mod_only()
async def raid_cmd(ctx):
    """Start a boss raid (mod only). Everyone attacks with ?attack."""
    await log_command(ctx.guild, ctx.author, "raid")
    guild_id = str(ctx.guild.id)
    if guild_id in active_raids:
        await ctx.send("A raid is already active! Use `?attack` to join.")
        return
    boss = random.choice(RAID_BOSSES)
    active_raids[guild_id] = {
        "boss": boss.copy(), "hp": boss["hp"], "max_hp": boss["hp"],
        "participants": {}, "channel_id": str(ctx.channel.id),
    }
    embed = discord.Embed(
        title=f"{boss['emoji']} BOSS RAID — {boss['name']}",
        description=(
            f"A powerful enemy has appeared!\n\n"
            f"**HP:** {boss['hp']:,}  |  **Reward Pool:** {boss['pool']:,} points\n\n"
            f"Type `?attack` to strike! Rewards split by damage dealt."
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text="Raid ends when boss dies or in 10 minutes.")
    await ctx.send("@everyone", embed=embed)
    asyncio.create_task(_auto_end_raid(guild_id, 600))

async def _auto_end_raid(guild_id, delay):
    await asyncio.sleep(delay)
    if guild_id in active_raids:
        await _conclude_raid(guild_id, timeout=True)

async def _conclude_raid(guild_id, timeout=False):
    raid = active_raids.pop(guild_id, None)
    if not raid:
        return
    guild   = bot.get_guild(int(guild_id))
    if not guild:
        return
    channel = guild.get_channel(int(raid["channel_id"]))
    if not channel:
        return
    boss  = raid["boss"]
    parts = raid["participants"]
    if not parts:
        await channel.send(f"The **{boss['name']}** fled — nobody attacked!")
        return
    total_dmg = sum(parts.values())
    pool      = boss["pool"]
    if timeout:
        pool  = int(pool * (1 - raid["hp"] / raid["max_hp"]))
        title = f"Time is up! {boss['name']} escaped with {raid['hp']:,} HP remaining."
    else:
        title = f"{boss['emoji']} {boss['name']} has been defeated!"
    data = load_data()
    data = ensure_keys(data)
    lines = []
    for uid, dmg in sorted(parts.items(), key=lambda x: x[1], reverse=True):
        share = int((dmg / total_dmg) * pool)
        if share:
            set_user_points(data, guild_id, uid, get_user_points(data, guild_id, uid) + share)
        m    = guild.get_member(int(uid))
        name = m.display_name if m else f"User {uid}"
        lines.append(f"{name}: **{dmg:,}** dmg -> **+{share:,}** pts")
    save_data(data)
    embed = discord.Embed(
        title=title,
        description="\n".join(lines) or "No rewards.",
        color=discord.Color.gold()
    )
    await channel.send(embed=embed)

@bot.command(name="attack")
async def attack_cmd(ctx):
    """Attack the active boss during a raid!"""
    await log_command(ctx.guild, ctx.author, "attack")
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    if guild_id not in active_raids:
        await ctx.send("No raid active! Wait for a mod to start one with `?raid`.", delete_after=5)
        return
    raid = active_raids[guild_id]
    dmg  = random.randint(50, 200)
    crit = random.random() < 0.1
    if crit:
        dmg = int(dmg * 2.5)
    raid["hp"] = max(0, raid["hp"] - dmg)
    raid["participants"][uid] = raid["participants"].get(uid, 0) + dmg
    pct      = raid["hp"] / raid["max_hp"]
    bar      = chr(9608) * int(pct * 10) + chr(9617) * (10 - int(pct * 10))
    crit_tag = " CRIT!" if crit else ""
    await ctx.send(
        f"{ctx.author.mention} deals **{dmg}** damage!{crit_tag}\n"
        f"{raid['boss']['emoji']} HP: `[{bar}]` **{raid['hp']:,}/{raid['max_hp']:,}**",
        delete_after=15
    )
    if raid["hp"] <= 0:
        await _conclude_raid(guild_id)


# ============================================================
#   MYSTERY BOXES  (5 unique users in 5s triggers a drop)
# ============================================================

_mystery_box_tracker = {}
_mystery_box_active  = {}

MYSTERY_BOX_REWARDS = [
    (500,  "Common Box",    discord.Color.greyple(), 60),
    (1000, "Rare Box",      discord.Color.purple(),  25),
    (2500, "Epic Box",      discord.Color.gold(),    12),
    (5000, "Legendary Box", discord.Color.orange(),  3),
]

async def _maybe_spawn_mystery_box(channel, guild_id, uid):
    now = time.time()
    _mystery_box_tracker.setdefault(guild_id, {}).setdefault(str(channel.id), {})[uid] = now
    window = {u: t for u, t in _mystery_box_tracker[guild_id][str(channel.id)].items() if now - t <= 5}
    _mystery_box_tracker[guild_id][str(channel.id)] = window
    if (len(window) >= 5
            and guild_id not in _mystery_box_active
            and guild_id not in active_trivia
            and guild_id not in active_fun_quiz
            and guild_id not in active_raids):
        _mystery_box_tracker[guild_id][str(channel.id)] = {}
        _mystery_box_active[guild_id] = True
        asyncio.create_task(_spawn_mystery_box(channel, guild_id))

async def _spawn_mystery_box(channel, guild_id):
    reward_pts, box_name, color, _ = random.choices(
        MYSTERY_BOX_REWARDS, weights=[r[3] for r in MYSTERY_BOX_REWARDS], k=1
    )[0]

    class MBView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.claimed = False

        @discord.ui.button(label="Claim!", style=discord.ButtonStyle.green)
        async def claim_btn(self, interaction: discord.Interaction, button):
            if self.claimed:
                await interaction.response.send_message("Already claimed!", ephemeral=True)
                return
            self.claimed = True
            self.stop()
            _mystery_box_active.pop(guild_id, None)
            data = load_data()
            data = ensure_keys(data)
            claim_uid = str(interaction.user.id)
            set_user_points(data, guild_id, claim_uid, get_user_points(data, guild_id, claim_uid) + reward_pts)
            save_data(data)
            button.disabled = True
            button.label    = f"Claimed by {interaction.user.display_name}!"
            win_embed = discord.Embed(
                title=f"{box_name} Opened!",
                description=f"{interaction.user.mention} claimed **{reward_pts:,} points**!",
                color=color
            )
            await interaction.response.edit_message(embed=win_embed, view=self)

        async def on_timeout(self):
            _mystery_box_active.pop(guild_id, None)

    embed = discord.Embed(
        title=f"A {box_name} appeared!",
        description=f"Chat activity summoned a mystery box!\nFirst to click wins **{reward_pts:,} points**!\n30 seconds...",
        color=color
    )
    await channel.send(embed=embed, view=MBView())


# ============================================================
#   SETBIO / SETTITLE
# ============================================================

@bot.command(name="setbio")
async def setbio_cmd(ctx, *, bio: str = None):
    """Set a custom bio on your ?profile."""
    await log_command(ctx.guild, ctx.author, "setbio")
    if not bio:
        await ctx.send("Usage: `?setbio I love gaming!`")
        return
    if len(bio) > 150:
        await ctx.send("Bio must be 150 characters or less.")
        return
    data = load_data()
    data = ensure_keys(data)
    data.setdefault("bios", {})[str(ctx.author.id)] = bio
    save_data(data)
    await ctx.send(f"Bio updated!")

@bot.command(name="settitle")
async def settitle_cmd(ctx, *, title: str = None):
    """Equip an unlocked achievement title. ?settitle [title name]"""
    await log_command(ctx.guild, ctx.author, "settitle")
    data     = load_data()
    data     = ensure_keys(data)
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    unlocked = data.get("achievements", {}).get(guild_id, {}).get(uid, [])
    if not title:
        if unlocked:
            await ctx.send(f"Your unlocked titles: **{', '.join(unlocked)}**\nUse `?settitle [name]` to equip one.")
        else:
            await ctx.send("No titles yet. Keep playing to earn them!")
        return
    matched = next((t for t in unlocked if t.lower() == title.lower()), None)
    if not matched:
        await ctx.send(f"You have not unlocked **{title}** yet.")
        return
    data.setdefault("titles", {})[uid] = matched
    save_data(data)
    await ctx.send(f"Title equipped: **{matched}**")


# ============================================================
#   CLANS
# ============================================================

CLAN_CREATE_COST = 5000
MAX_CLAN_MEMBERS = 20

@bot.command(name="clan")
async def clan_cmd(ctx, action: str = None, *, arg: str = None):
    """?clan create/join/leave/info/top"""
    await log_command(ctx.guild, ctx.author, "clan", f"{action or ''} {arg or ''}".strip())
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    data     = load_data()
    data     = ensure_keys(data)
    data.setdefault("clans", {}).setdefault(guild_id, {})
    data.setdefault("clan_members", {}).setdefault(guild_id, {})
    clans   = data["clans"][guild_id]
    members = data["clan_members"][guild_id]

    if not action:
        await ctx.send("Usage: `?clan create [name]` · `?clan join [name]` · `?clan leave` · `?clan info` · `?clan top`")
        return

    action = action.lower()

    if action == "create":
        if not arg:
            await ctx.send("Provide a clan name.")
            return
        if uid in members:
            await ctx.send("You are already in a clan. Leave first with `?clan leave`.")
            return
        if arg.lower() in {k.lower() for k in clans}:
            await ctx.send(f"A clan named **{arg}** already exists.")
            return
        pts = get_user_points(data, guild_id, uid)
        if pts < CLAN_CREATE_COST:
            await ctx.send(f"Creating a clan costs **{CLAN_CREATE_COST:,} points**. You have **{pts:,}**.")
            return
        set_user_points(data, guild_id, uid, pts - CLAN_CREATE_COST)
        clans[arg] = {"leader": uid, "members": [uid], "xp": 0}
        members[uid] = arg
        save_data(data)
        await ctx.send(f"Clan **{arg}** created for {CLAN_CREATE_COST:,} points!")

    elif action == "join":
        if not arg:
            await ctx.send("Which clan? `?clan join ClanName`")
            return
        if uid in members:
            await ctx.send("You are already in a clan.")
            return
        match = next((k for k in clans if k.lower() == arg.lower()), None)
        if not match:
            await ctx.send(f"Clan **{arg}** not found.")
            return
        if len(clans[match]["members"]) >= MAX_CLAN_MEMBERS:
            await ctx.send(f"**{match}** is full.")
            return
        clans[match]["members"].append(uid)
        members[uid] = match
        save_data(data)
        await ctx.send(f"Joined clan **{match}**!")

    elif action == "leave":
        if uid not in members:
            await ctx.send("You are not in a clan.")
            return
        clan_name = members[uid]
        clan = clans[clan_name]
        clan["members"] = [m for m in clan["members"] if m != uid]
        del members[uid]
        if not clan["members"]:
            del clans[clan_name]
            await ctx.send(f"You left **{clan_name}** and it was disbanded.")
        elif clan["leader"] == uid:
            clan["leader"] = clan["members"][0]
            save_data(data)
            new_leader = ctx.guild.get_member(int(clan["leader"]))
            await ctx.send(f"You left **{clan_name}**. Leadership passed to {new_leader.display_name if new_leader else 'someone else'}.")
        else:
            save_data(data)
            await ctx.send(f"You left **{clan_name}**.")

    elif action == "info":
        clan_name = members.get(uid)
        if not clan_name:
            await ctx.send("You are not in a clan.")
            return
        clan   = clans[clan_name]
        leader = ctx.guild.get_member(int(clan["leader"]))
        names  = [(ctx.guild.get_member(int(m)).display_name if ctx.guild.get_member(int(m)) else f"User {m}") for m in clan["members"]]
        embed  = discord.Embed(title=f"Clan: {clan_name}", color=discord.Color.blurple())
        embed.add_field(name="Leader",  value=leader.display_name if leader else "Unknown")
        embed.add_field(name="Members", value=f"{len(clan['members'])}/{MAX_CLAN_MEMBERS}")
        embed.add_field(name="Clan XP", value=f"{clan['xp']:,}")
        embed.add_field(name="Roster",  value=", ".join(names) or "None", inline=False)
        await ctx.send(embed=embed)

    elif action == "top":
        if not clans:
            await ctx.send("No clans yet.")
            return
        sorted_clans = sorted(clans.items(), key=lambda x: x[1].get("xp", 0), reverse=True)[:10]
        medals = {1:"1st",2:"2nd",3:"3rd"}
        lines  = [f"{medals.get(r, str(r)+'..')} **{cn}** — {cd.get('xp',0):,} XP · {len(cd['members'])} members"
                  for r, (cn, cd) in enumerate(sorted_clans, 1)]
        await ctx.send(embed=discord.Embed(title="Clan Leaderboard", description="\n".join(lines), color=discord.Color.gold()))
    else:
        await ctx.send("Unknown action.")


# ============================================================
#   PARTNERSHIPS
# ============================================================

@bot.command(name="partner")
async def partner_cmd(ctx, target: discord.Member = None):
    """?partner @user — propose | ?partner — view your partnership"""
    await log_command(ctx.guild, ctx.author, "partner")
    uid  = str(ctx.author.id)
    data = load_data()
    data = ensure_keys(data)
    data.setdefault("partnerships", {})
    data.setdefault("partner_requests", {})
    now  = time.time()

    if target is None:
        p = data["partnerships"].get(uid)
        if not p:
            await ctx.send("No partner yet. Use `?partner @user` to propose!")
            return
        pm   = ctx.guild.get_member(int(p["partner_id"]))
        days = int((now - p["since"]) / 86400)
        bonus = 20 if days >= 90 else (10 if days >= 30 else 5)
        await ctx.send(
            f"Your Partner: {pm.mention if pm else 'Unknown'}\n"
            f"Together: **{days} days**\n"
            f"Daily bonus: **+{bonus}%**"
        )
        return

    if target.bot or target.id == ctx.author.id:
        await ctx.send("Invalid target.")
        return
    tid = str(target.id)
    if uid in data["partnerships"]:
        await ctx.send("You are already in a partnership.")
        return

    rev_key = f"{tid}_{uid}"
    req_key = f"{uid}_{tid}"
    if rev_key in data["partner_requests"]:
        del data["partner_requests"][rev_key]
        data["partnerships"][uid] = {"partner_id": tid, "since": now}
        data["partnerships"][tid] = {"partner_id": uid, "since": now}
        save_data(data)
        await ctx.send(f"You and {target.mention} are now partners! Your daily bonus grows the longer you stay together.")
    else:
        data["partner_requests"][req_key] = now
        save_data(data)
        await ctx.send(f"Partnership request sent to {target.mention}! They can accept by using `?partner {ctx.author.mention}`.")

@bot.command(name="unpartner")
async def unpartner_cmd(ctx):
    """End your current partnership."""
    await log_command(ctx.guild, ctx.author, "unpartner")
    uid  = str(ctx.author.id)
    data = load_data()
    data = ensure_keys(data)
    data.setdefault("partnerships", {})
    p = data["partnerships"].pop(uid, None)
    if not p:
        await ctx.send("You are not in a partnership.")
        return
    data["partnerships"].pop(p["partner_id"], None)
    save_data(data)
    pm = ctx.guild.get_member(int(p["partner_id"]))
    await ctx.send(f"Partnership ended with {pm.mention if pm else 'your partner'}.")


# ============================================================
#   CRAFTING SYSTEM
# ============================================================

CRAFT_MATERIALS = {
    "animal_hide":    "Animal Hide",
    "rare_feather":   "Rare Feather",
    "bone_fragment":  "Bone Fragment",
    "pearl":          "Pearl",
    "ancient_scale":  "Ancient Scale",
    "coral_fragment": "Coral Fragment",
}

CRAFT_RECIPES = {
    "legendary_rod": {
        "name": "Legendary Fishing Rod",
        "desc": "Massively increases fishing rewards.",
        "ingredients": {"ancient_scale": 3, "coral_fragment": 1, "pearl": 1},
    },
    "masterwork_rifle": {
        "name": "Masterwork Rifle",
        "desc": "Increases hunt rewards by 50%.",
        "ingredients": {"bone_fragment": 2, "rare_feather": 1, "animal_hide": 1},
    },
    "fortune_charm": {
        "name": "Fortune Charm",
        "desc": "Increases ?crime and ?beg success rate permanently.",
        "ingredients": {"pearl": 1, "rare_feather": 1, "animal_hide": 1},
    },
    "enchanted_bait": {
        "name": "Enchanted Bait",
        "desc": "Guarantees a rare fish on next cast.",
        "ingredients": {"pearl": 2, "coral_fragment": 1},
    },
}

def get_materials(data, guild_id, user_id):
    return data.setdefault("crafting_materials", {}).setdefault(guild_id, {}).setdefault(user_id, {})

def add_material(data, guild_id, user_id, material, amount=1):
    mats = get_materials(data, guild_id, user_id)
    mats[material] = mats.get(material, 0) + amount

@bot.command(name="materials", aliases=["mats"])
async def materials_cmd(ctx):
    """View your crafting materials."""
    await log_command(ctx.guild, ctx.author, "materials")
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    data     = load_data()
    data     = ensure_keys(data)
    mats     = get_materials(data, guild_id, uid)
    if not mats or all(v == 0 for v in mats.values()):
        await ctx.send("No crafting materials yet. Earn them from `?hunt` and `?fish`!")
        return
    lines = [f"{CRAFT_MATERIALS.get(k, k)}: **{v}**" for k, v in mats.items() if v > 0]
    embed = discord.Embed(title="Your Crafting Materials", description="\n".join(lines), color=discord.Color.teal())
    embed.set_footer(text="?craft to see recipes | ?craft [item] to craft")
    await ctx.send(embed=embed)

@bot.command(name="craft")
async def craft_cmd(ctx, *, item_key: str = None):
    """?craft — list recipes | ?craft [item] — craft an item"""
    await log_command(ctx.guild, ctx.author, "craft", item_key or "")
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    if not item_key:
        embed = discord.Embed(title="Crafting Recipes", color=discord.Color.teal())
        for key, recipe in CRAFT_RECIPES.items():
            ing = ", ".join(f"{CRAFT_MATERIALS.get(m, m)} x{q}" for m, q in recipe["ingredients"].items())
            embed.add_field(name=recipe["name"], value=f"{recipe['desc']}\n**Needs:** {ing}\n`?craft {key}`", inline=False)
        await ctx.send(embed=embed)
        return
    matched_key = next((k for k in CRAFT_RECIPES if item_key.lower() in (k.lower(), CRAFT_RECIPES[k]["name"].lower())), None)
    if not matched_key:
        await ctx.send(f"Unknown recipe. Use `?craft` to see all.")
        return
    recipe = CRAFT_RECIPES[matched_key]
    data   = load_data()
    data   = ensure_keys(data)
    mats   = get_materials(data, guild_id, uid)
    missing = [f"{CRAFT_MATERIALS.get(m, m)}: need {q}, have {mats.get(m, 0)}"
               for m, q in recipe["ingredients"].items() if mats.get(m, 0) < q]
    if missing:
        await ctx.send("Missing materials:\n" + "\n".join(missing))
        return
    for m, q in recipe["ingredients"].items():
        mats[m] -= q
    add_to_inventory(data, guild_id, uid, matched_key)
    save_data(data)
    await ctx.send(f"You crafted **{recipe['name']}**! {recipe['desc']}\nCheck `?inventory`.")


# ============================================================
#   STOCK MARKET
# ============================================================

STOCKS_DEF = {
    "AHMD": {"name": "Ahmed Coins",   "emoji": "🪙"},
    "VXON": {"name": "Vexon Tech",    "emoji": "💻"},
    "LNGE": {"name": "Lounge Shares", "emoji": "🛋️"},
    "GCORP":{"name": "Gaming Corp",   "emoji": "🎮"},
    "STRM": {"name": "Stream Token",  "emoji": "📡"},
}
_stock_market_running = False

@tasks.loop(hours=1)
async def stock_market_loop():
    data   = load_data()
    data   = ensure_keys(data)
    market = data.setdefault("stocks", {})
    for ticker in STOCKS_DEF:
        if ticker not in market:
            market[ticker] = {"price": random.randint(50, 200), "history": []}
        old   = market[ticker]["price"]
        chg   = random.uniform(-0.20, 0.30)
        new   = max(10, int(old * (1 + chg)))
        market[ticker]["history"] = (market[ticker]["history"] + [old])[-24:]
        market[ticker]["price"]   = new
    save_data(data)
    print("Stock market updated")

@bot.command(name="startmarket")
@mod_only()
async def startmarket_cmd(ctx):
    """Start the stock market (mod only, run once)."""
    global _stock_market_running
    if _stock_market_running:
        await ctx.send("Stock market is already running!")
        return
    data   = load_data()
    data   = ensure_keys(data)
    market = data.setdefault("stocks", {})
    for ticker in STOCKS_DEF:
        if ticker not in market:
            market[ticker] = {"price": random.randint(50, 200), "history": []}
    save_data(data)
    stock_market_loop.start()
    _stock_market_running = True
    await ctx.send(
        "**Stock market is now LIVE!**\n"
        "Prices update every hour.\n"
        "`?stocks` — view prices | `?buystock [TICKER] [shares]` | `?sellstock [TICKER] [shares]`"
    )

@bot.command(name="stocks")
async def stocks_cmd(ctx):
    """View current stock prices."""
    await log_command(ctx.guild, ctx.author, "stocks")
    data   = load_data()
    data   = ensure_keys(data)
    market = data.get("stocks", {})
    if not market:
        await ctx.send("Stock market not started yet. A mod can start it with `?startmarket`.")
        return
    uid  = str(ctx.author.id)
    port = data.setdefault("stock_portfolio", {}).get(uid, {})
    lines = []
    for ticker, info in STOCKS_DEF.items():
        if ticker not in market:
            continue
        price   = market[ticker]["price"]
        history = market[ticker].get("history", [])
        trend   = "📈" if (not history or price >= history[-1]) else "📉"
        owned   = port.get(ticker, 0)
        owned_str = f" (own: {owned})" if owned else ""
        lines.append(f"{info['emoji']} **{ticker}** — {info['name']}: **{price:,} pts/share** {trend}{owned_str}")
    embed = discord.Embed(title="Stock Market", description="\n".join(lines) or "No data.", color=discord.Color.blurple())
    embed.set_footer(text="Prices update hourly | ?buystock [TICKER] [shares] | ?sellstock [TICKER] [shares]")
    await ctx.send(embed=embed)

@bot.command(name="buystock")
async def buystock_cmd(ctx, ticker: str = None, shares: int = None):
    """Buy stock shares. ?buystock [TICKER] [shares]"""
    await log_command(ctx.guild, ctx.author, "buystock")
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    if not ticker or not shares or shares <= 0:
        await ctx.send("Usage: `?buystock VXON 5`")
        return
    ticker = ticker.upper()
    if ticker not in STOCKS_DEF:
        await ctx.send(f"Unknown ticker **{ticker}**. Use `?stocks`.")
        return
    data   = load_data()
    data   = ensure_keys(data)
    market = data.get("stocks", {})
    if ticker not in market:
        await ctx.send("Stock market not started yet.")
        return
    price = market[ticker]["price"]
    cost  = price * shares
    pts   = get_user_points(data, guild_id, uid)
    if pts < cost:
        await ctx.send(f"You need **{cost:,} points** but only have **{pts:,}**.")
        return
    set_user_points(data, guild_id, uid, pts - cost)
    port = data.setdefault("stock_portfolio", {}).setdefault(uid, {})
    port[ticker] = port.get(ticker, 0) + shares
    save_data(data)
    await ctx.send(f"Bought **{shares}x {ticker}** at **{price:,}/share** for **{cost:,} points**.")

@bot.command(name="sellstock")
async def sellstock_cmd(ctx, ticker: str = None, shares: int = None):
    """Sell stock shares. ?sellstock [TICKER] [shares]"""
    await log_command(ctx.guild, ctx.author, "sellstock")
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    if not ticker or not shares or shares <= 0:
        await ctx.send("Usage: `?sellstock VXON 5`")
        return
    ticker = ticker.upper()
    if ticker not in STOCKS_DEF:
        await ctx.send(f"Unknown ticker **{ticker}**.")
        return
    data   = load_data()
    data   = ensure_keys(data)
    market = data.get("stocks", {})
    if ticker not in market:
        await ctx.send("Stock market not started yet.")
        return
    port  = data.setdefault("stock_portfolio", {}).setdefault(uid, {})
    owned = port.get(ticker, 0)
    if owned < shares:
        await ctx.send(f"You only own **{owned}x {ticker}**.")
        return
    price  = market[ticker]["price"]
    earned = price * shares
    set_user_points(data, guild_id, uid, get_user_points(data, guild_id, uid) + earned)
    port[ticker] = owned - shares
    if port[ticker] == 0:
        del port[ticker]
    save_data(data)
    await ctx.send(f"Sold **{shares}x {ticker}** at **{price:,}/share** for **{earned:,} points**.")


# ============================================================
#   PAY  (?pay @user [amount])
# ============================================================

@bot.command(name="pay")
async def pay_cmd(ctx, target: discord.Member = None, amount: int = None):
    """Transfer points to another member. ?pay @user [amount]"""
    await log_command(ctx.guild, ctx.author, "pay")
    if not target or target.bot or target.id == ctx.author.id:
        await ctx.send("Usage: `?pay @user [amount]`")
        return
    if not amount or amount <= 0:
        await ctx.send("Amount must be greater than 0.")
        return
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    tid      = str(target.id)
    data     = load_data()
    data     = ensure_keys(data)
    pts      = get_user_points(data, guild_id, uid)
    if pts < amount:
        await ctx.send(f"You only have **{pts:,} points**.")
        return
    set_user_points(data, guild_id, uid, pts - amount)
    set_user_points(data, guild_id, tid, get_user_points(data, guild_id, tid) + amount)
    save_data(data)
    await ctx.send(f"✅ {ctx.author.mention} sent **{amount:,} points** to {target.mention}.")


# ============================================================
#   ROB  (?rob @user) — riskier steal
# ============================================================

ROB_COOLDOWN = 14400  # 4 hours
rob_cooldowns = {}

@bot.command(name="rob")
async def rob_cmd(ctx, target: discord.Member = None):
    """High-risk robbery. ?rob @user — bigger rewards, bigger penalties."""
    await log_command(ctx.guild, ctx.author, "rob")
    if not target or target.bot or target.id == ctx.author.id:
        await ctx.send("Usage: `?rob @user`")
        return
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    tid      = str(target.id)
    now      = time.time()
    cd_key   = f"{guild_id}_{uid}"
    if cd_key in rob_cooldowns and now - rob_cooldowns[cd_key] < ROB_COOLDOWN:
        rem = int(ROB_COOLDOWN - (now - rob_cooldowns[cd_key]))
        h, m = divmod(rem // 60, 60)
        await ctx.send(f"You can rob again in **{h}h {m}m**.")
        return
    data = load_data()
    data = ensure_keys(data)
    robber_pts = get_user_points(data, guild_id, uid)
    victim_pts = get_user_points(data, guild_id, tid)
    if victim_pts < 200:
        await ctx.send(f"{target.display_name} is too poor to rob (needs 200+ points).")
        return
    rob_cooldowns[cd_key] = now
    # 45% success chance (riskier than ?steal)
    success = random.random() < 0.45
    if success:
        stolen = random.randint(int(victim_pts * 0.10), int(victim_pts * 0.35))
        stolen = max(50, stolen)
        set_user_points(data, guild_id, uid, robber_pts + stolen)
        set_user_points(data, guild_id, tid, max(0, victim_pts - stolen))
        save_data(data)
        await ctx.send(
            f"🦹 {ctx.author.mention} successfully robbed {target.mention} "
            f"and got away with **{stolen:,} points**!"
        )
    else:
        fine = random.randint(int(robber_pts * 0.10), int(robber_pts * 0.25))
        fine = min(fine, robber_pts)
        set_user_points(data, guild_id, uid, robber_pts - fine)
        set_user_points(data, guild_id, tid, victim_pts + fine)
        save_data(data)
        await ctx.send(
            f"👮 {ctx.author.mention} got caught trying to rob {target.mention}! "
            f"You paid a fine of **{fine:,} points**."
        )


# ============================================================
#   RANK  (?rank)
# ============================================================

@bot.command(name="rank")
async def rank_cmd(ctx, member: discord.Member = None):
    """Show your exact position on the XP leaderboard."""
    await log_command(ctx.guild, ctx.author, "rank")
    target   = member or ctx.author
    guild_id = str(ctx.guild.id)
    data     = load_data()
    data     = ensure_keys(data)
    guild_xp = data["xp"].get(guild_id, {})
    if not guild_xp:
        await ctx.send("No XP data yet.")
        return
    sorted_members = sorted(guild_xp.items(), key=lambda x: x[1], reverse=True)
    uid = str(target.id)
    rank = next((i + 1 for i, (mid, _) in enumerate(sorted_members) if mid == uid), None)
    total_xp = guild_xp.get(uid, 0)
    total_members = len(sorted_members)
    if not rank:
        await ctx.send(f"{target.display_name} has no XP yet.")
        return
    percentile = round((1 - rank / total_members) * 100, 1)
    embed = discord.Embed(
        title=f"📊 {target.display_name}'s Rank",
        description=(
            f"**Rank:** #{rank} out of {total_members} members\n"
            f"**XP:** {total_xp:,}\n"
            f"**Top:** {percentile}% of the server"
        ),
        color=target.color or discord.Color.purple()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)


# ============================================================
#   WEEKLY LEADERBOARD  (?weekly)
# ============================================================

@tasks.loop(hours=1)
async def weekly_reset_loop():
    """Resets weekly XP/points every Monday at midnight UTC."""
    from datetime import timezone as tz_module
    now = datetime.now(tz_module.utc)
    if now.weekday() == 0 and now.hour == 0:
        data = load_data()
        data = ensure_keys(data)
        if data.get("weekly_reset", 0) < (now.timestamp() - 3600):
            data["weekly_xp"]     = {}
            data["weekly_points"] = {}
            data["weekly_reset"]  = now.timestamp()
            save_data(data)
            print("Weekly leaderboard reset.")

@weekly_reset_loop.before_loop
async def before_weekly():
    await bot.wait_until_ready()

@bot.command(name="weekly")
async def weekly_cmd(ctx):
    """Show the weekly XP leaderboard — resets every Monday."""
    await log_command(ctx.guild, ctx.author, "weekly")
    guild_id = str(ctx.guild.id)
    data     = load_data()
    data     = ensure_keys(data)
    weekly   = data.get("weekly_xp", {}).get(guild_id, {})
    if not weekly:
        await ctx.send("No weekly XP yet — chat to earn some!")
        return
    sorted_w = sorted(weekly.items(), key=lambda x: x[1], reverse=True)[:10]
    medals   = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines    = []
    for rank, (uid, xp) in enumerate(sorted_w, 1):
        m    = ctx.guild.get_member(int(uid))
        name = m.display_name if m else f"User {uid}"
        lines.append(f"{medals.get(rank, f'**{rank}.**')} {name} — **{xp:,} XP**")
    embed = discord.Embed(
        title="📅 Weekly XP Leaderboard",
        description="\n".join(lines),
        color=discord.Color.blue()
    )
    embed.set_footer(text="Resets every Monday at midnight UTC")
    await ctx.send(embed=embed)


# ============================================================
#   BALTOP  (?baltop)
# ============================================================

@bot.command(name="baltop")
async def baltop_cmd(ctx):
    """Dedicated points leaderboard."""
    await log_command(ctx.guild, ctx.author, "baltop")
    guild_id = str(ctx.guild.id)
    data     = load_data()
    data     = ensure_keys(data)
    pts_data = data["points"].get(guild_id, {})
    if not pts_data:
        await ctx.send("No points data yet.")
        return
    sorted_pts = sorted(pts_data.items(), key=lambda x: x[1], reverse=True)[:10]
    medals     = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines      = []
    for rank, (uid, pts) in enumerate(sorted_pts, 1):
        m    = ctx.guild.get_member(int(uid))
        name = m.display_name if m else f"User {uid}"
        lines.append(f"{medals.get(rank, f'**{rank}.**')} {name} — **{pts:,} points**")
    embed = discord.Embed(
        title="💰 Points Leaderboard",
        description="\n".join(lines),
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


# ============================================================
#   STREAK  (?streak)
# ============================================================

@bot.command(name="streak")
async def streak_cmd(ctx, member: discord.Member = None):
    """Show your daily streak, next tier bonus, and longest streak."""
    await log_command(ctx.guild, ctx.author, "streak")
    target   = member or ctx.author
    guild_id = str(ctx.guild.id)
    uid      = str(target.id)
    data     = load_data()
    data     = ensure_keys(data)
    streak_data = data.get("daily_streaks", {}).get(guild_id, {}).get(uid, {})
    current = streak_data.get("streak", 0) if isinstance(streak_data, dict) else int(streak_data)
    longest = streak_data.get("longest", current) if isinstance(streak_data, dict) else current
    # Calculate current multiplier
    if current >= 30:
        mult, next_tier, days_to_next = "3.0×", None, None
    elif current >= 14:
        mult, next_tier, days_to_next = "2.5×", 30, 30 - current
    elif current >= 7:
        mult, next_tier, days_to_next = "2.0×", 14, 14 - current
    elif current >= 3:
        mult, next_tier, days_to_next = "1.5×", 7, 7 - current
    else:
        mult, next_tier, days_to_next = "1.0×", 3, 3 - current
    desc = (
        f"**Current Streak:** {current} day{'s' if current != 1 else ''} 🔥\n"
        f"**Longest Streak:** {longest} day{'s' if longest != 1 else ''}\n"
        f"**Current Bonus:** {mult} daily rewards\n"
    )
    if next_tier:
        desc += f"\n**Next tier:** {days_to_next} more day{'s' if days_to_next != 1 else ''} for next bonus ({next_tier}+ days)"
    else:
        desc += "\n🏆 **Maximum bonus reached!** (30+ days)"
    embed = discord.Embed(
        title=f"🔥 {target.display_name}'s Streak",
        description=desc,
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)


# ============================================================
#   COOLDOWNS  (?cooldowns)
# ============================================================

@bot.command(name="cooldowns", aliases=["cd"])
async def cooldowns_cmd(ctx):
    """Show all your active cooldowns at a glance."""
    await log_command(ctx.guild, ctx.author, "cooldowns")
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    now      = time.time()
    data     = load_data()
    data     = ensure_keys(data)
    cd_key   = f"{guild_id}_{uid}"

    def fmt(remaining):
        if remaining <= 0:
            return "✅ Ready"
        h, rem = divmod(int(remaining), 3600)
        m, s   = divmod(rem, 60)
        if h:
            return f"⏳ {h}h {m}m"
        elif m:
            return f"⏳ {m}m {s}s"
        return f"⏳ {s}s"

    # Daily
    last_daily   = data.get("daily_claimed", {}).get(guild_id, {}).get(uid, 0)
    daily_rem    = max(0, 86400 - (now - last_daily))
    # Steal
    steal_key    = f"{guild_id}_{uid}"
    last_steal   = data.get("last_robbed", {}).get(steal_key, 0)
    steal_rem    = max(0, 18000 - (now - last_steal))
    # Rob
    rob_rem      = max(0, ROB_COOLDOWN - (now - rob_cooldowns.get(cd_key, 0)))
    # Beg
    beg_rem      = max(0, 60 - (now - beg_cooldowns.get(cd_key, 0)))
    # Crime
    crime_rem    = max(0, CRIME_COOLDOWN - (now - crime_cooldowns.get(cd_key, 0)))
    # Hunt
    hunt_cd_key  = f"{guild_id}_{uid}"
    hunt_rem     = max(0, HUNT_COOLDOWN - (now - hunt_cooldowns.get(hunt_cd_key, 0)))
    # Fish
    fish_rem     = max(0, FISH_COOLDOWN - (now - fish_cooldowns.get(cd_key, 0)))
    # Scratch
    scratch_rem  = max(0, SCRATCH_COOLDOWN - (now - scratch_cooldowns.get(cd_key, 0))) if cd_key in scratch_cooldowns else 0
    # Slots
    slots_rem    = max(0, SLOTS_COOLDOWN - (now - slots_cooldowns.get(cd_key, 0)))
    # Adventure
    adv_rem      = max(0, ADVENTURE_COOLDOWN - (now - adventure_cooldowns.get(cd_key, 0)))

    embed = discord.Embed(
        title=f"⏰ {ctx.author.display_name}'s Cooldowns",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Daily",     value=fmt(daily_rem),   inline=True)
    embed.add_field(name="Steal",     value=fmt(steal_rem),   inline=True)
    embed.add_field(name="Rob",       value=fmt(rob_rem),     inline=True)
    embed.add_field(name="Beg",       value=fmt(beg_rem),     inline=True)
    embed.add_field(name="Crime",     value=fmt(crime_rem),   inline=True)
    embed.add_field(name="Hunt",      value=fmt(hunt_rem),    inline=True)
    embed.add_field(name="Fish",      value=fmt(fish_rem),    inline=True)
    embed.add_field(name="Scratch",   value=fmt(scratch_rem), inline=True)
    embed.add_field(name="Slots",     value=fmt(slots_rem),   inline=True)
    embed.add_field(name="Adventure", value=fmt(adv_rem),     inline=True)
    await ctx.send(embed=embed)


# ============================================================
#   TRADE  (?trade @user [my_item] for [their_item])
# ============================================================

class TradeView(discord.ui.View):
    def __init__(self, proposer, target, my_item, their_item, guild_id):
        super().__init__(timeout=60)
        self.proposer   = proposer
        self.target     = target
        self.my_item    = my_item
        self.their_item = their_item
        self.guild_id   = guild_id
        self.done       = False

    @discord.ui.button(label="✅ Accept Trade", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("This trade isn't for you!", ephemeral=True)
            return
        if self.done:
            return
        self.done = True
        self.stop()
        data = load_data()
        data = ensure_keys(data)
        gid  = self.guild_id
        pid  = str(self.proposer.id)
        tid  = str(self.target.id)
        # Verify both still have items
        p_inv = get_inventory(data, gid, pid)
        t_inv = get_inventory(data, gid, tid)
        p_has = any(i.get("id") == self.my_item for i in p_inv)
        t_has = any(i.get("id") == self.their_item for i in t_inv)
        if not p_has:
            await interaction.response.edit_message(content=f"{self.proposer.mention} no longer has that item.", embed=None, view=None)
            return
        if not t_has:
            await interaction.response.edit_message(content=f"You no longer have that item.", embed=None, view=None)
            return
        # Remove from each and give to the other
        data["inventories"][gid][pid] = [i for i in p_inv if i.get("id") != self.my_item]
        data["inventories"][gid][tid] = [i for i in t_inv if i.get("id") != self.their_item]
        add_to_inventory(data, gid, pid, self.their_item)
        add_to_inventory(data, gid, tid, self.my_item)
        save_data(data)
        await interaction.response.edit_message(
            content=f"✅ Trade complete! {self.proposer.mention} got **{self.their_item}**, {self.target.mention} got **{self.my_item}**.",
            embed=None, view=None
        )

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("Not your trade!", ephemeral=True)
            return
        self.done = True
        self.stop()
        await interaction.response.edit_message(content="Trade declined.", embed=None, view=None)

    async def on_timeout(self):
        self.done = True


@bot.command(name="trade")
async def trade_cmd(ctx, target: discord.Member = None, my_item: str = None, *, rest: str = None):
    """Propose an item trade. ?trade @user [your_item] for [their_item]"""
    await log_command(ctx.guild, ctx.author, "trade")
    if not target or target.bot or target.id == ctx.author.id:
        await ctx.send("Usage: `?trade @user [your_item_id] for [their_item_id]`")
        return
    if not my_item or not rest or " for " not in (my_item + " " + rest).lower():
        await ctx.send("Usage: `?trade @user [your_item_id] for [their_item_id]`\nCheck `?inventory` for item IDs.")
        return
    full = f"{my_item} {rest}"
    if " for " not in full.lower():
        await ctx.send("Format: `?trade @user item1 for item2`")
        return
    parts = full.lower().split(" for ", 1)
    my_item_id    = parts[0].strip()
    their_item_id = parts[1].strip()
    guild_id = str(ctx.guild.id)
    data     = load_data()
    data     = ensure_keys(data)
    p_inv = get_inventory(data, guild_id, str(ctx.author.id))
    t_inv = get_inventory(data, guild_id, str(target.id))
    if not any(i.get("id") == my_item_id for i in p_inv):
        await ctx.send(f"You don't have **{my_item_id}** in your inventory.")
        return
    if not any(i.get("id") == their_item_id for i in t_inv):
        await ctx.send(f"{target.display_name} doesn't have **{their_item_id}**.")
        return
    embed = discord.Embed(
        title="🔄 Trade Proposal",
        description=(
            f"{ctx.author.mention} wants to trade with {target.mention}\n\n"
            f"**They offer:** `{my_item_id}`\n"
            f"**They want:** `{their_item_id}`\n\n"
            f"{target.mention} — accept or decline within 60 seconds."
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=TradeView(ctx.author, target, my_item_id, their_item_id, guild_id))


# ============================================================
#   GIFT  (?gift @user [item])
# ============================================================

@bot.command(name="gift")
async def gift_cmd(ctx, target: discord.Member = None, *, item_id: str = None):
    """Gift an item to another member. ?gift @user [item_id]"""
    await log_command(ctx.guild, ctx.author, "gift")
    if not target or target.bot or target.id == ctx.author.id:
        await ctx.send("Usage: `?gift @user [item_id]`")
        return
    if not item_id:
        await ctx.send("Specify an item ID. Check `?inventory` for your items.")
        return
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    tid      = str(target.id)
    data     = load_data()
    data     = ensure_keys(data)
    inv      = get_inventory(data, guild_id, uid)
    item_entry = next((i for i in inv if i.get("id") == item_id.lower()), None)
    if not item_entry:
        await ctx.send(f"You don't have **{item_id}** in your inventory.")
        return
    data["inventories"][guild_id][uid] = [i for i in inv if i != item_entry]
    add_to_inventory(data, guild_id, tid, item_id.lower())
    save_data(data)
    await ctx.send(f"🎁 {ctx.author.mention} gifted **{item_id}** to {target.mention}!")


# ============================================================
#   TRIVIA CATEGORIES  (?trivia [category])
# ============================================================

@bot.command(name="trivia")
@mod_only()
async def trivia_cmd(ctx, category: str = None):
    """Start a trivia question. Optionally specify a category."""
    await log_command(ctx.guild, ctx.author, "trivia", category or "random")
    guild_id = str(ctx.guild.id)
    if guild_id in active_trivia:
        await ctx.send("A trivia question is already active!")
        return
    # Pick question pool
    if category and category.lower() in TRIVIA_CATEGORIES:
        pool = TRIVIA_CATEGORIES[category.lower()]
        cat_label = category.title()
    elif category == "list" or category == "categories":
        cats = ", ".join(f"`{c}`" for c in TRIVIA_CATEGORIES.keys())
        await ctx.send(f"Available categories: {cats}\nOr use `?trivia` for a random question.")
        return
        return
    else:
        pool = TRIVIA_QUESTIONS
        cat_label = "General"
    question = random.choice(pool)
    hints    = question.get("hints", [])
    active_trivia[guild_id] = {
        "answer":     question["a"],
        "hints":      hints,
        "hint_index": 0,
        "channel_id": str(ctx.channel.id),
        "question":   question["q"],
    }
    embed = discord.Embed(
        title=f"🧠 Trivia — {cat_label}",
        description=(
            f"**{question['q']}**\n\n"
            f"First to answer wins **{TRIVIA_XP_REWARD} XP** and **{TRIVIA_POINTS_REWARD} points**!\n"
            f"Hints appear after wrong answers. You have {TRIVIA_TIMEOUT} seconds!\n\n"
            f"💬 **Just type your answer in the chat!**"
        ),
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)
    asyncio.create_task(_trivia_timeout(guild_id, ctx.channel, TRIVIA_TIMEOUT))

async def _trivia_timeout(guild_id, channel, timeout):
    await asyncio.sleep(timeout)
    if guild_id in active_trivia:
        ans = active_trivia.pop(guild_id)["answer"]
        await channel.send(f"⏰ Time is up! The answer was **{ans.title()}**.")


# ============================================================
#   SPIN  (?spin — daily free spin wheel)
# ============================================================

SPIN_REWARDS = [
    (500,   "🥉 Common Spin",    discord.Color.greyple(), 45),
    (1000,  "🥈 Good Spin",      discord.Color.blue(),    28),
    (2500,  "🥇 Great Spin",     discord.Color.gold(),    15),
    (5000,  "💎 Rare Spin",      discord.Color.purple(),   8),
    (10000, "🌟 Legendary Spin", discord.Color.orange(),   3),
    (0,     "💨 Empty Spin",     discord.Color.dark_grey(), 1),
]

@bot.command(name="spin")
async def spin_cmd(ctx):
    """Daily free spin wheel. Once per day."""
    await log_command(ctx.guild, ctx.author, "spin")
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    now      = time.time()
    data     = load_data()
    data     = ensure_keys(data)
    last     = data.get("spin_claimed", {}).get(guild_id, {}).get(uid, 0)
    if now - last < 86400:
        next_spin = int(last + 86400)
        await ctx.send(f"You already spun today! Next spin: <t:{next_spin}:R>")
        return
    pts_val, label, color, _ = random.choices(SPIN_REWARDS, weights=[r[3] for r in SPIN_REWARDS], k=1)[0]
    data.setdefault("spin_claimed", {}).setdefault(guild_id, {})[uid] = now
    if pts_val > 0:
        set_user_points(data, guild_id, uid, get_user_points(data, guild_id, uid) + pts_val)
    save_data(data)
    # Animated spin
    symbols = ["🎰", "🎲", "🎪", "🎡", "🎢"]
    msg     = await ctx.send(f"🎡 Spinning...")
    for s in symbols:
        await msg.edit(content=f"{s} Spinning...")
        await asyncio.sleep(0.4)
    if pts_val > 0:
        embed = discord.Embed(
            title=f"🎡 {label}!",
            description=f"You won **{pts_val:,} points**!",
            color=color
        )
    else:
        embed = discord.Embed(
            title="💨 Better luck tomorrow!",
            description="You won nothing this time. Come back tomorrow!",
            color=color
        )
    await msg.edit(content=None, embed=embed)


# ============================================================
#   HIGH-LOW  (?highlow [amount])
# ============================================================

@bot.command(name="highlow", aliases=["hl"])
async def highlow_cmd(ctx, amount: int = None):
    """Guess if the next number is higher or lower. ?highlow [amount]"""
    await log_command(ctx.guild, ctx.author, "highlow")
    if not amount or amount <= 0:
        await ctx.send("Usage: `?highlow [amount]`")
        return
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    data     = load_data()
    data     = ensure_keys(data)
    pts      = get_user_points(data, guild_id, uid)
    if pts < amount:
        await ctx.send(f"You only have **{pts:,} points**.")
        return
    current = random.randint(1, 100)
    class HLView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=20)
            self.done = False
        async def _resolve(self, interaction, guess):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("Not your game!", ephemeral=True)
                return
            if self.done:
                return
            self.done = True
            self.stop()
            next_num = random.randint(1, 100)
            correct = (guess == "higher" and next_num > current) or                       (guess == "lower"  and next_num < current) or                       next_num == current
            d2 = load_data()
            d2 = ensure_keys(d2)
            if correct:
                set_user_points(d2, guild_id, uid, get_user_points(d2, guild_id, uid) + amount)
                save_data(d2)
                await interaction.response.edit_message(
                    content=f"**{current}** → **{next_num}** — Correct! +**{amount:,} points**!",
                    view=None
                )
            else:
                set_user_points(d2, guild_id, uid, max(0, get_user_points(d2, guild_id, uid) - amount))
                save_data(d2)
                await interaction.response.edit_message(
                    content=f"**{current}** → **{next_num}** — Wrong! -**{amount:,} points**.",
                    view=None
                )
        @discord.ui.button(label="📈 Higher", style=discord.ButtonStyle.green)
        async def higher(self, interaction, button): await self._resolve(interaction, "higher")
        @discord.ui.button(label="📉 Lower", style=discord.ButtonStyle.red)
        async def lower(self, interaction, button):  await self._resolve(interaction, "lower")
        async def on_timeout(self): self.done = True
    await ctx.send(
        f"🎲 The number is **{current}**. Will the next number be higher or lower?\nBet: **{amount:,} points**",
        view=HLView()
    )


# ============================================================
#   BLACKJACK  (?blackjack [amount])
# ============================================================

def _bj_card():
    ranks = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
    suits = ["♠","♥","♦","♣"]
    return random.choice(ranks) + random.choice(suits)

def _bj_value(cards):
    total, aces = 0, 0
    for c in cards:
        rank = c[:-1]
        if rank in ("J","Q","K"):
            total += 10
        elif rank == "A":
            aces  += 1
            total += 11
        else:
            total += int(rank)
    while total > 21 and aces:
        total -= 10
        aces  -= 1
    return total

@bot.command(name="blackjack", aliases=["bj"])
async def blackjack_cmd(ctx, amount: int = None):
    """Play blackjack vs the bot. ?blackjack [amount] (alias: ?bj)"""
    await log_command(ctx.guild, ctx.author, "blackjack")
    if not amount or amount <= 0:
        await ctx.send("Usage: `?blackjack [amount]` (alias: `?bj`)")
        return
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    data     = load_data()
    data     = ensure_keys(data)
    pts      = get_user_points(data, guild_id, uid)
    if pts < amount:
        await ctx.send(f"You only have **{pts:,} points**.")
        return

    player = [_bj_card(), _bj_card()]
    dealer = [_bj_card(), _bj_card()]

    def hand_str(cards, hide_second=False):
        if hide_second:
            return f"{cards[0]}  🂠  (value: {_bj_value([cards[0]])}+?)"
        return f"{' '.join(cards)}  (value: **{_bj_value(cards)}**)"

    def make_embed(done=False, result=""):
        e = discord.Embed(title="🃏 Blackjack", color=discord.Color.green())
        e.add_field(name="Your Hand",    value=hand_str(player),           inline=False)
        e.add_field(name="Dealer's Hand",value=hand_str(dealer, hide_second=not done), inline=False)
        if result:
            e.add_field(name="Result", value=result, inline=False)
        return e

    class BJView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.done = False
        async def _finish(self, interaction, stood=False):
            if self.done:
                return
            self.done = True
            self.stop()
            # Dealer draws to 17
            while _bj_value(dealer) < 17:
                dealer.append(_bj_card())
            pv, dv = _bj_value(player), _bj_value(dealer)
            d2 = load_data()
            d2 = ensure_keys(d2)
            if pv > 21:
                result = f"💥 Bust! You lose **{amount:,} points**."
                set_user_points(d2, guild_id, uid, max(0, get_user_points(d2, guild_id, uid) - amount))
            elif dv > 21 or pv > dv:
                result = f"🏆 You win **{amount:,} points**!"
                set_user_points(d2, guild_id, uid, get_user_points(d2, guild_id, uid) + amount)
            elif pv == dv:
                result = "🤝 Push — bet returned."
            else:
                result = f"💸 Dealer wins. You lose **{amount:,} points**."
                set_user_points(d2, guild_id, uid, max(0, get_user_points(d2, guild_id, uid) - amount))
            save_data(d2)
            await interaction.response.edit_message(embed=make_embed(done=True, result=result), view=None)
        @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
        async def hit(self, interaction, button):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("Not your game!", ephemeral=True)
                return
            player.append(_bj_card())
            if _bj_value(player) >= 21:
                await self._finish(interaction)
            else:
                await interaction.response.edit_message(embed=make_embed(), view=self)
        @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
        async def stand(self, interaction, button):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("Not your game!", ephemeral=True)
                return
            await self._finish(interaction, stood=True)
        async def on_timeout(self): self.done = True

    # Check for instant blackjack
    if _bj_value(player) == 21:
        winnings = int(amount * 1.5)
        data2 = load_data(); data2 = ensure_keys(data2)
        set_user_points(data2, guild_id, uid, get_user_points(data2, guild_id, uid) + winnings)
        save_data(data2)
        await ctx.send(embed=make_embed(done=True, result=f"🃏 Blackjack! You win **{winnings:,} points**! (1.5×)"))
        return

    await ctx.send(embed=make_embed(), view=BJView())


# ============================================================
#   WORDLE  (?wordle)
# ============================================================

WORDLE_WORDS = [
    "crane","slate","audio","canoe","raise","stare","alone","store","share","horse",
    "flame","blade","grace","plane","price","pride","prime","crime","climb","claim",
    "brave","brake","grade","grape","graze","glare","flare","place","space","trace",
    "badge","cadge","dance","fence","hence","hence","lance","mince","pence","since",
    "storm","scorn","sworn","short","sport","spore","snore","shore","score","smoke",
    "stone","stove","stoke","stole","spoke","slope","slone","shone","phone","prone",
    "groan","grown","brown","crown","drown","frown","clown","blown","shown","known",
    "think","drink","blink","brink","clink","stink","shrink","sting","swing","bring",
]

def _get_daily_word():
    """Same word for everyone in the server each day."""
    from datetime import date
    seed = int(date.today().strftime("%Y%m%d"))
    rng  = random.Random(seed)
    return rng.choice(WORDLE_WORDS).upper()

def _wordle_display(guesses, word):
    """Build the emoji display grid."""
    lines = []
    for guess in guesses:
        row = ""
        for i, ch in enumerate(guess):
            if ch == word[i]:
                row += "🟩"
            elif ch in word:
                row += "🟨"
            else:
                row += "⬛"
        lines.append(f"{row}  {guess}")
    return "\n".join(lines) if lines else "*No guesses yet*"

@bot.command(name="wordle")
@bot.command(name="clanwar")
async def clanwar_cmd(ctx, *, target_clan: str = None):
    """
    Challenge another clan to war!
    ?clanwar [clan name] — declare war
    ?clanwar join        — join your clan's ongoing war
    ?clanwar status      — check war standings
    """
    await log_command(ctx.guild, ctx.author, "clanwar", target_clan or "")
    guild_id = str(ctx.guild.id)
    uid      = str(ctx.author.id)
    data     = load_data()
    data     = ensure_keys(data)
    members  = data.get("clan_members", {}).get(guild_id, {})
    clans    = data.get("clans", {}).get(guild_id, {})
    wars     = data.setdefault("clan_wars", {}).setdefault(guild_id, {})

    my_clan  = members.get(uid)
    if not my_clan:
        await ctx.send("You're not in a clan! Join one with `?clan join [name]`.")
        return

    if not target_clan or target_clan.lower() == "status":
        # Show war status
        war = wars.get(my_clan)
        if not war:
            await ctx.send(f"**{my_clan}** has no active war. Challenge a clan with `?clanwar [clan name]`.")
            return
        opp   = war["opponent"]
        my_s  = war["scores"].get(my_clan, 0)
        opp_s = war["scores"].get(opp, 0)
        ends  = f"<t:{int(war['ends_at'])}:R>"
        embed = discord.Embed(title=f"⚔️ Clan War: {my_clan} vs {opp}", color=discord.Color.red())
        embed.add_field(name=my_clan, value=f"**{my_s}** battles won", inline=True)
        embed.add_field(name="vs", value="⚔️", inline=True)
        embed.add_field(name=opp,  value=f"**{opp_s}** battles won", inline=True)
        embed.add_field(name="Ends", value=ends, inline=False)
        await ctx.send(embed=embed)
        return

    if target_clan.lower() == "join":
        war = wars.get(my_clan)
        if not war:
            await ctx.send("No active war for your clan.")
            return
        if time.time() > war["ends_at"]:
            await ctx.send("The war has ended.")
            return
        opp = war["opponent"]
        # Battle another clan member
        opp_members = [m for m, c in members.items() if c == opp]
        if not opp_members:
            await ctx.send("No members to battle in the opposing clan.")
            return
        result = random.choice(["win", "win", "loss"])
        if result == "win":
            war["scores"][my_clan] = war["scores"].get(my_clan, 0) + 1
            msg = f"⚔️ {ctx.author.mention} fought for **{my_clan}** and **won**! +1 point."
        else:
            war["scores"][opp] = war["scores"].get(opp, 0) + 1
            msg = f"⚔️ {ctx.author.mention} fought for **{my_clan}** and **lost**. +1 for {opp}."
        save_data(data)
        await ctx.send(msg)
        return

    # Declare war
    match = next((k for k in clans if k.lower() == target_clan.lower()), None)
    if not match:
        await ctx.send(f"Clan **{target_clan}** not found.")
        return
    if match == my_clan:
        await ctx.send("You can't war your own clan.")
        return
    if my_clan in wars or match in wars:
        await ctx.send("One of the clans is already in a war.")
        return

    ends_at = time.time() + 86400  # 24 hour war
    war_entry = {
        "opponent": match,
        "scores":   {my_clan: 0, match: 0},
        "ends_at":  ends_at,
    }
    wars[my_clan] = war_entry
    wars[match]   = {**war_entry, "opponent": my_clan}
    save_data(data)
    await ctx.send(
        f"⚔️ **Clan War declared!** {my_clan} vs {match}\n"
        f"War lasts 24 hours. Members use `?clanwar join` to fight!\n"
        f"Ends: <t:{int(ends_at)}:R>"
    )


# ============================================================
#   SLOWMODE  (?slowmode [seconds]) — MOD
# ============================================================

@bot.command(name="slowmode")
@mod_only()
async def slowmode_cmd(ctx, seconds: int = None):
    """Set channel slowmode. ?slowmode [seconds] | ?slowmode 0 to remove."""
    await log_command(ctx.guild, ctx.author, "slowmode")
    if seconds is None:
        await ctx.send("Usage: `?slowmode [seconds]` — use 0 to remove slowmode.")
        return
    seconds = max(0, min(seconds, 21600))  # Discord max is 6 hours
    await ctx.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        await ctx.send("⏱️ Slowmode removed from this channel.")
    else:
        await ctx.send(f"⏱️ Slowmode set to **{seconds} seconds** in this channel.")
    await log_action(ctx.guild, "Slowmode", None, ctx.author, f"{seconds}s in #{ctx.channel.name}")


# ============================================================
#   MOD NOTE  (?note @user [text]) — MOD
# ============================================================

@bot.command(name="note")
@mod_only()
async def note_cmd(ctx, member: discord.Member = None, *, text: str = None):
    """Add a private mod note to a user. Only mods can see it. ?note @user [text]"""
    await log_command(ctx.guild, ctx.author, "note")
    if not member or not text:
        await ctx.send("Usage: `?note @user [note text]`")
        return
    guild_id = str(ctx.guild.id)
    uid      = str(member.id)
    data     = load_data()
    data     = ensure_keys(data)
    data.setdefault("mod_notes", {}).setdefault(guild_id, {}).setdefault(uid, [])
    data["mod_notes"][guild_id][uid].append({
        "note":      text,
        "mod":       str(ctx.author),
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
    })
    save_data(data)
    await ctx.send(f"📝 Note added for **{member.display_name}**.", delete_after=10)


# ============================================================
#   HISTORY  (?history @user) — MOD
# ============================================================

@bot.command(name="history")
@mod_only()
async def history_cmd(ctx, member: discord.Member = None):
    """Full mod history for a user — warnings, timeouts, notes, automod."""
    await log_command(ctx.guild, ctx.author, "history")
    if not member:
        await ctx.send("Usage: `?history @user`")
        return
    guild_id = str(ctx.guild.id)
    uid      = str(member.id)
    data     = load_data()
    data     = ensure_keys(data)
    warnings = data.get("warnings", {}).get(guild_id, {}).get(uid, [])
    notes    = data.get("mod_notes", {}).get(guild_id, {}).get(uid, [])
    embed = discord.Embed(
        title=f"📋 Mod History — {member.display_name}",
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:D>", inline=True)
    embed.add_field(name="Joined Server",   value=f"<t:{int(member.joined_at.timestamp())}:D>" if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="Total Warnings",  value=str(len(warnings)), inline=True)
    if warnings:
        warn_lines = []
        for w in warnings[-5:]:
            warn_lines.append(f"• `{w.get('timestamp','?')}` — {w.get('reason','?')[:60]} (by {w.get('moderator','?')})")
        embed.add_field(name=f"Last {min(5,len(warnings))} Warning(s)", value="\n".join(warn_lines), inline=False)
    if notes:
        note_lines = []
        for n in notes[-3:]:
            note_lines.append(f"• `{n.get('timestamp','?')}` — {n.get('note','?')[:60]} (by {n.get('mod','?')})")
        embed.add_field(name=f"Mod Notes ({len(notes)})", value="\n".join(note_lines), inline=False)
    if not warnings and not notes:
        embed.description = "✅ No warnings or notes on record."
    await ctx.send(embed=embed)

# ============================================================
#   MODSTATS  (?modstats) — MOD
# ============================================================

@bot.command(name="modstats")
@mod_only()
async def modstats_cmd(ctx):
    """AutoMod statistics — actions taken, top offenders."""
    await log_command(ctx.guild, ctx.author, "modstats")
    guild_id = str(ctx.guild.id)
    data     = load_data()
    data     = ensure_keys(data)
    warnings = data.get("warnings", {}).get(guild_id, {})
    # Count automod vs manual warns
    automod_count  = 0
    manual_count   = 0
    user_warn_counts = {}
    for uid, warns in warnings.items():
        for w in warns:
            if "[AutoMod]" in w.get("reason", ""):
                automod_count += 1
            else:
                manual_count  += 1
        user_warn_counts[uid] = len(warns)
    top_offenders = sorted(user_warn_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    embed = discord.Embed(title="📊 Mod Statistics", color=discord.Color.orange())
    embed.add_field(name="AutoMod Actions",  value=str(automod_count), inline=True)
    embed.add_field(name="Manual Warnings",  value=str(manual_count),  inline=True)
    embed.add_field(name="Total Warned Users", value=str(len(warnings)), inline=True)
    if top_offenders:
        lines = []
        for uid, count in top_offenders:
            m    = ctx.guild.get_member(int(uid))
            name = m.display_name if m else f"User {uid}"
        embed.add_field(name="Top Offenders", value="\n".join(lines), inline=False)
    await ctx.send(embed=embed)


# ============================================================
#   LOCKCATEGORY  (?lockcategory) — MOD
# ============================================================

@bot.command(name="lockcategory")
@mod_only()
async def lockcategory_cmd(ctx):
    """Lock every text channel in this category. Emergency use."""
    await log_command(ctx.guild, ctx.author, "lockcategory")
    if not ctx.channel.category:
        await ctx.send("This channel isn't in a category.")
        return
    category = ctx.channel.category
    locked   = 0
    for channel in category.text_channels:
        if channel == ctx.channel:
            continue
        try:
            ow = channel.overwrites_for(ctx.guild.default_role)
            ow.send_messages = False
            await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
            locked += 1
        except discord.Forbidden:
            pass
    await ctx.send(f"🔒 Locked **{locked}** channels in **{category.name}**.")
    await log_action(ctx.guild, "Lock Category", None, ctx.author, f"Locked {category.name}")


# ============================================================
#   CLEARCHANNEL  (?clearchannel) — MOD
# ============================================================

@bot.command(name="clearchannel")
@mod_only()
async def clearchannel_cmd(ctx):
    """Recreate this channel with the same settings — purges all messages."""
    await log_command(ctx.guild, ctx.author, "clearchannel")
    ch   = ctx.channel
    pos  = ch.position
    try:
        new_ch = await ch.clone(reason=f"Channel cleared by {ctx.author}")
        await new_ch.edit(position=pos)
        await ch.delete(reason=f"Cleared by {ctx.author}")
        await new_ch.send(f"🧹 Channel cleared by **{ctx.author.display_name}**.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to do that.")
    await log_action(ctx.guild, "Clear Channel", None, ctx.author, f"#{ch.name}")


# ============================================================
#   SOFTBAN  (?softban @user [reason]) — SENIOR MOD
# ============================================================

@bot.command(name="softban")
@mod_only()
async def softban_cmd(ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
    """Ban then immediately unban to delete messages. ?softban @user [reason]"""
    await log_command(ctx.guild, ctx.author, "softban")
    senior = ["Managers", "Ahmed"]
    if not any(r.name in senior for r in ctx.author.roles) and not ctx.author.guild_permissions.administrator:
        await ctx.send("Only **Managers** and **Ahmed** can use softban.")
        return
    if not member:
        await ctx.send("Usage: `?softban @user [reason]`")
        return
    try:
        await ctx.guild.ban(member, reason=f"Softban by {ctx.author}: {reason}", delete_message_days=7)
        await ctx.guild.unban(member, reason="Softban — immediate unban")
        await ctx.send(f"🔨 **{member.display_name}** has been softbanned. Their recent messages have been deleted.")
        await log_action(ctx.guild, "Softban", member, ctx.author, reason)
    except discord.Forbidden:
        await ctx.send("I don't have permission to ban that member.")

# ============================================================
#   RUN BOT
# ============================================================

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise RuntimeError("FATAL: TOKEN environment variable is not set. Set it before starting the bot.")

bot.run(TOKEN)
