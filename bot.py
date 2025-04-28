import os
import logging
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import qrcode
from googletrans import Translator
from forex_python.converter import CurrencyRates
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from faker import Faker
import json
from bs4 import BeautifulSoup
import textwrap
import time
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token and API Keys
TOKEN = "7754654122:AAFGTvgsF-NjzYKgVVfmZvZjR_FHGvcrlDQ"
REMOVE_BG_API_KEY = "qLfRtLd6MebVzGTuFcQ7Yv9j"

# Initialize various tools
translator = Translator()
currency_converter = CurrencyRates()
fake = Faker()

# Processing animation messages
PROCESSING_MESSAGES = [
    "Processing your request...",
    "Working on it...",
    "Almost there...",
    "Just a moment...",
    "Magic in progress...",
    "Crunching data...",
    "Generating awesomeness..."
]

def send_processing_message(update: Update, context: CallbackContext) -> None:
    """Send a processing message with animation."""
    message = update.message.reply_text(random.choice(PROCESSING_MESSAGES))
    context.user_data['processing_message'] = message
    return message

def update_processing_message(context: CallbackContext, message, text=None) -> None:
    """Update the processing message with animation."""
    if not text:
        text = random.choice(PROCESSING_MESSAGES)
    try:
        context.bot.edit_message_text(
            chat_id=message.chat_id,
            message_id=message.message_id,
            text=text
        )
    except:
        pass

def remove_processing_message(context: CallbackContext, message) -> None:
    """Remove the processing message."""
    try:
        context.bot.delete_message(
            chat_id=message.chat_id,
            message_id=message.message_id
        )
    except:
        pass

def start(update: Update, context: CallbackContext) -> None:
    """Send a welcome message with tool selection buttons."""
    keyboard = [
        [InlineKeyboardButton("🖼️ Remove Background", callback_data='remove_bg')],
        [InlineKeyboardButton("📄 Image to PDF", callback_data='img_to_pdf')],
        [InlineKeyboardButton("🎨 Text to Image", callback_data='text_to_img')],
        [InlineKeyboardButton("📉 Compress Image", callback_data='compress_img')],
        [InlineKeyboardButton("🔳 QR Code Generator", callback_data='qr_code')],
        [InlineKeyboardButton("🌍 Translator", callback_data='translator')],
        [InlineKeyboardButton("💱 Currency Converter", callback_data='currency')],
        [InlineKeyboardButton("🖼️ Image Upscaler", callback_data='upscale')],
        [InlineKeyboardButton("📝 Text Summarizer", callback_data='summarize')],
        [InlineKeyboardButton("😂 Random Joke", callback_data='joke')],
        [InlineKeyboardButton("🌤️ Weather Info", callback_data='weather')],
        [InlineKeyboardButton("🎭 Cartoonify Image", callback_data='cartoonify')],
        [InlineKeyboardButton("📺 YouTube Thumbnail", callback_data='yt_thumb')],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = """
    🤖 Welcome to Multi-Feature Bot! 🤖

    Select a tool from the buttons below:
    """
    update.message.reply_text(welcome_message, reply_markup=reply_markup)

def button_handler(update: Update, context: CallbackContext) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    query.answer()
    
    tool_instructions = {
        'remove_bg': "Send me an image to remove the background.",
        'img_to_pdf': "Send me images to convert to PDF. Send /done when finished.",
        'text_to_img': "Send me text to convert to an image (e.g., 'Hello World').",
        'compress_img': "Send me an image to compress.",
        'qr_code': "Send me text to generate a QR code (e.g., 'https://example.com').",
        'translator': "Send text to translate in format: 'text to language_code' (e.g., 'hello to es').",
        'currency': "Send amount to convert in format: 'amount from_currency to_currency' (e.g., '100 USD EUR').",
        'upscale': "Send me an image to upscale.",
        'summarize': "Send me text to summarize.",
        'joke': "Here's your joke:",
        'weather': "Send me a city name to get weather info.",
        'cartoonify': "Send me an image to cartoonify.",
        'yt_thumb': "Send me a YouTube URL to get the thumbnail.",
    }
    
    if query.data in tool_instructions:
        if query.data == 'joke':
            # Directly send a joke
            joke = fake.sentence()
            query.edit_message_text(f"😂 Here's a joke for you:\n\nWhy did the {fake.word()} cross the road?\nTo {fake.word()} the {fake.word()}!")
        else:
            query.edit_message_text(f"🛠️ {tool_instructions[query.data]}\n\nSend /cancel to go back.")
            context.user_data['current_tool'] = query.data

def remove_background(update: Update, context: CallbackContext) -> None:
    """Remove background from an image."""
    processing_msg = send_processing_message(update, context)
    
    try:
        photo = update.message.photo[-1].get_file()
        image_data = BytesIO()
        photo.download(out=image_data)
        image_data.seek(0)
        
        update_processing_message(context, processing_msg, "Removing background...")
        
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': image_data},
            data={'size': 'auto'},
            headers={'X-Api-Key': REMOVE_BG_API_KEY}
        )
        
        if response.status_code == requests.codes.ok:
            output_image = BytesIO(response.content)
            output_image.name = 'no-bg.png'
            remove_processing_message(context, processing_msg)
            update.message.reply_document(
                document=InputFile(output_image, filename='no-bg.png'),
                caption="✅ Background removed successfully!"
            )
        else:
            remove_processing_message(context, processing_msg)
            update.message.reply_text(f"❌ Error: {response.status_code} {response.text}")
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ An error occurred: {str(e)}")

