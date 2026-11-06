Vexon's Bot 🤖
A feature-rich, single-file Discord community bot built with Python, discord.py, and aiohttp for Vexon's Community.

It combines moderation, automated safety tools, levelling, a virtual economy, games, and community engagement features in one project. The source is published for learning, experimentation, and further development. Everything is editable: you can adapt the bot to your own community, content creators, preferred features, and game balance. Some options are in config.json, while others are Python constants or logic in ahmed_bot.py.
Project status: Originally designed around one Discord community. The code is available publicly, but using it in another server requires adapting server-specific roles, channels, stream accounts, and configuration. It is not a plug-and-play multi-server service.

Features
Area	Examples
🛡️ Moderation	Warnings, bans, kicks, timeouts, temporary bans, channel locks, slowmode, moderation logs
🚨 Safety	AutoMod, anti-raid protection, verification, suspicious-activity monitoring, lockdown tools
📈 Progression	XP, levels, leaderboards, prestige, achievements, quests
🪙 Economy	Daily rewards, jobs, bank and savings cards, shop, inventory, stocks, trading and virtual-currency activities
🎮 Games	Trivia, Wordle, rock-paper-scissors, blackjack, high-low, dungeon adventures and other minigames
👥 Community	Tickets, birthdays, polls, suggestions, reaction roles, giveaways, reminders, clans
📣 Notifications	Streaming and upload checks for Twitch, Kick, YouTube and TikTok
🔧 Administration	Server setup commands, role tools, announcements, configurable command prefix and command toggles


The bot uses prefix commands, with ? as the default prefix. Examples:
?help
?profile
?daily
?shop
?trivia
?dungeon
?warn
?setup
Some commands require moderator, manager, administrator or community-specific roles. Run ?help for the command list available in your server.
Technology
- Python 3.10+
- discord.py
- aiohttp
- JSON files for configuration and persistent bot data
- Async tasks for scheduled checks and housekeeping
The runtime is primarily contained in [`ahmed_bot.py`](./ahmed_bot.py), with sections labelled for navigation.
Getting started
1. Create a Discord application
1. Open the Discord Developer Portal and create an application.
2. Add a bot and obtain its token. Keep the token private.
3. Under the bot's privileged gateway intents, enable Message Content Intent and Server Members Intent.
4. Invite the bot to your server using an OAuth2 URL with the bot scope and the permissions appropriate to the features you intend to use. Avoid granting Administrator unless genuinely required.
2. Download and install dependencies
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
python -m venv .venv
Activate the environment:
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
Install dependencies:
python -m pip install -r requirements.txt
3. Configure the bot
Copy config.example.json to config.json:
cp config.example.json config.json
On Windows, copy the file manually or use Copy-Item config.example.json config.json.

Edit config.json to match your Discord server. The bot expects channel names, role names, XP settings, and reaction-role configuration. Additional features refer to channel and role constants directly in ahmed_bot.py. The personalisation guide below explains where to change them.

Set your Discord bot token as an environment variable, not in the source file:
# macOS / Linux
export TOKEN="YOUR_DISCORD_BOT_TOKEN"
export OWNER_ID="YOUR_DISCORD_USER_ID"
export HOME_GUILD_ID="YOUR_DISCORD_SERVER_ID"

# Windows PowerShell
$env:TOKEN="YOUR_DISCORD_BOT_TOKEN"
$env:OWNER_ID="YOUR_DISCORD_USER_ID"
$env:HOME_GUILD_ID="YOUR_DISCORD_SERVER_ID"
Variable	Required?	Purpose
TOKEN	Yes	Discord bot token
OWNER_ID	Optional	Owner ID used by owner alerts and owner-specific functionality
HOME_GUILD_ID	Recommended	Home server ID; enables the home-server guard and some server-specific functionality
DATA_DIR	Optional	Location of persistent config.json and data.json files; defaults to the script directory


Note: If you set DATA_DIR, put your actual config.json there. On first use, the bot attempts to copy an existing config.json or data.json from the script directory into an empty data directory.
4. Personalise it for your server
You do not need to use Vexon's channels, streaming accounts, names, or settings. They are examples from the server the bot was originally built for. Replace them with your own before deploying. The bot is open source, so you are free to change, remove, or extend features under the MIT licence.

There are three places to make changes:
Where	What to change	Restart needed?
config.json	Prefix, welcome channel, level-up channel, moderation logs, role channel, XP-per-message, XP cooldown, moderator role names, reaction-role configuration	Restart recommended; some configuration is read dynamically
ahmed_bot.py → [SECTION 03]	Twitch, Kick, YouTube, TikTok accounts, announcement channels, owner alerts, XP/points rewards, security thresholds, role names, and other constants	Yes
Other labelled sections of ahmed_bot.py	Commands, game rules, shop items, trivia, automation, moderation logic and advanced behaviour	Yes


Change the Twitch, Kick, YouTube and TikTok accounts
Open ahmed_bot.py, find [SECTION 03] STATIC CONSTANTS & TUNING VALUES, and replace the account names and links with your own:
# Example accounts: replace these with your own
TWITCH_CHANNEL = "your_twitch_username"
TWITCH_LINK = "https://www.twitch.tv/your_twitch_username"

KICK_CHANNEL = "your-kick-username"
KICK_LINK = "https://kick.com/your-kick-username"

YOUTUBE_LIVE_CHANNEL = "your_youtube_name"  # label used in logs
YOUTUBE_LIVE_LINK = "https://www.youtube.com/@your_youtube_handle"
YOUTUBE_HANDLE = "your_youtube_handle"
YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@your_youtube_handle"

