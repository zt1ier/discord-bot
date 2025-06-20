# Moderation and leveling Discord bot
- Source code for my Discord moderation + leveling bot using the discord.py Python library
- Currently handles XP ranks, message logging, basic mod tools, and a custom help menu
- Still updating and improving as I learn more — things like auto-moderation might come later
- Feel free to fork, remix, or use it as a base for your own server bot

## Current features
- XP + leveling system with cooldowns and random gain per message
- Role rewards when reaching level milestones
- Leaderboard and rank checking (with role name display)
- Message logging for deleted and edited messages (including attachments!)
- Mod commands like kick, ban, unban, purge
- Role auto-assign on member join
- Channel-limited commands with mod/admin bypass
- Custom help embed that shows different views for mods and regular users
- Manual XP adjustment via points command (admin only)

## Default settings (can change in code or .env file)
| **Setting** | **Location** | **Code Snippet** | **Change This If** |
|---|---|---|---|
| **BOT Command Channel ID** | .env | `BOT_CHANNEL_ID=` | You want to allow commands in only one different channel. |
| **Command Prefix** | .env | `COMMAND_PREFIX=` | You want to change the prefix from `!` to something else (e.g. `?`, `/`, etc.) |
| **MOD / DEV Role IDs** | .env | `MOD_ROLE_ID=`<br>`DEV_ROLE_ID=` | The mod/dev roles have different IDs in your server. |
| **User Logs Channel ID** | .env | `USER_LOGS_CHANNEL_ID=` | You want to log deleted/edited messages in a different channel. |
| **Intents (Permissions)** | Lines 30–33 | `intents.message_content = True`<br>`intents.guilds = True`<br>`intents.members = True` | You need to enable/disable what data your bot can access (e.g., messages, members) |
| **XP Gain Cooldown & Cap** | Lines 44–45 | `XP_CAP_PER_MINUTE = 50` | You want users to earn more or less XP per minute. |
| **XP Role Milestones** | Lines 48–54 | `level_milestones = { ... }` | You want to edit XP requirements or change the role names for levels. |
| **Random XP Gain** | Line 202 | `xp_gain = random.randint(1, 5)` | You want users to gain more or less XP per message. |

That being said, the line locations might be innacurate. If there are other

Feel free to contact me for inquiries... somewhere. I don't know if GitHub has a private messaging system, so you may shoot me a message at **ffztier@gmail.com**.