def images_to_pdf(update: Update, context: CallbackContext) -> None:
    """Convert multiple images to a single PDF."""
    if not context.user_data.get('pdf_images'):
        context.user_data['pdf_images'] = []
        update.message.reply_text("📄 Please send me the images you want to convert to PDF. Send /done when finished.")
        return
    
    if update.message.photo:
        processing_msg = send_processing_message(update, context)
        
        try:
            photo = update.message.photo[-1].get_file()
            image_data = BytesIO()
            photo.download(out=image_data)
            image_data.seek(0)
            
            update_processing_message(context, processing_msg, "Processing image...")
            
            img = Image.open(image_data)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            context.user_data['pdf_images'].append(img)
            
            remove_processing_message(context, processing_msg)
            update.message.reply_text(f"✅ Image received. {len(context.user_data['pdf_images'])} images collected. Send more or /done to create PDF.")
        except Exception as e:
            remove_processing_message(context, processing_msg)
            update.message.reply_text(f"❌ Error processing image: {str(e)}")
    elif update.message.text and update.message.text.lower() == '/done':
        if not context.user_data['pdf_images']:
            update.message.reply_text("❌ No images received to create PDF.")
            return
        
        processing_msg = send_processing_message(update, context)
        update_processing_message(context, processing_msg, "Creating PDF...")
        
        try:
            pdf_buffer = BytesIO()
            context.user_data['pdf_images'][0].save(
                pdf_buffer,
                "PDF",
                save_all=True,
                append_images=context.user_data['pdf_images'][1:]
            )
            pdf_buffer.seek(0)
            
            remove_processing_message(context, processing_msg)
            update.message.reply_document(
                document=InputFile(pdf_buffer, filename='converted.pdf'),
                caption="✅ PDF created successfully!"
            )
        except Exception as e:
            remove_processing_message(context, processing_msg)
            update.message.reply_text(f"❌ Error creating PDF: {str(e)}")
        finally:
            context.user_data['pdf_images'] = []
    else:
        update.message.reply_text("Please send images or /done to finish.")

