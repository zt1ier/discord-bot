# ================================================= #
# ==================== IMPORTS ==================== #
# ================================================= #

import discord  # Discord bot API
from discord.ext import commands # Command framework
from dotenv import load_dotenv # Load environment variables
import random  # Random XP generation
import json  # For reading/writing XP data
import os  # File and env access
import time  # Time tracking for XP cooldowns
import shutil # For backing up XP file


# ======================================================== #
# ==================== CONFIGURATION ===================== #
# ======================================================== #

load_dotenv() # Load environment variables from .env file

# Get environment variables
token = os.getenv("DISCORD_TOKEN") # Bot token
prefix = os.getenv("COMMAND_PREFIX") # Bot prefix, e.g. "!"
MOD_ROLE_ID = int(os.getenv("MOD_ROLE_ID")) # Moderator role ID
DEV_ROLE_ID = int(os.getenv("DEV_ROLE_ID")) # Developer/Admin role ID
BOT_CHANNEL_ID = int(os.getenv("BOT_CHANNEL_ID")) # Allowed bot command channel
USER_LOGS_CHANNEL_ID = int(os.getenv("USER_LOGS_CHANNEL_ID")) # Channel for message logging

# Set up intents/permissions for what the bot can access
intents = discord.Intents.default() # Default permissions
intents.message_content = True  # To read message content
intents.guilds = True # To read server data
intents.members = True  # To access and manage member info, e.g. roles


# Create bot instance
bot = commands.Bot(command_prefix=prefix, intents=intents)

#  Remove the default help command to override it
bot.remove_command("help")

# Constants
XP_FILE = "xp_data.json" # XP storage file
XP_CAP_PER_MINUTE = 50  # Max XP that can be gained per minute
xp_cooldown = {} # Cooldown tracking dictionary: {user_id: {"xp": int, "timestamp": float}}

# XP milestones for levels and corresponding roles
# Change XP and role as you desire
level_milestones = {
    1: {"xp": 0, "role": "ROLE_NAME_1"},
    2: {"xp": 500, "role": "ROLE_NAME_2"},
    3: {"xp": 5000, "role": "ROLE_NAME_3"},
    4: {"xp": 25000, "role": "ROLE_NAME_4"},
    5: {"xp": 50000, "role": "ROLE_NAME_5"},
}

# Load XP data from file if it exists
if os.path.exists(XP_FILE):
    with open(XP_FILE, "r") as file:
        xp_data = json.load(file)
else:
    xp_data = {}  # Start with an empty XP database if file is missing

    
# ========================================================== #
# ==================== HELPER FUNCTIONS ==================== #
# ========================================================== #

# Save XP data to JSON file
# Also makes a .bak backup
def save_xp():
    with open(XP_FILE, "w") as file:
        json.dump(xp_data, file)
    shutil.copy(XP_FILE, XP_FILE + ".bak")  # Backup copy

# Return the level associated with a given XP value
def get_level(xp):
    xp = max(0, xp)
    current_level = 0
    for lvl, milestone in sorted(level_milestones.items()):
        if xp >= milestone["xp"]:
            current_level = lvl
        else:
            break
    return current_level

# Return the role name associated with a given level milestone
def get_role_for_level(milestone_level):
    closest_level = 0
    for lvl in sorted(level_milestones):
        if lvl <= milestone_level:
            closest_level = lvl
        else:
            break
    return level_milestones[closest_level]["role"]

# Update the user's role when they level up
async def update_user_role(member, new_role_name):
    guild = member.guild
    new_role = discord.utils.get(guild.roles, name=new_role_name)
    if not new_role:
        print(f"UpdateUserRole: Role '{new_role_name}' not found in the server.")
        return

    milestone_roles = [milestone["role"] for milestone in level_milestones.values()]
    roles_to_remove = [r for r in member.roles if r.name in milestone_roles and r != new_role]

    try:
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)
        if new_role not in member.roles:
            await member.add_roles(new_role)
    except Exception as e:
        print(f"UpdateUserRole: Error updating roles for {member}: {e}")

# Check if the command author is a mod or developer/admin
def is_mod_or_dev(ctx):
    member = ctx.author
    if not isinstance(member, discord.Member):
        return False
    return any(role.id in (MOD_ROLE_ID, DEV_ROLE_ID) for role in member.roles)

# Check if the command is used in allowed channel or by mod/dev
def is_in_allowed_channel():
    async def predicate(ctx):
        print(f"Checking if {ctx.author} can use commands in {ctx.channel}")
        
        # Allow mods/devs to use commands anywhere
        if is_mod_or_dev(ctx):
            return True
        
        if ctx.channel.id == BOT_CHANNEL_ID:
            return True
        
        await ctx.send(f"Please use commands in <#{BOT_CHANNEL_ID}>.")
        return False
    return commands.check(predicate)


