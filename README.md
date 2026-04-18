# 🎙️ VoiceForge

A self-hosted Discord bot for dynamic temporary voice channel management with a fully interactive dashboard panel, database persistence, and advanced member control features.

---

## 📦 Version History

### v3.0 — Database Persistence & Server Configuration
- 💾 **Database-backed server configuration** — Server setup (category, creator channel) is now persisted in SQLite, surviving bot restarts
- 🗄️ **Channel ownership tracking** — All temporary channels are tracked in a dedicated database with owner, category, and creation timestamps
- ⚙️ **Server registration system** — New `/register` and `/unregister` and `/setup` commands to set up and tear down bot configuration per server
- 🔄 **On-demand voice channel recovery** — Channels created before the last bot offline period are automatically recovered on startup
- 🔑 **Ownership persistence** — Channel owner data survives across bot restarts via database
- 📊 **New database modules** — `database_server_operations.py` and `database_channel_operations.py` for structured data handling
- 🎯 **Per-channel cooldowns** — Panel button cooldowns now apply per-channel instead of globally

### v2.1 — Stability & Permission Fixes
- 🔁 **On-start VC recovery** — Automatic channel creation for users in the creator channel when bot comes online
- 🗑️ **Orphan channel cleanup** — Automatic deletion of channels with no ownership records
- 🔒 **Permission overwrite fixes** — Fixed chat permissions for locked channels
- ⏱️ **Per-channel cooldowns** — Cooldowns run per channel instead of globally
- ✅ **Trust/Untrust sync** — Consistent permission checking across slash commands and panel buttons
- 🛡️ **Guild checks** — Server-only command validation

### v2.0 — Interactive Panel
- 🎛️ **Interactive Panel** — TempVoice-style UI with buttons for all channel controls
- 📨 **Native Member Search** — Discord's built-in user picker for invite, trust, and block
- 👑 **Smart Claim System** — Automatic ownership recovery for abandoned channels
- 🔒 **Panel sent into temp VC** — No extra channels needed; panel appears directly in created voice channels

---

## ✨ Features

### Core Functionality
- ✅ Auto-creates a personal voice channel when a user joins the **"Create VC"** channel
- ✅ Automatically recovers and creates channels for users already in creator channel on bot startup
- ✅ Automatically deletes empty channels when everyone leaves
- ✅ Automatically cleans up orphaned channels (no database record) periodically
- ✅ Full ownership system with claim and transfer support
- ✅ Rich set of slash commands for complete channel management
- ✅ Interactive button panel with modals and user selectors

### Database Features
- ✅ Persistent server configuration (survives restarts)
- ✅ Channel ownership tracking with timestamps
- ✅ Server registration & unregistration
- ✅ Comprehensive member permission control (trust, block, kick)

### Permission Management
- ✅ Lock/Unlock channels
- ✅ Hide/Show from channel list
- ✅ Trust members (full access even when locked)
- ✅ Block members (kick and permanent ban)
- ✅ Individual permission overwrites

---

## 📁 Project Structure

```
├── main.py                           # Bot entry point and configuration
├── config.py                         # Cooldown and limit constants
├── logger.py                         # Error and info logging setup
├── cogs/
│   ├── voice_manager.py              # Auto voice channel creation, deletion, and cleanup
│   ├── voice_interface.py            # Interactive panel UI (buttons, modals, selects)
│   ├── voice_controls.py             # All slash commands for channel control
│   ├── error_handling.py             # Global error handler
│   ├── sync_command.py               # Slash command sync and help utilities
│   └── databaseio.py                 # High-level database I/O wrapper
├── database_server_operations.py     # Server table CRUD operations
├── database_channel_operations.py    # Channel table CRUD operations
└── .env                              # Environment variables (create this)
```

---

## ⚙️ Setup

### 1. Clone the repository
```bash
git clone https://github.com/code-1py/VoiceForge.git
cd VoiceForge
```

### 2. Install dependencies
```bash
pip install discord.py python-dotenv pydantic
```

### 3. Create environment variables file

Create a `.env` file in the root directory:
```env
# Discord Bot Token
VOICE_BOT_TOKEN=your_bot_token_here

# Database names (optional - defaults provided)
SERVER_DB_NAME=discord_server.db
CHANNEL_DB_NAME=discord_channel.db
```

### 4. Run the bot
```bash
python main.py
```

---

## 🔧 Discord Server Setup

### Initial Setup Steps

