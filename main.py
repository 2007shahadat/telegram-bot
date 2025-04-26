import os
import requests
from io import BytesIO
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
import qrcode
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, Dispatcher
import asyncio

# CONFIG
BOT_TOKEN = "7754654122:AAFGTvgsF-NjzYKgVVfmZvZjR_FHGvcrlDQ"
REMOVE_BG_API = "qLfRtLd6MebVzGTuFcQ7Yv9j"
OPENWEATHER_API = "5e86e15f18ea4b5b9d942634e2f9d63e" # Free Key
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

user_images = {}
user_upscale_requests = {}

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "**Welcome! Available Commands:**\n\n"
        "/removebg\n/pdf\n/texttoimage\n/compress\n/qr\n/translate\n/convert\n/upscale\n"
        "/summarize\n/joke en or bn\n/cartoonify\n/ytthumb\n/weather\n",
    )

# REMOVE BG
async def removebg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await bot.get_file(photo.file_id)
    img_data = await file.download_as_bytearray()
    response = requests.post(
        'https://api.remove.bg/v1.0/removebg',
        files={'image_file': BytesIO(img_data)},
        data={'size': 'auto'},
        headers={'X-Api-Key': REMOVE_BG_API},
    )
    if response.status_code == 200:
        await update.message.reply_document(document=BytesIO(response.content), filename="no-bg.png")
    else:
        await update.message.reply_text('RemoveBG failed.')

# PDF
async def pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_images:
        user_images[user_id] = []
    photo = update.message.photo[-1]
    file = await bot.get_file(photo.file_id)
    img = Image.open(BytesIO(await file.download_as_bytearray())).convert("RGB")
    user_images[user_id].append(img)
    if len(user_images[user_id]) >= 2:
        pdf_path = BytesIO()
        user_images[user_id][0].save(pdf_path, save_all=True, append_images=user_images[user_id][1:], format="PDF")
        pdf_path.name = "output.pdf"
        pdf_path.seek(0)
        await update.message.reply_document(document=pdf_path)
        user_images[user_id] = []
    else:
        await update.message.reply_text("Send one more image to create PDF.")

# TEXT TO IMAGE
async def texttoimage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    img = Image.new('RGB', (600, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 90), text, fill=(0, 0, 0))
    output = BytesIO()
    output.name = 'text.png'
    img.save(output, 'PNG')
    output.seek(0)
    await update.message.reply_photo(photo=output)

# COMPRESS
async def compress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await bot.get_file(photo.file_id)
    img = Image.open(BytesIO(await file.download_as_bytearray()))
    output = BytesIO()
    output.name = "compressed.jpg"
    img.save(output, "JPEG", optimize=True, quality=30)
    output.seek(0)
    await update.message.reply_photo(photo=output)

# QR
async def qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    qr_img = qrcode.make(text)
    output = BytesIO()
    output.name = 'qr.png'
    qr_img.save(output, 'PNG')
    output.seek(0)
    await update.message.reply_photo(photo=output)

# TRANSLATE
async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /translate text lang")
        return
    *text_parts, lang = context.args
    text = " ".join(text_parts)
    url = f"https://api.mymemory.translated.net/get?q={text}&langpair=en|{lang}"
    data = requests.get(url).json()
    translated = data['responseData']['translatedText']
    await update.message.reply_text(f"Translated: {translated}")

# CONVERT CURRENCY (MOCK)
async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(context.args[0])
        from_currency = context.args[1].upper()
        to_currency = context.args[2].upper()
        rate = 1.1
        converted = amount * rate
        await update.message.reply_text(f"{amount} {from_currency} = {converted:.2f} {to_currency}")
    except:
        await update.message.reply_text("Use: /convert 100 USD EUR")

# UPSCALE
async def upscale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if len(context.args) != 1 or context.args[0] not in ["2x", "4x", "6x"]:
        await update.message.reply_text("Use: /upscale 2x or 4x or 6x")
        return
    scale = int(context.args[0].replace("x", ""))
    user_upscale_requests[user_id] = scale
    await update.message.reply_text(f"Send an image to upscale {scale}x")

# UPSCALE HANDLE PHOTO
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_upscale_requests:
        scale = user_upscale_requests.pop(user_id)
        photo = update.message.photo[-1]
        file = await bot.get_file(photo.file_id)
        img = Image.open(BytesIO(await file.download_as_bytearray()))
        img = img.resize((img.width * scale, img.height * scale))
        output = BytesIO()
        output.name = "upscaled.png"
        img.save(output, "PNG")
        output.seek(0)
        await update.message.reply_photo(photo=output)

# SUMMARIZE
async def summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if len(text) < 50:
        await update.message.reply_text("Text too short to summarize.")
        return
    sentences = text.split(".")
    short_summary = ". ".join(sentences[:2]) + "."
    await update.message.reply_text(f"Summary: {short_summary}")

# JOKE
async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.args[0] if context.args else "en"
    jokes_en = ["Why don't scientists trust atoms? Because they make up everything!", "I told my computer I needed a break, and it said no problem—it'll go to sleep!"]
    jokes_bn = ["একজন পাগল বলল: আমি তোমার ছাতা চুরি করিনি, আমি তো ভেবেছিলাম এটা আমার উইংস।", "স্যার: পড়াশুনা করলে কী হবে? ছাত্র: মোবাইলের চার্জ ফুরাবে।"]
    if lang == "bn":
        await update.message.reply_text(random.choice(jokes_bn))
    else:
        await update.message.reply_text(random.choice(jokes_en))

# CARTOONIFY (Mock)
async def cartoonify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Coming soon: Cartoonify Image!")

# YOUTUBE THUMBNAIL
async def ytthumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Use: /ytthumb YouTube_link")
        return
    link = context.args[0]
    video_id = link.split("v=")[-1].split("&")[0]
    thumb_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    await update.message.reply_photo(photo=thumb_url)

# WEATHER
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = " ".join(context.args)
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API}&units=metric"
    data = requests.get(url).json()
    if data.get("main"):
        temp = data["main"]["temp"]
        await update.message.reply_text(f"Weather in {city}: {temp}°C")
    else:
        await update.message.reply_text("City not found.")

# Dispatcher
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("removebg", removebg))
application.add_handler(CommandHandler("pdf", pdf))
application.add_handler(CommandHandler("texttoimage", texttoimage))
application.add_handler(CommandHandler("compress", compress))
application.add_handler(CommandHandler("qr", qr))
application.add_handler(CommandHandler("translate", translate))
application.add_handler(CommandHandler("convert", convert))
application.add_handler(CommandHandler("upscale", upscale))
application.add_handler(CommandHandler("summarize", summarize))
application.add_handler(CommandHandler("joke", joke))
application.add_handler(CommandHandler("cartoonify", cartoonify))
application.add_handler(CommandHandler("ytthumb", ytthumb))
application.add_handler(CommandHandler("weather", weather))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# Webhook for Deta
@app.route("/", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(application.process_update(update))
    return "ok"

if __name__ == "__main__":
    app.run(port=8080)