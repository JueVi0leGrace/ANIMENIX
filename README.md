# LinkHide Bot (Python / Termux)

A Telegram bot that hides links behind text or inline buttons.

## Features
- `/hide <url> <text>` – hidden text link
- `/button <url> | <label> | <message>` – message with an inline button
- `/buttons` – several buttons (one `url | label` per line)
- Send a bare link -> choose "Hidden text link" or "Inline button" -> send the text
- `/start`, `/help`, `/cancel`

> Note: this is an independent bot. The features of @lINkHID_BOT could not be
> verified, so this follows the common link-hider pattern.

## 1. Create the bot token
1. Open Telegram, chat with **@BotFather**
2. Send `/newbot`, follow the steps, copy the token
3. (Optional) `/setcommands` and paste:
```
start - Start the bot
help - Show help
hide - Hide a link behind text
button - Message with an inline button
buttons - Message with several buttons
cancel - Cancel current action
```

## 2. Install on Android (Termux)
Install Termux from **F-Droid** (the Play Store version is outdated).
```bash
pkg update -y && pkg upgrade -y
pkg install python -y
mkdir -p ~/linkhide && cd ~/linkhide
```
Copy `bot.py`, `requirements.txt` and `env.example` into `~/linkhide`
(e.g. save them with `nano`, or run `termux-setup-storage` and copy from
Downloads: `cp ~/storage/downloads/linkhide-bot/* ~/linkhide/`).

```bash
pip install -r requirements.txt
cp env.example .env
nano .env          # replace PASTE_YOUR_TOKEN_HERE with your token
python bot.py
```

## 3. Keep it running in the background
```bash
pkg install tmux -y
termux-wake-lock
tmux new -s bot
python bot.py
# detach: Ctrl+B then D     reattach: tmux attach -t bot
```
In Android settings, set Termux battery usage to **Unrestricted** so it isn't killed.

## Troubleshooting
- `BOT_TOKEN is missing` -> check `.env` is in the same folder as `bot.py`.
- `Unauthorized` -> token is wrong; copy it again from @BotFather.
- Buttons need links starting with `http://` or `https://`.
- Never share your token. If leaked, use `/revoke` in @BotFather.
