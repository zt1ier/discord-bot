import discord  # discord bot api
from discord.ext import commands
import random  # for random xp
import json  # to read and write xp data in file
import os  # to check if xp file exists before loading
import time  # xp cap per minute


# intents are permissions the bot needs to access certain info
intents = discord.Intents.default()
intents.message_content = True  # to read message content
intents.guilds = True
intents.members = True  # to manage roles


# create bot instance with command prefix "!"
bot = commands.Bot(command_prefix="!", intents=intents)


# remove default bot help command
bot.remove_command("help")


# filename to store xp data
XP_FILE = "xp_data.json"


level_milestones = {
    1: {"xp": 0, "role": "Recruit"},
    2: {"xp": 500, "role": "Cadet"},
    3: {"xp": 5000, "role": "Sergeant"},
    4: {"xp": 25000, "role": "Operative"},
    5: {"xp": 50000, "role": "Marshall"},
}

# track xp gains per user per minute: {user_id: {"xp": int, "timestamp": float}}
xp_cooldown = {}

XP_CAP_PER_MINUTE = 50  # max xp a user can gain per minute

MOD_ROLE_ID = "MOD_ROLE_ID" # replace with actual ID
DEV_ROLE_ID = "DEV_ROLE_ID" # replace with actual ID
CONTROL_ROOM_CHANNEL_ID = "CONTROL_ROOM_CHANNEL_ID" # replace with actual ID
USER_LOGS_CHANNEL_ID = "USER_LOGS_CHANNEL_ID" # replace with actual ID



# load xp data from file if it exists
# otherwise, start with an empty dictionary
if os.path.exists(XP_FILE):
    with open(XP_FILE, "r") as a:
        xp_data = json.load(a)  # read stored xp data (user_id: xp)
else:
    xp_data = {}  # no file found, start fresh


# function to save XP data back to the file after changes
def save_xp():
    with open(XP_FILE, "w") as b:
        json.dump(xp_data, b)  # write the xp_data dictionary to file in json format


# calculate user level based on xp and milestones
def get_level(xp):
    xp = max(0, xp)
    current_level = 0
    # find the highest milestone where user xp is >= required xp
    for lvl, milestone in sorted(level_milestones.items()):
        if xp >= milestone["xp"]:
            current_level = lvl
        else:
            break
    return current_level


# find the role name for a given level
def get_role_for_level(milestone_level):
    closest_level = 0
    for lvl in sorted(level_milestones):
        if lvl <= milestone_level:
            closest_level = lvl
        else:
            break
    return level_milestones[closest_level]["role"]


# function to update user's roles
async def update_user_role(member, new_role_name):
    guild = member.guild

    new_role = discord.utils.get(guild.roles, name=new_role_name)
    if not new_role:
        print(f"Role '{new_role_name}' not found in the server.")
        return

    milestone_roles = [milestone["role"] for milestone in level_milestones.values()]
    roles_to_remove = [r for r in member.roles if r.name in milestone_roles and r != new_role]

    try:
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)
        if new_role not in member.roles:
            await member.add_roles(new_role)
    except Exception as e:
        print(f"Error updating roles for {member}: {e}")


def is_mod_or_dev(ctx):
    return any(role.id in (MOD_ROLE_ID, DEV_ROLE_ID) for role in ctx.author.roles)


def is_in_allowed_channel():
    async def predicate(ctx):
        # allow mods/devs to use commands anywhere
        if is_mod_or_dev(ctx):
            return True
        
        if ctx.channel.id == CONTROL_ROOM_CHANNEL_ID:
            return True
        
        # not in allowed channel and not mod/dev --> fail check
        await ctx.send(f"Please use commands in <#{CONTROL_ROOM_CHANNEL_ID}>.")
        return False
    return commands.check(predicate)


# event triggered when bot is ready and connected
@bot.event
async def on_ready():
    print(f"{bot.user} is online.")


@bot.event
# event triggered when a new member joins
async def on_member_join(member):
    role_name = "Recruit"
    guild = member.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        try:
            await member.add_roles(role)
            print(f"Assigned role '{role_name}' to {member}.")
        except Exception as e:
            print(f"Could not assign role on join: {e}")
    else:
        print(f"Role '{role_name}' not found in guild '{guild.name}'.")