1. **Create a Category** where temporary voice channels will be created
   - This is where all user-created voice channels will appear
   - Assign permissions to everyone roles for `connect`, `video` , `speak` , `view channel` , `voice activity` , `send message` , `read message history` 

2. **Create a Voice Channel** inside that category
   - This will be the "Create VC" trigger channel
   - Users join this channel to get their own personal voice channel
   - Name it something like `➕ Create VC` or `🎤 Join for VC`
   - Optional create a text channel like `✨・voice-controls` with no message permissions and use `/panel` to send panel interface in channel

3. **Set Bot Permissions**
   - Ensure the bot has administrator permissions in the server

### Using the Bot

First-time setup requires a server registration command:

```
/setup
```

Shows instructions to setup bot in server.

```
/register
```

This stores your category and creator channel configuration in the database, enabling persistent operation across bot restarts.

To remove the bot from a server:

```
/unregister
```

---

## 🎛️ Interactive Panel

When a user joins the Create VC channel, a panel is automatically sent inside their new voice channel with the following controls:

| Button | Icon | Description | Owner Only |
|--------|------|-------------|-----------|
| **Lock** | 🔒 | Block others from joining | ✅ |
| **Unlock** | 🔓 | Allow others to join | ✅ |
| **Hide** | 🙈 | Hide from channel list | ✅ |
| **Show** | 👁️ | Make visible in channel list | ✅ |
| **Rename** | ✏️ | Change channel name (max 32 chars) | ✅ |
| **Set Limit** | 👥 | Cap max members (0 = unlimited) | ✅ |
| **Invite** | 📨 | Search and allow a member to join | ✅ |
| **Kick** | 👢 | Disconnect a member from channel | ✅ |
| **Ban** | 🚫 | Search and block a member | ✅ |
| **Trust** | ✅ | Search and give full permissions | ✅ |
| **Untrust** | ⛔ | Remove a member's trust | ✅ |
| **Unblock** | ✔️ | Remove a member's ban | ✅ |
| **Transfer** | 🔁 | Give ownership to someone else | ✅ |
| **Claim** | 👑 | Claim an abandoned channel | ❌ |
| **Delete** | 🗑️ | Delete your channel permanently | ✅ |

> **Note:** All controls are owner-only except **Claim**, which anyone in the channel can use.

### Sending Panel Manually

You can manually send a panel to any voice channel using:

```
/panel
```

Requires `Manage Channels` permission.

---

## 🛠️ Owner Commands (Prefix: `!`)

| Command | Description |
|---------|-------------|
| `!syncguild` | Sync slash commands to the current server |
| `!syncglobal` | Sync slash commands globally |
| `!clearguild` | Clear all guild slash commands |
| `!clearglobal` | Clear all global slash commands |

> **Note:** These commands are restricted to the bot owner. Use them after updating commands to make changes visible to users.

---

## 📋 Slash Commands

### Server Management

| Command | Description |
|---------|-------------|
| `/register` | Register this server to use the bot (save config to database) |
| `/unregister` | Unregister this server and remove all data |
| `/setup` | Shows instructions to setup bot in server |

### Channel Management

| Command | Description | Cooldown |
|---------|-------------|----------|
| `/rename <name>` | Rename your voice channel (max 32 characters) | 300s |
| `/limit <number>` | Set user limit (1–99), or 0 to remove | 3s |
| `/delete` | Delete your voice channel | 5s |
| `/lock` | Lock the channel so no one can join | 4s |
| `/unlock` | Unlock the channel | 4s |
| `/hide` | Hide the channel from everyone | 5s |
| `/unhide` | Make the channel visible again | 5s |

### Ownership

| Command | Description | Cooldown |
|---------|-------------|----------|
| `/claim` | Claim an unowned or abandoned channel | 90s |
| `/transfer <member>` | Transfer ownership to another member | 90s |

### Member Control

| Command | Description | Cooldown |
|---------|-------------|----------|
| `/kick <members>` | Kick up to 5 members from your channel | 2s |
| `/invite <members>` | Send a DM invite to up to 5 members | 5s |
| `/trust <members>` | Allow up to 5 members to view/join even if locked or hidden | 4s |
| `/untrust <members>` | Remove up to 5 members from the trusted list | 4s |
| `/trusted` | View the trusted members list | 3s |
| `/block <members>` | Kick and block up to 5 members | 3s |
| `/unblock <members>` | Remove up to 5 members from the blocked list | 3s |
| `/blocked` | View the blocked members list | 3s |

