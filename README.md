# 🎙️ VoiceForge v2.0

A self-hosted Discord bot for dynamic temporary voice channel management, featuring a fully interactive TempVoice-style dashboard.

## ✨ What's New in v2.0

- 🎛️ **Interactive Panel** — TempVoice-style UI with buttons for all channel controls
- 📨 **Native Member Search** — Discord's built-in member picker for invite, trust, and ban
- 👑 **Smart Claim System** — Automatically handles ownership recovery
- 🔒 **Panel sent directly into your temp VC** — No extra channels needed

## ✨ Features

- Auto-creates a personal voice channel when a user joins the designated **"Create VC"** channel
- Automatically deletes empty channels when everyone leaves
- Full ownership system with claim and transfer support
- Rich set of slash commands for channel management
- Interactive button panel sent directly into each created voice channel

## 📁 Project Structure
```
├── main.py                  # Bot entry point and configuration
├── config.py                # Cooldown and limit constants
├── logger.py                # Error and info logging setup
├── cogs/
│   ├── voice_manager.py     # Auto voice channel creation and deletion
│   ├── voice_interface.py   # Interactive panel UI (buttons, modals, selects)
│   ├── voice_controls.py    # All slash commands for channel control
│   ├── error_handling.py    # Global error handler
│   └── sync_command.py      # Slash command sync and help utilities
```

## ⚙️ Setup

### 1. Clone the repository
```bash
git clone https://github.com/code-1py/VoiceForge
cd VoiceForge
```

### 2. Install dependencies
```bash
pip install discord.py python-dotenv
```

### 3. Configure environment variables

Create a `.env` file in the root directory:
```env
VOICE_BOT_TOKEN=your_bot_token_here
CUSTOM_VOICE_CATEGORY_ID=your_category_id_here
CUSTOM_VOICE_CHANNEL_ID=your_create_vc_channel_id_here
SERVER_ID=your_server_id_here
```

### 4. Run the bot
```bash
python main.py
```

## 🔧 Discord Setup

1. Create a **Category** where voice channels will be created
2. Inside that category, create a **Voice Channel** that will act as the trigger (e.g. `➕ Create VC`)
3. Copy the **Category ID** and **Channel ID** into your `.env` file
4. Make sure the bot has the following permissions:
   - `Manage Channels`
   - `Move Members`
   - `View Channels`
   - `Connect`
   - `Send Messages`

## 🎛️ Interactive Panel

When a user joins the Create VC channel, a panel is automatically sent inside their new voice channel with the following buttons:

| Button | Description |
|---|---|
| 🔒 Lock | Block others from joining |
| 🔓 Unlock | Allow others to join |
| 🙈 Hide | Hide from channel list |
| 👁️ Show | Make visible in channel list |
| ✏️ Rename | Change your channel name |
| 👥 Set Limit | Cap max members (0 = unlimited) |
| 📨 Invite | Search and allow a member to join |
| 👢 Kick | Disconnect a member |
| 🚫 Ban | Search and block a member |
| ✅ Trust | Search and give full permissions |
| ⛔ Untrust | Remove a member's trust |
| ✔️ Unblock | Remove a member's ban |
| 🔁 Transfer | Give ownership to someone else |
| 👑 Claim | Claim an abandoned channel |
| 🗑️ Delete | Delete your channel permanently |

> All controls are owner-only except **Claim**.

You can also manually send a panel to any channel using `/panel` (requires Manage Channels permission).

## 🛠️ Owner Commands (Prefix: `!`)

| Command | Description |
|---|---|
| `!syncguild` | Sync slash commands to the current server |
| `!syncglobal` | Sync slash commands globally |
| `!clearguild` | Clear all guild slash commands |
| `!clearglobal` | Clear all global slash commands |

## 📋 Slash Commands

### Channel Management

| Command | Description | Cooldown |
|---|---|---|
| `/rename <name>` | Rename your voice channel (max 32 characters) | 300s |
| `/limit <number>` | Set user limit (1–99), or 0 to remove | 3s |
| `/delete` | Delete your voice channel | 5s |
| `/lock` | Lock the channel so no one can join | 4s |
| `/unlock` | Unlock the channel | 4s |
| `/hide` | Hide the channel from everyone | 5s |
| `/unhide` | Make the channel visible again | 5s |

### Ownership

| Command | Description | Cooldown |
|---|---|---|
| `/claim` | Claim an unowned or abandoned channel | 90s |
| `/transfer <member>` | Transfer ownership to another member | 90s |

### Member Control

| Command | Description | Cooldown |
|---|---|---|
| `/kick <members>` | Kick up to 5 members from your channel | 2s |
| `/invite <members>` | Send a DM invite to up to 5 members | 5s |
| `/trust <members>` | Allow up to 5 members to view/join even if locked or hidden | 4s |
| `/untrust <members>` | Remove up to 5 members from the trusted list | 4s |
| `/trusted` | View the trusted members list | 3s |
| `/block <members>` | Kick and block up to 5 members | 3s |
| `/unblock <members>` | Remove up to 5 members from the blocked list | 3s |
| `/blocked` | View the blocked members list | 3s |

### Help

| Command | Description |
|---|---|
| `/help` | Shows all available slash commands |

## 📝 Logs

Logs are stored in the `Logs/` directory:
- `VOICE_BOT.log` — General bot activity
- `error.log` — Unexpected errors with timestamps

## 📌 Notes

- All voice control commands only work inside channels created by this bot
- Only the **channel owner** can use management commands
- Channels are automatically deleted when they become empty
- Ownership data is stored in-memory and resets on bot restart — use **Claim** to re-register

## 📜 License

This project is licensed under the [MIT License](LICENSE)