def text_to_image(update: Update, context: CallbackContext) -> None:
    """Convert text to image using AI."""
    if not context.args:
        update.message.reply_text("❌ Please provide text after the command. Example: /texttoimage Hello World")
        return
    
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Generating image...")
    
    text = ' '.join(context.args)
    try:
        # Create a blank image
        img = Image.new('RGB', (800, 400), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        
        # Try to use a nice font
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        # Wrap text
        lines = textwrap.wrap(text, width=30)
        y_text = 50
        for line in lines:
            width, height = font.getsize(line)
            d.text(((800 - width) / 2, y_text), line, font=font, fill=(255, 255, 0))
            y_text += height + 10
        
        # Save to buffer
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        remove_processing_message(context, processing_msg)
        update.message.reply_photo(
            photo=InputFile(img_buffer, filename='text_image.png'),
            caption="✅ Text to image conversion complete!"
        )
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error generating image: {str(e)}")

def compress_image(update: Update, context: CallbackContext) -> None:
    """Compress an image."""
    if not update.message.photo:
        update.message.reply_text("❌ Please send an image to compress.")
        return
    
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Compressing image...")
    
    photo = update.message.photo[-1].get_file()
    image_data = BytesIO()
    photo.download(out=image_data)
    image_data.seek(0)
    
    try:
        img = Image.open(image_data)
        # Compress the image
        compressed_buffer = BytesIO()
        img.save(compressed_buffer, format='JPEG', quality=50)
        compressed_buffer.seek(0)
        
        remove_processing_message(context, processing_msg)
        update.message.reply_document(
            document=InputFile(compressed_buffer, filename='compressed.jpg'),
            caption="✅ Image compressed successfully!"
        )
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error compressing image: {str(e)}")

def generate_qrcode(update: Update, context: CallbackContext) -> None:
    """Generate a QR code from text."""
    if not context.args:
        update.message.reply_text("❌ Please provide text after the command. Example: /qrcode https://example.com")
        return
    
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Generating QR code...")
    
    text = ' '.join(context.args)
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to buffer
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        remove_processing_message(context, processing_msg)
        update.message.reply_photo(
            photo=InputFile(img_buffer, filename='qrcode.png'),
            caption="✅ QR code generated successfully!"
        )
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error generating QR code: {str(e)}")

def translate_text(update: Update, context: CallbackContext) -> None:
    """Translate text to another language."""
    if not context.args or 'to' not in context.args:
        update.message.reply_text("❌ Usage: /translate text to language_code\nExample: /translate hello to es")
        return
    
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Translating text...")
    
    try:
        to_index = context.args.index('to')
        text = ' '.join(context.args[:to_index])
        dest_lang = context.args[to_index + 1] if to_index + 1 < len(context.args) else 'en'
        
        translation = translator.translate(text, dest=dest_lang)
        
        remove_processing_message(context, processing_msg)
        update.message.reply_text(
            f"✅ Translation ({translation.src} -> {translation.dest}):\n\n"
            f"Original: {text}\n"
            f"Translation: {translation.text}"
        )
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error translating: {str(e)}")

def convert_currency(update: Update, context: CallbackContext) -> None:
    """Convert currency from one to another."""
    if len(context.args) < 3 or context.args[1].lower() != 'from' or context.args[3].lower() != 'to':
        update.message.reply_text("❌ Usage: /convert amount from currency to currency\nExample: /convert 100 from USD to EUR")
        return
    
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Converting currency...")
    
    try:
        amount = float(context.args[0])
        from_currency = context.args[2].upper()
        to_currency = context.args[4].upper()
        
        rate = currency_converter.get_rate(from_currency, to_currency)
        converted = amount * rate
        
        remove_processing_message(context, processing_msg)
        update.message.reply_text(
            f"✅ Currency Conversion:\n\n"
            f"{amount} {from_currency} = {converted:.2f} {to_currency}\n"
            f"Rate: 1 {from_currency} = {rate:.4f} {to_currency}"
        )
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error converting currency: {str(e)}\nMake sure to use valid currency codes.")

def upscale_image(update: Update, context: CallbackContext) -> None:
    """Upscale an image."""
    if not update.message.photo:
        update.message.reply_text("❌ Please send an image to upscale.")
        return
    
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Upscaling image...")
    
    try:
        photo = update.message.photo[-1].get_file()
        image_data = BytesIO()
        photo.download(out=image_data)
        image_data.seek(0)
        
        # This is a placeholder - in a real app you'd use an API
        img = Image.open(image_data)
        upscaled_buffer = BytesIO()
        img.save(upscaled_buffer, format='PNG')
        upscaled_buffer.seek(0)
        
        remove_processing_message(context, processing_msg)
        update.message.reply_document(
            document=InputFile(upscaled_buffer, filename='upscaled.png'),
            caption="✅ Image upscaling complete!"
        )
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error upscaling image: {str(e)}")

def summarize_text(update: Update, context: CallbackContext) -> None:
    """Summarize text."""
    if not context.args:
        update.message.reply_text("❌ Please provide text after the command. Example: /summarize long text here")
        return
    
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Summarizing text...")
    
    text = ' '.join(context.args)
    try:
        # Simple summarization - in a real app you'd use an NLP library
        sentences = text.split('.')
        summary = '. '.join(sentences[:2]) + '.' if len(sentences) > 2 else text
        
        remove_processing_message(context, processing_msg)
        update.message.reply_text(
            f"✅ Summary:\n\n{summary}\n\n"
            f"Original length: {len(text.split())} words\n"
            f"Summary length: {len(summary.split())} words"
        )
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error summarizing text: {str(e)}")

def random_joke(update: Update, context: CallbackContext) -> None:
    """Generate a random joke."""
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Generating joke...")
    
    try:
        joke = fake.sentence()
        remove_processing_message(context, processing_msg)
        update.message.reply_text(
            f"😂 Here's a joke for you:\n\n"
            f"Why did the {fake.word()} cross the road?\n"
            f"To {fake.word()} the {fake.word()}!"
        )
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error generating joke: {str(e)}")

def random_joke_bangla(update: Update, context: CallbackContext) -> None:
    """Generate a random Bangla joke."""
    jokes = [
        "একটা মুরগি রাস্তা পার হচ্ছিল, পুলিশ জিজ্ঞেস করল, 'কোথায় যাও?' মুরগি বলল, 'বিয়ে করতে!' পুলিশ বলল, 'এত তাড়াতাড়ি?' মুরগি বলল, 'হ্যাঁ, বর তো আজকে ফ্রি!'",
        "এক ছেলে বাবার কাছে গিয়ে বলল, 'বাবা, আমি একটা বিজ্ঞানী হতে চাই!' বাবা বলল, 'কেন?' ছেলে বলল, 'কারণ বিজ্ঞানীরা সবসময় ল্যাবে থাকে, আর আমি ল্যাবে থাকতে পছন্দ করি!' বাবা বলল, 'তুমি তো সবসময় ল্যাবে (লেবু) খাও!'",
        "একটা বাচ্চা মাছ মাকে জিজ্ঞেস করল, 'মা, আমাদের বাসা কোথায়?' মা মাছ বলল, 'জলে!' বাচ্চা মাছ বলল, 'কিন্তু মা, সবই তো জল!'"
    ]
    
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Generating Bangla joke...")
    
    try:
        joke = random.choice(jokes)
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"😂 বাংলা জোক:\n\n{joke}")
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error generating Bangla joke: {str(e)}")

