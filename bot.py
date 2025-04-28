import os
import requests
from io import BytesIO
from PIL import Image
from flask import Flask, request
from telegram import Bot, Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import qrcode
from rembg import remove
from transformers import pipeline
import random

# Bot token
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

# Flask app
app = Flask(__name__)

application = ApplicationBuilder().token(BOT_TOKEN).build()

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "**Welcome to ALL_IN_1TOOLS_BOT!**\n\nAvailable Commands:\n"
        "/removebg - Remove Image Background\n"
        "/pdf - Convert Images to PDF\n"
        "/texttoimage - Generate AI Image\n"
        "/compress - Compress an Image\n"
        "/qr - Generate QR Code\n"
        "/translate - Translate Text\n"
        "/convert - Currency Convert\n"
        "/upscale - Image Upscale\n"
        "/summarize - Summarize Text\n"
        "/joke - Get a Joke\n"
        "/weather - Weather Info\n"
        "/cartoonify - Cartoonify an Image\n"
        "/ytdown - YouTube Thumbnail Downloader\n"
    )

# Remove Background
async def removebg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_data = await file.download_as_bytearray()

        headers = {"X-Api-Key": "qLfRtLd6MebVzGTuFcQ7Yv9j"}
        response = requests.post(
            "https://api.remove.bg/v1.0/removebg",
            files={"image_file": img_data},
            headers=headers,
        )
        output = BytesIO(response.content)
        output.name = "no-bg.png"
        await update.message.reply_document(document=output)
    else:
        await update.message.reply_text("Please send a photo after using /removebg.")

# Image to PDF
pdf_images = {}
async def pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me images one by one. Type /done when finished.")

async def save_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in pdf_images:
        pdf_images[user_id] = []
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    img = Image.open(BytesIO(await file.download_as_bytearray())).convert("RGB")
    pdf_images[user_id].append(img)
    await update.message.reply_text("Image added.")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in pdf_images and pdf_images[user_id]:
        output = BytesIO()
        pdf_images[user_id][0].save(output, save_all=True, append_images=pdf_images[user_id][1:], format="PDF")
        output.name = "output.pdf"
        output.seek(0)
        await update.message.reply_document(document=output)
        del pdf_images[user_id]
    else:
        await update.message.reply_text("No images to save.")

# Text to Image (using placeholder API)
async def texttoimage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = ' '.join(context.args)
    if not prompt:
        await update.message.reply_text("Usage: /texttoimage your prompt")
        return
    await update.message.reply_text(f"Here is your generated image for prompt: '{prompt}' (Feature coming soon)")

# Compress Image
async def compress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img = Image.open(BytesIO(await file.download_as_bytearray()))
        output = BytesIO()
        img.save(output, "JPEG", quality=20)
        output.name = "compressed.jpg"
        output.seek(0)
        await update.message.reply_document(document=output)
    else:
        await update.message.reply_text("Please send an image after /compress.")

# QR Code
async def qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("Usage: /qr your_text_here")
        return
    qr_img = qrcode.make(text)
    output = BytesIO()
    qr_img.save(output, format="PNG")
    output.name = "qr.png"
    output.seek(0)
    await update.message.reply_document(document=output)

# Translator
async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("Usage: /translate your_text_here"ication.add_handler(CommandHandler("joke", joke))
application.add_handler(CommandHandler("weather", weather))
application.add_handler(CommandHandler("cartoonify", cartoonify))
application.add_handler(CommandHandler("ytdown", ytdown))
application.add_handler(MessageHandler(filters.PHOTO, save_image))

# Flask for Keep Alive
@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)
    return "ok"

if __name__ == "__main__":
    application.run_polling()