# event triggered on every message sent in channels the bot can read
@bot.event
async def on_message(message):
    if message.author.bot:
        return  # ignore messages sent by bots
    
    # call !help if user mentions the bot directly as a message, not in the middle of a sentence
    if message.content.strip() in [f"<@{bot.user.id}>", f"<@!{bot.user.id}>"]:
        ctx = await bot.get_context(message)
        ctx.command = bot.get_command("help")
        await bot.invoke(ctx)
        return  # skip xp handling after this

    user_id = str(message.author.id)  # convert user id to string for json key

    current_time = time.time()

    if user_id not in xp_cooldown:
        xp_cooldown[user_id] = {"xp": 0, "timestamp": current_time}

    elapsed = current_time - xp_cooldown[user_id]["timestamp"]

    # reset cooldown if 60 seconds has passed
    if elapsed > 60:
        xp_cooldown[user_id]["xp"] = 0
        xp_cooldown[user_id]["timestamp"] = current_time

    # randomize user xp gain
    xp_gain = random.randint(1, 5)
    xp_allowed = XP_CAP_PER_MINUTE - xp_cooldown[user_id]["xp"]

    if xp_allowed <= 0:
        # xp cap reached, no XP gained this message
        xp_gain = 0
    elif xp_gain > xp_allowed:
        # limit xp_gain to remaining allowed xp
        xp_gain = xp_allowed

    if xp_gain > 0:
        # add random xp for each message sent by user
        xp_data[user_id] = xp_data.get(user_id, 0) + xp_gain
        xp_cooldown[user_id]["xp"] += xp_gain

        # calculate level before and after adding xp
        level_before = get_level(xp_data[user_id] - xp_gain)
        level_after = get_level(xp_data[user_id])

        # if user leveled up, send a congratulatory message
        if level_after > level_before:
            role_name = get_role_for_level(level_after)
            await message.channel.send(f"{message.author.mention} has ranked up to {role_name}.")

            # update user roles
            await update_user_role(message.author, role_name)

        save_xp()  # save the updated xp data to file

    # allows other commands to still be processed
    await bot.process_commands(message)


# error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use that command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # ignore unknown commands
    else:
        raise error  # let other errors surface


# command users can run to check their current level and xp
@bot.command(aliases=["r"])
@is_in_allowed_channel()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_id = str(member.id)
    xp = xp_data.get(user_id, 0)
    lvl = get_level(xp)
    role_name = get_role_for_level(lvl) or "Unranked"
    await ctx.send(f"User {member.mention} assigned to rank **{role_name}**. Credit accumulation registered at {xp} points.")


# command users can run to check available commands
@bot.command(aliases=["h"])
@is_in_allowed_channel()
async def help(ctx):
    if is_mod_or_dev(ctx):
        embed = discord.Embed(
            title="Moderator Commands — DIRECTIVE-7",
            description="Prefix: `!` \n\nHere are the available commands grouped by access level:",
            color=discord.Color.from_str("#4b0082")  # purple i think
        )

        # User Commands Section
        embed.add_field(
            name="User Commands",
            value=(
                "`rank` / `r` — Check your current Rank and Credits.\n"
                "`help` / `h` — Show this help message.\n"
                "`leaderboard` / `lb` — See the top ranked users."
            ),
            inline=False
        )

        # Moderator Commands Section
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
            title="User Commands — DIRECTIVE-7",
            description="Prefix: `!` \n\n Listed below are the available commands in my program:",
            color=discord.Color.from_str("#00bfff")  # light blue
        )
        
        embed.add_field(name="`help` / `h`", value="> Show this help message.", inline=False)
        embed.add_field(name="`rank` / `r`", value="> Check your current Rank and Credits.", inline=False)
        embed.add_field(name="`leaderboard` / `lb`", value="> See the top ranked users.", inline=False)

        embed.set_footer(text="More commands will be available in future updates.")

    await ctx.send(embed=embed)