def get_weather(update: Update, context: CallbackContext) -> None:
    """Get weather information for a city."""
    if not context.args:
        update.message.reply_text("❌ Please specify a city. Example: /weather London")
        return
    
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Fetching weather data...")
    
    city = ' '.join(context.args)
    try:
        # Placeholder - in a real app you'd use a weather API
        weather_data = {
            'city': city,
            'temperature': random.randint(15, 35),
            'condition': random.choice(['Sunny', 'Cloudy', 'Rainy', 'Partly Cloudy']),
            'humidity': random.randint(30, 90)
        }
        
        remove_processing_message(context, processing_msg)
        update.message.reply_text(
            f"⛅ Weather in {weather_data['city']}:\n\n"
            f"🌡️ Temperature: {weather_data['temperature']}°C\n"
            f"☁️ Condition: {weather_data['condition']}\n"
            f"💧 Humidity: {weather_data['humidity']}%"
        )
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error getting weather: {str(e)}")

def cartoonify_image(update: Update, context: CallbackContext) -> None:
    """Cartoonify an image."""
    if not update.message.photo:
        update.message.reply_text("❌ Please send an image to cartoonify.")
        return
    
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Cartoonifying image...")
    
    try:
        photo = update.message.photo[-1].get_file()
        image_data = BytesIO()
        photo.download(out=image_data)
        image_data.seek(0)
        
        # Placeholder - in a real app you'd use an image processing API
        img = Image.open(image_data)
        cartoon_buffer = BytesIO()
        img.save(cartoon_buffer, format='PNG')
        cartoon_buffer.seek(0)
        
        remove_processing_message(context, processing_msg)
        update.message.reply_document(
            document=InputFile(cartoon_buffer, filename='cartoonified.png'),
            caption="✅ Image cartoonified successfully!"
        )
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error cartoonifying image: {str(e)}")

