import discord
from discord.ext import commands
import json
import os
import time
from datetime import timedelta

# ============================================================
#   AHMED'S DISCORD BOT - Full Rewrite
#   Edit config.json to change settings WITHOUT restarting
#   data.json is handled automatically by the bot
# ============================================================

CONFIG_FILE = "config.json"
DATA_FILE = "data.json"

# ---- Load config fresh every time (allows live edits) ----
def get_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# ---- Load and save data ----
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"xp": {}, "joined_before": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---- XP cooldown tracker ----
xp_cooldowns = {}

# ---- Leveling logic ----
# Level 1 = 100 total XP, Level 2 = 200 total XP, Level N = N * 100 total XP
def get_level(total_xp):
    return total_xp // 100

def xp_for_next_level(total_xp):
    current_level = get_level(total_xp)
    next_level_xp = (current_level + 1) * 100
    return next_level_xp - total_xp

# ---- Check if user has a mod role ----
def is_mod(member):
    config = get_config()
    mod_roles = config.get("mod_roles", [])
    return any(role.name in mod_roles for role in member.roles) or member.guild_permissions.administrator

# ---- Bot setup ----
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

config = get_config()
bot = commands.Bot(command_prefix=config["prefix"], intents=intents, help_command=None)

# ============================================================
#   EVENTS
# ============================================================

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    print(f"Prefix: {get_config()['prefix']}")

# ---- Welcome message (first time joiners only) ----
@bot.event
async def on_member_join(member):
    config = get_config()
    data = load_data()
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

# ---- XP on message ----
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    config = get_config()
    data = load_data()

    user_id = str(message.author.id)
    guild_id = str(message.guild.id)
    cooldown_key = f"{guild_id}_{user_id}"
    now = time.time()

    if guild_id not in data["xp"]:
        data["xp"][guild_id] = {}
    if user_id not in data["xp"][guild_id]:
        data["xp"][guild_id][user_id] = 0

    if cooldown_key not in xp_cooldowns or now - xp_cooldowns[cooldown_key] >= config["xp_cooldown_seconds"]:
        xp_cooldowns[cooldown_key] = now

        old_xp = data["xp"][guild_id][user_id]
        old_level = get_level(old_xp)

        data["xp"][guild_id][user_id] += config["xp_per_message"]
        new_xp = data["xp"][guild_id][user_id]
        new_level = get_level(new_xp)

        save_data(data)

        if new_level > old_level:
            level_channel = discord.utils.get(
                message.guild.text_channels,
                name=config["level_up_channel"]
            )
            if level_channel:
                embed = discord.Embed(
                    title="Level Up!",
                    description=(
                        f"{message.author.mention} just reached **Level {new_level}**!\n"
                        f"Total XP: **{new_xp}**"
                    ),
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=message.author.display_avatar.url)
                await level_channel.send(embed=embed)

    await bot.process_commands(message)

# ---- Reaction role: give role on react ----
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

# ---- Reaction role: remove role on unreact ----
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
#   USER COMMANDS (anyone can use)
# ============================================================

@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(title="Bot Commands", color=discord.Color.purple())
    embed.add_field(
        name="User Commands",
        value=(
            "`?level` - Your level, total XP, and XP needed for next level\n"
            "`?level @user` - Check another user's level\n"
            "`?leaderboard` - Top 10 XP earners in the server\n"
            "`?help` - Shows this message"
        ),
        inline=False
    )
    embed.add_field(
        name="Mod Commands",
        value=(
            "`?timeout @user [minutes] [reason]` - Timeout a member\n"
            "`?untimeout @user` - Remove a timeout\n"
            "`?mute @user [reason]` - Mute a member\n"
            "`?unmute @user` - Unmute a member\n"
            "`?kick @user [reason]` - Kick a member\n"
            "`?ban @user [reason]` - Ban a member\n"
            "`?warn @user [reason]` - Warn a member via DM\n"
            "`?purge [amount]` - Delete messages (max 100)\n"
            "`?setuproles` - Post the reaction roles message\n"
            "`?setxp [amount]` - Change XP earned per message\n"
            "`?setcooldown [seconds]` - Change XP cooldown"
        ),
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
    next_level = current_level + 1

    embed = discord.Embed(
        title=f"{member.display_name}'s Level",
        color=discord.Color.purple()
    )
    embed.add_field(name="Level", value=str(current_level), inline=True)
    embed.add_field(name="Total XP", value=str(total_xp), inline=True)
    embed.add_field(
        name="Progress to Next Level",
        value=f"{xp_needed} XP needed to reach Level {next_level}",
        inline=False
    )
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
        level = get_level(xp)
        description += f"{rank} {member.display_name} — Level {level} | {xp} XP\n"

    embed.description = description if description else "No members with XP found."
    await ctx.send(embed=embed)

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

# ---- Live config commands (no restart needed) ----
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

# ---- Reaction roles setup ----
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

    embed = discord.Embed(
        title="Get Your Roles",
        description=description,
        color=discord.Color.purple()
    )

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
#   Replace YOUR_BOT_TOKEN_HERE with your token from
#   discord.com/developers/applications
# ============================================================

bot.run(os.environ.get("MTQ4NjE4MjcxNDQyMzExNTkxNg.GXoBRd.Lt8C1tVTXanXdQIOb3IWgJX-FveMnIChN8E6AA"))