# ==================================================== #
# ==================== BOT EVENTS ==================== #
# ==================================================== #


# on_ready: Called once the bot is online and connected
@bot.event
async def on_ready():
    print(f"{bot.user} is online.")
    if prefix:
        print(f"Command prefix is '{prefix}'")
    else:
        print("Prefix not found.")

# on_member_join: Assign starting role to new members who join
@bot.event
async def on_member_join(member):
    role_name = get_role_for_level(1)
    role = discord.utils.get(member.guild.roles, name=role_name)
    if role:
        try:
            await member.add_roles(role)
            print(f"Assigned role '{role_name}' to {member}.")
        except Exception as e:
            print(f"Could not assign role on join: {e}")
    else:
        print(f"Role '{role_name}' not found in guild '{member.guild.name}'.")

# on_message: Tracks XP and handles bot logic
@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Ignore messages from bot/s

    # Ignore short messages to reduce spam/farming
    if not message.content.startswith(prefix) and len(message.content.strip()) < 10:
        return

    # If bot is directly mentioned, show help
    if message.content.strip() in [f"<@{bot.user.id}>", f"<@!{bot.user.id}>"]:
        ctx = await bot.get_context(message)
        ctx.command = bot.get_command("help")
        await bot.invoke(ctx)
        return

    user_id = str(message.author.id)  # Store user ID as string for XP tracking
    current_time = time.time()

    # Initialize cooldown tracking if not already present
    if user_id not in xp_cooldown:
        xp_cooldown[user_id] = {"xp": 0, "timestamp": current_time}

    time_elapsed = current_time - xp_cooldown[user_id]["timestamp"]

    # Reset cooldown timer if a minute has passed
    if time_elapsed > 60:
        xp_cooldown[user_id]["xp"] = 0
        xp_cooldown[user_id]["timestamp"] = current_time

    # Calculate how much XP can be gained this message
    xp_gain = random.randint(1, 5)
    xp_allowed = XP_CAP_PER_MINUTE - xp_cooldown[user_id]["xp"]

    if xp_allowed <= 0:
        xp_gain = 0  # Cap hit, no XP this message
    elif xp_gain > xp_allowed:
        xp_gain = xp_allowed  # Limit gain to cap

    # Add XP and check for level-up
    if xp_gain > 0:
        xp_data[user_id] = xp_data.get(user_id, 0) + xp_gain
        xp_cooldown[user_id]["xp"] += xp_gain

        level_before = get_level(xp_data[user_id] - xp_gain)
        level_after = get_level(xp_data[user_id])

        # Notify on level-up and update role
        if level_after > level_before:
            role_name = get_role_for_level(level_after)
            await message.channel.send(f"{message.author.mention} has ranked up to {role_name}.")
            await update_user_role(message.author, role_name)

        save_xp()  # Save XP after processing

    await bot.process_commands(message)  # Let commands still work

