import os, re, shutil, tempfile, logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from core.config import OWNER_ID, WORK_DIR, MAX_UPLOAD_MB
from core.storage import save_api_key, get_api_key
from core.project import extract_zip, inventory, read_project_context, apply_operations, make_zip
from ai.gemini import ask_text, inspect_image, transcribe_audio, parse_agent_json

log = logging.getLogger(__name__)

def is_owner(update):
    return bool(update.effective_user and update.effective_user.id == OWNER_ID)

async def deny(update):
    if update.effective_message:
        await update.effective_message.reply_text("এই বটটি ব্যক্তিগতভাবে ব্যবহারের জন্য অনুমোদিত নয়।")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update): return await deny(update)
    await update.message.reply_text(
        "স্বাগতম! আমি ATIQ AI AGENT।\n\n"
        "কোড/প্রশ্ন পাঠাও, স্ক্রিনশট পাঠাও, অথবা ZIP প্রজেক্টের সঙ্গে কাজের নির্দেশনা দাও।\n"
        "/help — কমান্ড\n/setkey YOUR_GEMINI_KEY — API Key সেট\n/status — সার্ভিস অবস্থা"
    )

async def help_command(update, context):
    if not is_owner(update): return await deny(update)
    await update.message.reply_text(
        "কমান্ড:\n/start — শুরু\n/help — সাহায্য\n/status — অবস্থা\n"
        "/setkey KEY — Gemini API Key পরিবর্তন\n\n"
        "ZIP-এর caption-এ কাজের নির্দেশনা লিখে পাঠাও। সাধারণ ফাইল/ছবি পাঠালেও নির্দেশনা caption-এ লিখতে পারো।\n"
        "সীমা: সর্বোচ্চ %d MB। আপলোড করা প্রজেক্টের বাইরে কোনো ফাইল অ্যাক্সেস করা হয় না।" % MAX_UPLOAD_MB
    )

async def status(update, context):
    if not is_owner(update): return await deny(update)
    await update.message.reply_text(
        "ATIQ AI AGENT: Online\nGemini API: " + ("Configured" if get_api_key() else "Not configured")
    )

async def setkey(update, context):
    if not is_owner(update): return await deny(update)
    if update.effective_chat.type != "private":
        return await update.message.reply_text("API Key শুধু বটের Private Chat-এ পরিবর্তন করো।")
    if not context.args:
        return await update.message.reply_text("ব্যবহার: /setkey YOUR_GEMINI_API_KEY")
    key = context.args[0].strip()
    if len(key) < 20:
        return await update.message.reply_text("API Key সঠিক মনে হচ্ছে না। আবার চেষ্টা করো।")
    save_api_key(key)
    try:
        await update.message.delete()
    except Exception:
        pass
    await update.effective_chat.send_message("Gemini API Key এনক্রিপ্ট করে সংরক্ষণ করা হয়েছে।")

async def _download(update, context, tg_file, filename):
    if tg_file.file_size and tg_file.file_size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"ফাইলের সীমা {MAX_UPLOAD_MB} MB।")
    path = WORK_DIR / f"upload_{update.effective_user.id}_{next(tempfile._get_candidate_names())}"
    await tg_file.download_to_drive(custom_path=str(path))
    return path

async def _run_project(update, instruction, zip_path):
    user_dir = WORK_DIR / str(OWNER_ID)
    if user_dir.exists():
        shutil.rmtree(user_dir)
    user_dir.mkdir(parents=True, exist_ok=True)
    extract_zip(zip_path, user_dir)
    context_text = read_project_context(user_dir)
    prompt = (
        "Uploaded project file list:\n" + "\n".join(inventory(user_dir)) +
        "\n\nReadable source files:\n" + context_text +
        "\n\nUser request:\n" + (instruction or "Analyze this project and summarize its structure. Do not change files.")
    )
    raw = ask_text(prompt)
    data = parse_agent_json(raw)
    changed = apply_operations(user_dir, data.get("operations", []))
    reply = data.get("reply", "কাজ সম্পন্ন।")
    if changed:
        out = WORK_DIR / f"ATIQ_AI_AGENT_UPDATED_{update.effective_user.id}.zip"
        make_zip(user_dir, out)
        await update.effective_message.reply_text(reply + "\n\nপরিবর্তিত ফাইল:\n" + "\n".join(changed))
        with open(out, "rb") as f:
            await update.effective_message.reply_document(f, filename=out.name, caption="আপডেট করা প্রজেক্ট ZIP")
    else:
        await update.effective_message.reply_text(reply + "\n\nকোনো ফাইল পরিবর্তন করা হয়নি।")