### Utilities

| Command | Description |
|---------|-------------|
| `/help` | Shows all available slash commands |
| `/panel` | Manually send the control panel to a voice channel |

---

## 🗄️ Database Schema

### Servers Table
Stores server configuration and setup information.

```
servers
├── id (PK)
├── server_id (unique)
├── category_id (where temp channels go)
├── creator_channel_id (join to create VC)
├── created_at
└── updated_at
```

### Channels Table
Tracks all temporary voice channels and ownership.

```
serversChannels
├── id (PK)
├── server_id
├── owner_id
├── category_id
├── channel_id (unique)
├── created_at
└── updated_at
```

---

## 📝 Logs

Logs are stored in the `Logs/` directory:

- **`VOICE_BOT.log`** — General bot activity, startup logs, and voice channel events
- **`error.log`** — Detailed error traces with timestamps and locations

### Log Locations
- Timestamp: All errors include ISO format timestamps
- Traceback: Full Python traceback for debugging
- Location: Error location includes file name and function name

Example error log entry:
```
2024-01-15 10:45:23,456 - ERROR - Location : create_temp_voice_channel - file : voice_manager.py : Error Name - HTTPException - traceback : 
Traceback (most recent call last):
  File "voice_manager.py", line 120, in create_temp_voice_channel
    ...
```

---

## 🔄 Database Operations

### Server Configuration

**Register a server:**
```
/register
```
This creates a server entry in the database with the configured category and creator channel.

**Unregister a server:**
```
/unregister
```
This removes all server configuration and associated channel data from the database.

### Channel Tracking

Channels are automatically tracked when created. The database records:
- Owner ID
- Server ID
- Category ID
- Channel ID
- Creation timestamp

When channels are deleted (empty or manually), database records are cleaned up automatically.

---

## 📌 Important Notes

### Ownership & Persistence
- ✅ Channel ownership is **persisted in the database**
- ✅ Ownership data **survives bot restarts**
- ✅ Use `/claim` to take ownership of a channel without a registered owner

### Command Behavior
- All voice control commands **only work inside channels created by this bot**
- Only the **channel owner** can use management commands (except `/claim`)
- Channels are **automatically deleted when they become empty** (no non-bot members)
- **Orphaned channels** (in database but deleted in Discord) are cleaned up on startup

### Cooldowns
- Cooldowns are **per-channel**, not per-user
- Different commands have different cooldown durations (see Slash Commands above)
- Cooldown timer starts when the command is **executed**, not when it completes

### Performance
- Bot caches server configuration on startup for fast lookups
- Database is SQLite (lightweight, file-based)
- Automatic cleanup runs periodically to prevent orphaned records
- Channel member tracking is real-time via Discord events

---

## 🚀 Deployment Checklist

- [ ] Install dependencies: `pip install discord.py python-dotenv pydantic`
- [ ] Create `.env` file with all required variables
- [ ] Create Discord category and voice channel
- [ ] Copy IDs to `.env`
- [ ] Grant bot necessary permissions in the category
- [ ] Run `python main.py`
- [ ] In Discord, run `/register` to set up the server
- [ ] Test by joining the Create VC channel
- [ ] (Optional) Run `!syncglobal` to register commands globally

---

## 🐛 Troubleshooting

### Bot doesn't create channels
- ✅ Check that you ran `/register` in the server
- ✅ Verify bot has `Manage Channels` and `Move Members` permissions
- ✅ Ensure the creator channel ID is correct
- ✅ Run `/unregister` and again run `/register`in the server to reset server config

### Channels aren't being deleted when empty
- ✅ Check that bot has permission to delete channels in the category
- ✅ Verify the channel is actually empty (no members, not even bots)
- ✅ Check `error.log` for detailed error information

### Commands aren't showing up
- ✅ Run `!syncguild` (in the server) or `!syncglobal` (for all servers)
- ✅ Wait a few seconds for Discord to update

### Database errors
- ✅ Check that `discord_server.db` and `discord_channel.db` exist in the root directory
- ✅ Verify write permissions on the directory
- ✅ Check `error.log` for detailed database error traces

---

## 📜 License

This project is licensed under the [MIT License](LICENSE)

---

## 📞 Support

For issues, feature requests, or questions:
1. Check the [GitHub Issues](https://github.com/code-1py/VoiceForge/issues)
2. Review the logs in the `Logs/` directory
3. Ensure all environment variables are set correctly

---

**Made with ❤️ by code-1py**