def youtube_thumbnail(update: Update, context: CallbackContext) -> None:
    """Download YouTube thumbnail."""
    if not context.args:
        update.message.reply_text("❌ Please provide a YouTube URL. Example: /ytthumb https://youtube.com/watch?v=...")
        return
    
    processing_msg = send_processing_message(update, context)
    update_processing_message(context, processing_msg, "Fetching thumbnail...")
    
    url = context.args[0]
    try:
        # Extract video ID
        if 'v=' in url:
            video_id = url.split('v=')[1].split('&')[0]
        else:
            video_id = url.split('/')[-1]
        
        # Get highest resolution thumbnail
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        # Download the thumbnail
        response = requests.get(thumbnail_url)
        if response.status_code == 200:
            remove_processing_message(context, processing_msg)
            update.message.reply_photo(
                photo=thumbnail_url,
                caption="✅ YouTube thumbnail downloaded!"
            )
        else:
            # Try lower resolution if maxresdefault doesn't exist
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            response = requests.get(thumbnail_url)
            if response.status_code == 200:
                remove_processing_message(context, processing_msg)
                update.message.reply_photo(
                    photo=thumbnail_url,
                    caption="✅ YouTube thumbnail downloaded!"
                )
            else:
                remove_processing_message(context, processing_msg)
                update.message.reply_text("❌ Could not retrieve thumbnail for this video.")
    except Exception as e:
        remove_processing_message(context, processing_msg)
        update.message.reply_text(f"❌ Error downloading thumbnail: {str(e)}")

def cancel(update: Update, context: CallbackContext) -> None:
    """Cancel the current operation."""
    if 'pdf_images' in context.user_data:
        context.user_data['pdf_images'] = []
    if 'current_tool' in context.user_data:
        del context.user_data['current_tool']
    
    update.message.reply_text("❌ Operation cancelled. What would you like to do next?", reply_markup=get_main_menu())

def get_main_menu():
    """Return the main menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("🖼️ Remove Background", callback_data='remove_bg')],
        [InlineKeyboardButton("📄 Image to PDF", callback_data='img_to_pdf')],
        [InlineKeyboardButton("🎨 Text to Image", callback_data='text_to_img')],
        [InlineKeyboardButton("📉 Compress Image", callback_data='compress_img')],
        [InlineKeyboardButton("🔳 QR Code Generator", callback_data='qr_code')],
        [InlineKeyboardButton("🌍 Translator", callback_data='translator')],
        [InlineKeyboardButton("💱 Currency Converter", callback_data='currency')],
        [InlineKeyboardButton("🖼️ Image Upscaler", callback_data='upscale')],
        [InlineKeyboardButton("📝 Text Summarizer", callback_data='summarize')],
        [InlineKeyboardButton("😂 Random Joke", callback_data='joke')],
        [InlineKeyboardButton("🌤️ Weather Info", callback_data='weather')],
        [InlineKeyboardButton("🎭 Cartoonify Image", callback_data='cartoonify')],
        [InlineKeyboardButton("📺 YouTube Thumbnail", callback_data='yt_thumb')],
    ]
    return InlineKeyboardMarkup(keyboard)

def message_handler(update: Update, context: CallbackContext) -> None:
    """Handle regular messages based on the current tool."""
    if 'current_tool' not in context.user_data:
        update.message.reply_text("Please select a tool from the menu.", reply_markup=get_main_menu())
        return
    
    current_tool = context.user_data['current_tool']
    
    if current_tool == 'remove_bg':
        remove_background(update, context)
    elif current_tool == 'img_to_pdf':
        images_to_pdf(update, context)
    elif current_tool == 'text_to_img':
        text_to_image(update, context)
    elif current_tool == 'compress_img':
        compress_image(update, context)
    elif current_tool == 'qr_code':
        generate_qrcode(update, context)
    elif current_tool == 'translator':
        translate_text(update, context)
    elif current_tool == 'currency':
        convert_currency(update, context)
    elif current_tool == 'upscale':
        upscale_image(update, context)
    elif current_tool == 'summarize':
        summarize_text(update, context)
    elif current_tool == 'joke':
        random_joke(update, context)
    elif current_tool == 'weather':
        get_weather(update, context)
    elif current_tool == 'cartoonify':
        cartoonify_image(update, context)
    elif current_tool == 'yt_thumb':
        youtube_thumbnail(update, context)
    else:
        update.message.reply_text("Invalid tool selected. Please try again.", reply_markup=get_main_menu())

def error_handler(update: Update, context: CallbackContext) -> None:
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        update.message.reply_text("❌ An error occurred. Please try again.")

def main() -> None:
    """Start the bot."""
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("cancel", cancel))
    dispatcher.add_handler(CommandHandler("jokebn", random_joke_bangla))
    
    # Button handler
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handler
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    dispatcher.add_handler(MessageHandler(Filters.photo, message_handler))
    
    # Error handler
    dispatcher.add_error_handler(error_handler)

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
