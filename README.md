# Moderation and leveling Discord bot
- Source code for my Discord moderation + leveling bot using the discord.py Python library
- Currently handles XP ranks, message logging, basic mod tools, and a custom help menu
- Still updating and improving as I learn more — things like auto-moderation might come later
- Feel free to fork, remix, or use it as a base for your own server bot


**Current features**
- XP + leveling system with cooldowns and rank roles
- Message logging for deleted and edited messages (including attachments!)
- Leaderboard and rank checking
- Mod commands like kick, ban, unban, purge
- Role auto-assign on join
- Channel-limited commands with mod/dev bypass
- Custom help embed with split view for mods and users


**Default settings** (can change in code)
| **Setting** | **Location** | **Code Snippet** | **Change This If** |
|---|---|---|---|
| **Command Prefix** | Line 17 | `bot = commands.Bot(command_prefix="!", intents=intents)` | You want to change the prefix from `!` to something else (e.g. `?`, `/`, etc.) |
| **Intents (Permissions)** | Lines 11-13 | `intents.message_content = True`<br>`intents.guilds = True`<br>`intents.members = True` | You need to enable/disable what data your bot can access (e.g., messages, members) |
| **XP Role Milestones** | Lines 28–34 | `level_milestones = { ... }` | You want to edit XP requirements or change the role names for levels. |
| **XP Gain Cooldown & Cap** | Line 39 | `XP_CAP_PER_MINUTE = 50` | You want users to earn more or less XP per minute. |
| **Role IDs (Mod/Dev)** | Lines 41-42 | `MOD_ROLE_ID = ...`<br>`DEV_ROLE_ID = ...` | The mod/dev roles have different IDs in your server. |
| **Command Channel ID** | Line 43 | `CONTROL_ROOM_CHANNEL_ID = ...` | You want to allow commands in only one different channel. |
| **User Logs Channel ID** | Line 44 | `USER_LOGS_CHANNEL_ID = ...` | You want to log deleted/edited messages in a different channel. |
| **Default Role on Join**   | Line 136 | `role_name = "Recruit"` | You want new users to get a different role when they join. |
| **Random XP Gain** | Line 177 | `xp_gain = random.randint(1, 5)` | You want users to gain more or less XP per message. |

Feel free to contact me for inquiries... somewhere. I don't know if GitHub has a private messaging system, so you may shoot me a message at **ffztier@gmail.com**.
