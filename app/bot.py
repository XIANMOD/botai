import logging, os, shutil, uuid
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from .config import settings
from .image_pipeline import ai_outpaint
from .live_photo import make_live_photo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dimz")

RATIO_KEYS = ["9:16", "16:9", "19:6", "1:1", "4:5", "3:4"]

def user_dir(user_id: int):
    p = Path(settings.work_dir) / str(user_id) / uuid.uuid4().hex[:8]
    p.mkdir(parents=True, exist_ok=True)
    return p

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🖼️ AI Photo Resize", callback_data="menu:image"),
         InlineKeyboardButton("🎞️ Live Photo iPhone", callback_data="menu:live")],
        [InlineKeyboardButton("ℹ️ Cara penggunaan", callback_data="menu:help")]
    ]
    await update.message.reply_text(
        "✨ DIMZ AI RESIZER\\n\\nKirim foto untuk AI Outpainting atau video untuk membuat "
        "paket Live Photo iPhone.\\n\\nPilih fitur di bawah atau langsung kirim file.",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "PHOTO: kirim foto → pilih rasio → bot memperluas area kosong dengan AI.\\n"
        "LIVE PHOTO: kirim video → bot mengambil klip pendek + key photo → ZIP.\\n"
        "Catatan: Live Photo ZIP adalah pasangan aset; pengenalan native Apple Photos tidak dijamin.")

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    action = q.data
    if action == "menu:image":
        context.user_data["mode"] = "image"
        await q.message.reply_text("Kirim foto yang ingin diubah rasionya.")
    elif action == "menu:live":
        context.user_data["mode"] = "live"
        await q.message.reply_text("Kirim video pendek. Bot akan membuat pasangan key photo + MOV.")
    elif action == "menu:help":
        await q.message.reply_text("Kirim foto/video langsung. Ukuran upload dibatasi Telegram dan MAX_UPLOAD_MB.")

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    if photo.file_size and photo.file_size > settings.max_upload_mb * 1024 * 1024:
        return await update.message.reply_text(f"File terlalu besar. Batas bot: {settings.max_upload_mb} MB.")
    work = user_dir(update.effective_user.id)
    src = work / "source.jpg"
    tgfile = await context.bot.get_file(photo.file_id)
    await tgfile.download_to_drive(src)
    context.user_data["source_path"] = str(src)
    context.user_data["work_dir"] = str(work)
    context.user_data["media_type"] = "image"
    buttons = [[InlineKeyboardButton(r, callback_data=f"ratio:{r}") for r in RATIO_KEYS[i:i+3]]
               for i in range(0, len(RATIO_KEYS), 3)]
    await update.message.reply_text("Pilih rasio output:", reply_markup=InlineKeyboardMarkup(buttons))

async def ratio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ratio = q.data.split(":", 1)[1]
    src = Path(context.user_data.get("source_path", ""))
    if not src.exists():
        return await q.message.reply_text("Foto sumber tidak ditemukan. Kirim ulang fotonya.")
    output = Path(context.user_data["work_dir"]) / f"DIMZ_{ratio.replace(':','-')}.png"
    msg = await q.message.reply_text(f"⏳ Memproses foto ke {ratio}. AI sedang memperluas area...")
    try:
        result = await __import__("asyncio").to_thread(ai_outpaint, src, ratio, output)
        await q.message.reply_document(document=result.open("rb"), filename=result.name,
                                       caption=f"✅ Selesai — rasio {ratio}\\nDIMZ AI RESIZER")
    except Exception as e:
        log.exception("image processing failed")
        await q.message.reply_text(f"❌ Gagal memproses: {str(e)[:700]}")
    finally:
        try: await msg.delete()
        except Exception: pass

async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    media = update.message.video or update.message.document
    if media.file_size and media.file_size > settings.max_upload_mb * 1024 * 1024:
        return await update.message.reply_text(f"Video terlalu besar. Batas bot: {settings.max_upload_mb} MB.")
    work = user_dir(update.effective_user.id)
    src = work / "source_video.mp4"
    tgfile = await context.bot.get_file(media.file_id)
    await tgfile.download_to_drive(src)
    msg = await update.message.reply_text("⏳ Membuat Live Photo asset pair...")
    try:
        archive = await __import__("asyncio").to_thread(make_live_photo, src, work)
        await update.message.reply_document(document=archive.open("rb"), filename=archive.name,
            caption="✅ Paket Live Photo siap. Baca IMPORT.txt di dalam ZIP untuk langkah impor ke iPhone.")
    except Exception as e:
        log.exception("live photo processing failed")
        await update.message.reply_text(f"❌ Gagal memproses video: {str(e)[:700]}")
    finally:
        try: await msg.delete()
        except Exception: pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Unhandled exception", exc_info=context.error)

def main():
    if not settings.telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN belum diatur.")
    Path(settings.work_dir).mkdir(parents=True, exist_ok=True)
    app = Application.builder().token(settings.telegram_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(ratio_callback, pattern=r"^ratio:"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, receive_video))
    app.add_error_handler(error_handler)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