TIKTOK_USERNAME = "your_tiktok_username"
TIKTOK_URL = "https://www.tiktok.com/@your_tiktok_username"

# These are Discord channel NAMES, without the # prefix
LIVE_ANNOUNCE_CHANNEL = "live-announcements"
UPLOAD_CHANNEL = "upload-announcement"
Important: Set both the usernames and their links. The bot does not automatically generate the correct URL for every platform. Keep Discord channel names exactly matched to the channels on your server. YOUTUBE_LIVE_CHANNEL is a label; the YouTube API checker uses YOUTUBE_CHANNEL_ID (or tries to resolve it) to identify the channel.

To enable the corresponding API-based checks, set these optional environment variables on your computer or hosting provider:
Environment variable	Used for
TWITCH_CLIENT_ID	Twitch API client ID
TWITCH_CLIENT_SECRET	Twitch API client secret
YOUTUBE_API_KEY	YouTube Data API v3, including live checks and upload fallback
YOUTUBE_CHANNEL_ID	The actual YouTube channel ID (recommended for reliable identification)


Create your own API credentials with the respective platforms. Never commit credentials to GitHub. The Kick and TikTok checkers use publicly accessible endpoints/pages and may need maintenance if those services change them. Changing a username alone does not guarantee the platform check will continue working.

Do not want streaming or upload announcements? You are free to remove or disable those background tasks in the source. Search for check_twitch, check_kick, check_youtube_live, check_youtube_uploads and check_tiktok and review their task scheduling/startup code before editing it. There is no universal feature-on/off switch in config.json in the current version.
Change your Discord channels, roles and command prefix
Copy the example config as described above, then edit config.json, for example:
{
  "prefix": "!",
  "welcome_channel": "welcome",
  "level_up_channel": "level-ups",
  "mod_log_channel": "staff-logs",
  "get_roles_channel": "self-roles",
  "xp_per_message": 10,
  "xp_cooldown_seconds": 30,
  "reaction_roles": {},
  "mod_roles": ["Moderator", "Admin"]
}
This is an example, not the file you must use. Keep all the expected keys. Some other channel and role names are hard-coded in ahmed_bot.py rather than config.json; search SECTION 03 and the relevant feature sections for names such as BOT_LOGS_CHANNEL, TICKET_SUPPORT_ROLES, APPEAL_REVIEWER_ROLES, COOLDOWN_EXEMPT_ROLES, and LEVEL_ROLES. Also search for literal "Vexon", "Managers", and "Mod": several command permissions and messages check those names directly. Changing mod_roles alone will not update every permission check.
Change economy, levelling, games and community features
You can adjust the bot's behaviour to fit your members:
Feature	Where to look	Examples
XP, levels and rewards	config.json, Sections 03 and 08, levelling commands	XP per message, cooldowns, level formula, reward amounts
Virtual economy and shop	Section 03, SHOP_ITEMS in Section 04, economy command sections	Prices, items, bank limits, daily rewards, jobs, stocks
Trivia and word games	TRIVIA_QUESTIONS, TRIVIA_CATEGORIES, WORD_OF_THE_DAY_LIST	Replace questions, answers and daily words
Dungeon gameplay	DUNGEON_TIERS, DUNGEON_ENCOUNTERS	Difficulty, encounters, rewards, cooldowns
Moderation and anti-raid	Section 03, AutoMod section, moderation commands	Thresholds, forbidden content, role access, actions
Tickets, birthdays, polls and giveaways	Corresponding labelled feature sections	Channels, support roles, behaviours, responses
Commands and bot messages	Each bot.command(...) definition	Change wording, add commands, remove unneeded commands


The source has searchable [SECTION XX] headings and a table of contents at the top, making it easier to locate features. A code editor's Find feature (Ctrl+F / Cmd+F) is the fastest way to locate a setting or existing server name.

After changing behaviour, test the bot in a private Discord server and check its permissions before deploying to a public community. Automatic moderation, lockdown, bans, and role changes deserve extra care.
5. Start the bot
python ahmed_bot.py
Then try ?help in an appropriate channel.
Hosting
This bot was written to support persistent deployment, including platforms such as Railway. Configure the environment variables in your host's settings. For hosts with ephemeral filesystems, attach a persistent volume and set DATA_DIR to its mount path so your bot data survives restarts and redeployments.

A persistent volume protects against routine redeployments, but does not replace backups. Back up your data separately.
Project structure
.
├── ahmed_bot.py          # Main bot implementation
├── config.example.json   # Safe starter configuration
├── requirements.txt      # Python dependencies
├── .gitignore            # Local data, tokens and cache exclusions
├── LICENSE               # MIT licence
└── README.md             # Project documentation
At runtime, config.json and data.json are stored beside the script or under DATA_DIR. They are excluded from Git to protect local configuration and community data.
Before using it in another server
- Follow the Personalise it for your server guide above to replace account names, links, channel names, roles, rewards, and any other defaults.
- Review the moderation and security automation before giving the bot elevated permissions.
- Check channel and role setup, message-content access, and permissions in a test server.
- External services, particularly platform pages or unofficial feeds, might change their endpoints or responses over time.
- Review retention and handling of moderation logs, IDs, birthdays, and other community data before running the bot publicly.
Contributing
Issues and pull requests are welcome. Please include a clear description, reproduction steps for bugs, and relevant testing information. Never include live bot tokens, private configuration, or exported server/member data in an issue or pull request.
Licence
Distributed under the MIT License. Copyright © 2026 Ahmed.

This repository is an independent community project and is not affiliated with or endorsed by Discord, Twitch, Kick, YouTube, or TikTok.
