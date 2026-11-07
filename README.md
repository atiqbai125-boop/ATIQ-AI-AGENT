# ATIQ AI AGENT

A private Telegram coding assistant powered by Gemini, built with Python, FastAPI and Render.

## Included
- Owner-only Telegram bot
- Gemini text and image understanding
- Voice transcription through Gemini and optional Bengali voice replies through Edge TTS
- ZIP upload, safe extraction, project inventory and text-file edits
- Backups before replacing text files
- Updated project ZIP returned to Telegram
- API key update using `/setkey`
- FastAPI health endpoint for Render

## Safety and current limitations
- The agent does **not** execute uploaded code, shell commands, APK builds, installers, or scripts.
- It edits only allow-listed text files in the uploaded ZIP.
- ZIP path traversal, symlink entries, hidden paths and oversized archives are rejected.
- It does not access the phone's local storage; upload files through Telegram.
- A screenshot is analyzed and explained; visual UI implementation can be generated from a text/ZIP task.
- TTS requires outbound access to the Edge TTS service. Text reply still works if voice generation fails.
- This starter is a foundation, not an unrestricted autonomous computer operator. Review AI-generated changes before using them.

## 1. Create Telegram bot
Use Telegram's official BotFather to create a bot and copy its token.
Find your numeric Telegram user ID using a trusted Telegram ID utility, then set it as `OWNER_TELEGRAM_ID`.
Do not share your bot token or Gemini API key.

## 2. Local run
Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS/Termux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your own values
python main.py
```

Open `http://127.0.0.1:10000/health` to check the service.

## 3. Deploy to Render
1. Create a private GitHub repository and upload this project.
2. In Render, choose **New + > Blueprint** and connect the repository.
3. Render reads `render.yaml`. Review the service and create it.
4. Add `TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, and `GEMINI_API_KEY` in the Render Environment page.
5. Keep the persistent disk mounted at `/var/data`. The Blueprint requests a paid Starter instance and a 1 GB disk.
6. Deploy and open `https://YOUR-SERVICE.onrender.com/health`.
7. Open the Telegram bot and send `/start`.

Render web services need to bind to `0.0.0.0` and the `PORT` environment variable; this app does that.

## 4. Bot usage
- `/start`
- `/help`
- `/status`
- `/setkey YOUR_GEMINI_API_KEY`
- Send a normal text question.
- Send a screenshot with a caption describing the UI/code you want.
- Send a `.zip` project with a caption such as: "Review this project, fix the listed UI bug, and return the updated ZIP."
- Send a voice message for transcription and a text/voice response.

## 5. Important
The `/setkey` command deletes the message containing the key where Telegram permits it. Prefer setting the initial key through Render Environment. The bot stores replacement keys encrypted using `BOT_SECRET_KEY`. If you change `BOT_SECRET_KEY`, previously stored encrypted keys cannot be decrypted; set the Gemini key again.

Do not commit `.env`, API keys, bot tokens, or private project files to GitHub.