# on_command_error: Handles missing permissions, arguments, or unknown commands
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use that command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`.")
    elif isinstance(error, commands.CommandNotFound):
        print("Command not found.")
    else:
        raise error  # Allow unhandled errors to surface

# on_message_delete: Logs deleted messages to log channel
@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return  # Ignore bot messages

    log_channel = bot.get_channel(USER_LOGS_CHANNEL_ID)
    if not log_channel:
        return  # No log channel found

    # Create embed with deletion info
    embed = discord.Embed(
        title="Message Deleted",
        description=(f"Author: {message.author.mention} (`{message.author}`)\nChannel: {message.channel.mention}"),
        color=discord.Color.from_str("#00bfff"),  # Light blue
        timestamp=message.created_at
    )

    # Add content if exists
    if message.content:
        embed.add_field(name="Content", value=message.content[:1024], inline=False)

    # Handle attachments
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.url)
                break

        non_image_attachments = [a.filename for a in message.attachments if not (a.content_type and a.content_type.startswith("image"))]
        if non_image_attachments:
            embed.add_field(name="Attachments", value="\n".join(non_image_attachments), inline=False)

    await log_channel.send(embed=embed)  # Send log


# on_message_edit: Logs edited messages to log channel
@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return  # Ignore if no actual change or from bot

    log_channel = bot.get_channel(USER_LOGS_CHANNEL_ID)
    if not log_channel:
        return  # No log channel

    embed = discord.Embed(
        title="Message Edited",
        description=f"Author: {before.author.mention} (`{before.author}`)\nChannel: {before.channel.mention}",
        color=discord.Color.from_str("#00bfff"),
        timestamp=after.edited_at or discord.utils.utcnow()
    )

    # Show before/after content
    embed.add_field(name="Before", value=before.content[:1024] or "*Empty*", inline=False)
    embed.add_field(name="After", value=after.content[:1024] or "*Empty*", inline=False)

    await log_channel.send(embed=embed)  # Send log
        
        
# ====================================================== #
# ==================== BOT COMMANDS ==================== #
# ====================================================== #
        
# rank: Show current rank and XP of a user
@bot.command(aliases=["r"])
@is_in_allowed_channel()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author  # Use the mentioned user or the command author
    user_id = str(member.id)
    xp = xp_data.get(user_id, 0)
    lvl = get_level(xp)
    role_name = get_role_for_level(lvl) or "Unranked"
    await ctx.send(f"{member.mention}, you're currently ranked **{role_name}** with {xp} points.")


# help: Show a list of available commands, customized by user role
@bot.command(aliases=["h"])
@is_in_allowed_channel()
async def help(ctx):
    if is_mod_or_dev(ctx):
        embed = discord.Embed(
            title="Moderator Commands",
            description="Prefix: `!` \n\nHere are the available commands grouped by access level:",
            color=discord.Color.from_str("#4b0082")
        )

        embed.add_field(
            name="User Commands",
            value=(
                "`rank` / `r` — Check your current Rank and Points.\n"
                "`help` / `h` — Show this help message.\n"
                "`leaderboard` / `lb` — See the top ranked users."
            ),
            inline=False
        )

        embed.add_field(
            name="Moderator Commands",
            value=(
                "`purge` / `p` — Delete multiple messages.\n"
                "`kick` / `k` — Kick a member from the server.\n"
                "`ban` / `b` — Ban a member from the server.\n"
                "`unban` / `ub` — Unban a previously banned user."
            ),
            inline=False
        )

        embed.set_footer(text="Handle these powers responsibly and keep the community safe.")
    else:
        embed = discord.Embed(
            title="User Commands",
            description="Prefix: `!` \n\n Listed below are the available commands in my program:",
            color=discord.Color.from_str("#00bfff")
        )

        embed.add_field(name="`help` / `h`", value="> Show this help message.", inline=False)
        embed.add_field(name="`rank` / `r`", value="> Check your current Rank and Points.", inline=False)
        embed.add_field(name="`leaderboard` / `lb`", value="> See the top ranked users.", inline=False)

        embed.set_footer(text="More commands will be available in future updates.")

    await ctx.send(embed=embed)

# points: Admin command to manually add or remove XP from a user
@bot.command(aliases=["pts"])
@commands.has_permissions(administrator=True)
async def points(ctx, member: discord.Member, amount: int):
    user_id = str(member.id)

    previous_xp = xp_data.get(user_id, 0)
    xp_data[user_id] = previous_xp + amount

    old_level = get_level(previous_xp)
    new_level = get_level(xp_data[user_id])

    action1 = "Generously gave" if amount >= 0 else "Selfishly stole"
    action2 = "to" if amount >= 0 else "from"
    await ctx.send(f"{action1} **{abs(amount)} points** {action2} {member.mention}.")

    if new_level > old_level:
        role_name = get_role_for_level(new_level)
        await ctx.send(f"Oh my days. {member.mention} has just ranked up to **{role_name}**.")
        await update_user_role(member, role_name)

    save_xp()
        
# purge: Moderator command to delete messages in bulk
@bot.command(aliases=["p"])
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"Deleted {amount} messages to keep things clean.", delete_after=5) # After 5 seconds

# kick: Moderator command to kick a member from the server
@bot.command(aliases=["k"])
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"Woah, {member.mention} just disappeared.")

# ban: Moderator command to ban a member from the server
@bot.command(aliases=["b"])
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member.mention} is never coming back.")


# unban: Moderator command to unban a user
@bot.command(aliases=["ub"])
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user: str):
    async for ban_entry in ctx.guild.bans():
        if str(ban_entry.user.id) == user or str(ban_entry.user) == user:
            await ctx.guild.unban(ban_entry.user)
            await ctx.send(f"{ban_entry.user.mention} is coming back! Hopefully.")
            return
    await ctx.send("Yeah, that user doesn't exist, chief.")
    

# message: Send a message in the specified channel
@bot.command(aliases=["msg"])
@commands.has_permissions(send_messages=True)
async def message(ctx, channel: discord.TextChannel, *, msg):
    perms = channel.permissions_for(ctx.guild.me)
    if not perms.send_messages:
        await ctx.send(f"I don't have message perms in that channel dumbo.")
        return
    
    await channel.send(msg)


bot.run(token)
