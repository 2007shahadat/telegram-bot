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
        await update.message.reply_text("Usage: /translate your_text_here")
        return
    response = requests.get(f"https://api.mymemory.translated.net/get?q={text}&langpair=en|bn")
    result = response.json()
    translated = result['responseData']['translatedText']
    await update.message.reply_text(f"Translated Text: {translated}")

# Currency Converter
async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Usage: /convert 100 USD BDT")
        return
    amount, from_currency, to_currency = args
    response = requests.get(f"https://api.exchangerate.host/convert?from={from_currency}&to={to_currency}&amount={amount}")
    result = response.json()
    if result["success"]:
        converted = result["result"]
        await update.message.reply_text(f"{amount} {from_currency} = {converted:.2f} {to_currency}")
    else:
        await update.message.reply_text("Conversion failed.")

# Upscale (fake)
async def upscale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Upscaling image... (Feature coming soon!)")

# Summarize
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
async def summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("Usage: /summarize your_text")
        return
    if len(text) < 50:
        await update.message.reply_text("Please provide a longer text (at least 50 characters).")
        return
    summary = summarizer(text, max_length=50, min_length=25, do_sample=False)[0]['summary_text']
    await update.message.reply_text(f"Summary: {summary}")

# Joke Generator
english_jokes = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "I told my computer I needed a break, and it said 'No problem – I'll go to sleep.'",
]
bangla_jokes = [
    "পিয়াজের দামে এমন এক অবস্থা, চোখে জল আসার আগেই পকেট ফাঁকা হয়ে যায়!",
    "গার্লফ্রেন্ড: আমি কি মোটা? বয়ফ্রেন্ড: তুমি তো শুধু মিষ্টি!",
]
async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jokes = english_jokes + bangla_jokes
    await update.message.reply_text(random.choice(jokes))

# Weather
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = ' '.join(context.args)
    if not city:
        await update.message.reply_text("Usage: /weather city_name")
        return
    api_key = "7b802f221d6041238efc91a6ad39f4a7" # (Free API key use করছি)
    response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric")
    if response.status_code == 200:
        data = response.json()
        weather_info = f"City: {data['name']}\nTemp: {data['main']['temp']}°C\nWeather: {data['weather'][0]['description']}"
        await update.message.reply_text(weather_info)
    else:
        await update.message.reply_text("City not found!")

# Cartoonify (fake)
async def cartoonify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cartoonify feature coming soon!")

# YouTube Thumbnail Downloader
async def ytdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = ' '.join(context.args)
    if "youtube.com/watch?v=" not in url:
        await update.message.reply_text("Please send a valid YouTube link.")
        return
    video_id = url.split("v=")[1]
    thumb_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    await update.message.reply_photo(thumb_url)

# Handle Commands
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("removebg", removebg))
application.add_handler(CommandHandler("pdf", pdf))
application.add_handler(CommandHandler("done", done))
application.add_handler(CommandHandler("texttoimage", texttoimage))
application.add_handler(CommandHandler("compress", compress))
application.add_handler(CommandHandler("qr", qr))
application.add_handler(CommandHandler("translate", translate))
application.add_handler(CommandHandler("convert", convert))
application.add_handler(CommandHandler("upscale", upscale))
application.add_handler(CommandHandler("summarize", summarize))
application.add_handler(CommandHandler("joke", joke))
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