async def text_message(update, context):
    if not is_owner(update): return await deny(update)
    try:
        await update.message.reply_text("কাজটি বিশ্লেষণ করছি…")
        result = ask_text(update.message.text)
        try:
            data = parse_agent_json(result)
            await update.message.reply_text(data.get("reply", result)[:4000])
        except Exception:
            await update.message.reply_text(result[:4000])
    except Exception as e:
        log.exception("text task failed")
        await update.message.reply_text("সমস্যা হয়েছে: " + str(e)[:800])

async def photo_message(update, context):
    if not is_owner(update): return await deny(update)
    try:
        photo = update.message.photo[-1]
        tg = await context.bot.get_file(photo.file_id)
        path = await _download(update, context, tg, "image.jpg")
        answer = inspect_image(update.message.caption or "Describe this screenshot and suggest implementation.", path.read_bytes(), "image/jpeg")
        await update.message.reply_text(answer[:4000])
        path.unlink(missing_ok=True)
    except Exception as e:
        log.exception("image task failed")
        await update.message.reply_text("ছবি বিশ্লেষণে সমস্যা: " + str(e)[:700])

async def document_message(update, context):
    if not is_owner(update): return await deny(update)
    path = None
    try:
        doc = update.message.document
        tg = await context.bot.get_file(doc.file_id)
        path = await _download(update, context, tg, doc.file_name or "upload")
        caption = update.message.caption or ""
        if path.suffix.lower() == ".zip":
            await update.message.reply_text("ZIP প্রজেক্ট পরীক্ষা করছি…")
            await _run_project(update, caption, path)
        elif path.suffix.lower() in {".png",".jpg",".jpeg",".webp"}:
            answer = inspect_image(caption or "Analyze this image.", path.read_bytes(), doc.mime_type or "image/jpeg")
            await update.message.reply_text(answer[:4000])
        else:
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                await update.message.reply_text("এই ফাইলটি সরাসরি পড়া যাচ্ছে না। TXT/কোড/ZIP ফাইল পাঠাও।")
                return
            prompt = (caption or "Review this file and explain it.") + "\n\nFILE: " + (doc.file_name or "uploaded") + "\n" + content[:30000]
            await update.message.reply_text(ask_text(prompt)[:4000])
    except Exception as e:
        log.exception("document task failed")
        await update.message.reply_text("ফাইল প্রসেস করতে সমস্যা: " + str(e)[:800])
    finally:
        if path:
            path.unlink(missing_ok=True)

async def voice_message(update, context):
    if not is_owner(update): return await deny(update)
    path = None
    try:
        voice = update.message.voice or update.message.audio
        tg = await context.bot.get_file(voice.file_id)
        path = await _download(update, context, tg, "voice.ogg")
        transcript = transcribe_audio(path.read_bytes(), "audio/ogg")
        if not transcript.strip():
            return await update.message.reply_text("ভয়েস থেকে কথা বোঝা যায়নি। আবার পাঠাও।")
        await update.message.reply_text("শুনেছি: " + transcript[:1000])
        result = ask_text(transcript)
        try:
            data = parse_agent_json(result)
            reply = data.get("reply", result)
        except Exception:
            reply = result
        await update.message.reply_text(reply[:4000])
        # Optional voice output through edge-tts; text reply remains available if TTS fails.
        try:
            import edge_tts
            audio_path = WORK_DIR / f"reply_{update.effective_user.id}.mp3"
            await edge_tts.Communicate(reply[:2500], "bn-BD-NabanitaNeural").save(str(audio_path))
            with open(audio_path, "rb") as audio:
                await update.message.reply_voice(audio)
            audio_path.unlink(missing_ok=True)
        except Exception as tts_error:
            log.warning("TTS unavailable: %s", tts_error)
    except Exception as e:
        log.exception("voice task failed")
        await update.message.reply_text("ভয়েস প্রসেস করতে সমস্যা: " + str(e)[:700])
    finally:
        if path:
            path.unlink(missing_ok=True)

async def error_handler(update, context):
    log.exception("Telegram handler error", exc_info=context.error)