# command to give xp to player (admin only)
@bot.command(aliases=["pts"])
@commands.has_permissions(administrator=True)
async def points(ctx, member: discord.Member, amount: int):
    user_id = str(member.id)
    
    # update xp
    previous_xp = xp_data.get(user_id, 0)
    xp_data[user_id] = previous_xp + amount
    
    # recalculate level
    old_level = get_level(xp_data[user_id] - amount)
    new_level = get_level(xp_data[user_id])
    
    action1 = "Gave" if amount >= 0 else "Took"
    action2 = "to" if amount >= 0 else "from"
    await ctx.send(f"{action1} **{abs(amount)} points** {action2} {member.mention}.")
    
    # notify if user leveled up, change role if ranked up
    if new_level > old_level:
        role_name = get_role_for_level(new_level)
        await ctx.send(f"{member.mention} has ranked up to **{role_name}**.")
        
        # update user roles
        await update_user_role(member, role_name)
        
    save_xp()  # save updated xp data
    
    
# command mods can run to delete messages
@bot.command(aliases=["p"])
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)  # +1 includes the command message itself
    await ctx.send(f"Purged {amount} messages.", delete_after=5)


# command mods can run to kick a user
@bot.command(aliases=["k"])
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
	await member.kick(reason=reason)
	await ctx.send(f"{member.mention} has been kicked.")


# command mods can run to ban a user
@bot.command(aliases=["b"])
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member.mention} has been banned.")


# command mods can run to unban a banned user
@bot.command(aliases=["ub"])
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user: str):
    async for ban_entry in ctx.guild.bans():
        if str(ban_entry.user.id) == user or str(ban_entry.user) == user:
            await ctx.guild.unban(ban_entry.user)
            await ctx.send(f"Unbanned {ban_entry.user.mention}.")
            return
    await ctx.send("User not found in ban list.")
    
    
# logs deleted messages to specified channel
@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    log_channel = bot.get_channel(USER_LOGS_CHANNEL_ID)
    if not log_channel:
        return
    
    embed = discord.Embed(
    	title="Message Deleted",
        description=(f"Author: {message.author.mention} (`{message.author}`)\nChannel: {message.channel.mention}"),
        color=discord.Color.from_str("#00bfff"),  # light blue, same with user !help
        timestamp=message.created_at
    )
    
    if message.content:
        embed.add_field(name="Content", value=message.content[:1024], inline=False)
        # [:1024] truncates the message to 1024 characters since the bot can only handle 1024 characters at max
        
    # include attachments if any
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.url)
                break
        
        non_image_attachments = [a.filename for a in message.attachments if not (a.content_type and a.content_type.startswith("image"))]
        if non_image_attachments:
            embed.add_field(name="Attachments", value="\n".join(non_image_attachments), inline=False)
        
    await log_channel.send(embed=embed)


# leaderboard, top 10
@bot.command(aliases=["lb", "top"])
async def leaderboard(ctx, count: int = 10):
    # limit to 25 users if !lb (count) --- but i don't think so
    count = max(1, min(count, 25))
    
    if not xp_data:
        await ctx.send("No points data available.")
        
    top_users = sorted(xp_data.items(), key=lambda x: x[1], reverse=True)[:count]
    
    embed = discord.Embed(
        title=f"Highest Ranked Users",
        color=discord.Color.from_str("#f1c40f"),
    )
    
    for rank, (user_id, xp), in enumerate(top_users, start=1):
        member = ctx.guild.get_member(int(user_id))
        username = member.display_name if member else f"<User {user_id}>"
        level = get_level(xp)
        role = get_role_for_level(level)
        embed.add_field(
            name=f"#{rank} — {username}",
            value=f"Credits: **{xp}** — Rank: **{role}**",
            inline=False
        )
        
    await ctx.send(embed=embed)

    
# logs edited messages to specified channel
@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return

    log_channel = bot.get_channel(USER_LOGS_CHANNEL_ID)
    if not log_channel:
        return

    embed = discord.Embed(
        title="Message Edited",
        description=f"Author: {before.author.mention} (`{before.author}`)\nChannel: {before.channel.mention}",
        color=discord.Color.from_str("#00bfff"),  # light blue, same with user !help
        timestamp=after.edited_at or discord.utils.utcnow()
    )

    embed.add_field(name="Before", value=before.content[:1024] or "*Empty*", inline=False)
    embed.add_field(name="After", value=after.content[:1024] or "*Empty*", inline=False)

    await log_channel.send(embed=embed)

bot.run("YOUR_KEY_HERE") # replace with your actual bot key
