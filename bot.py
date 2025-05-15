import logging
import os
import random
import string
import requests
from io import BytesIO

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# QR Code
import qrcode
from pyzbar.pyzbar import decode as qr_decode

# Image Processing
from PIL import Image

# URL Shortener
from pyshorteners import Shortener

# YouTube Downloader (and others)
import yt_dlp

# Remove Background
from removebg import RemoveBg # pip install removebg

# --- Configuration ---
# WARNING: Hardcoding API keys is a security risk if your code is public.
# Consider using environment variables or GitHub Secrets for production.
TELEGRAM_BOT_TOKEN = "7959962751:AAFg5M7qfFxYgjUTAdg-KIK6k6JFZuMemJI" # YOUR_BOT_TOKEN
REMOVEBG_API_KEY = "qLfRtLd6MebVzGTuFcQ7Yv9j" # YOUR_REMOVEBG_API_KEY

DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
CURRENCY_API_URL_FRANKFURTER = "https://api.frankfurter.app"


# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Global Variables (for simple state, e.g., TicTacToe - will reset on restart) ---
ttt_games = {} # chat_id: {board: [], player_turn: 'X', game_over: False}

# --- Helper Functions ---
def generate_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(length))
    return password

def get_random_fact():
    try:
        response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en")
        response.raise_for_status()
        return response.json()['text']
    except Exception as e:
        logger.error(f"Error fetching fact: {e}")
        return "Sorry, couldn't fetch a fact right now."

def get_random_joke():
    try:
        headers = {'Accept': 'application/json'}
        response = requests.get("https://icanhazdadjoke.com/", headers=headers)
        response.raise_for_status()
        return response.json()['joke']
    except Exception as e:
        logger.error(f"Error fetching joke: {e}")
        return "Sorry, couldn't fetch a joke right now."

# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I am your friendly utility bot."
        "\nUse /help to see what I can do.",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    Available commands:
    /start - Welcome message
    /help - This help message

    🔍 *Search & Info*
    /dict <word> - Get definition of a word.
    /fact - Get a random fact.
    /joke - Get a random joke.

    💰 *Converters*
    /currency <amount> <FROM_CODE> <TO_CODE> - Convert currency (e.g., /currency 10 USD EUR).
    (Unit Converter to be added)

    🛠️ *Utilities*
    /password [length] - Generate a strong password (default length 12).
    /qr <text> - Generate a QR code for the text.
    /shorten <url> - Shorten a long URL.
    /unshorten <short_url> - Get the original URL from a shortened one.
    (Send an image with a QR code to scan it)

    🖼️ *Image Tools*
    /removebg - Reply to an image to remove its background.
    /resize <width> <height> - Reply to an image to resize it.
    /compress <quality> - Reply to an image to compress it (quality 0-100).

    📥 *Downloaders* (May be unreliable)
    /yt <video_url> [audio|video] - Download YouTube content (default video).
    /insta <post_url> - Download Instagram post/reel/story.
    /fb <video_url> - Download Facebook video.
    /tiktok <video_url> - Download TikTok video.

    📦 *Telegram Stickers*
    Send me a sticker, and I'll try to download it for you.
    
    🕹️ *Games*
    /tictactoe - Start a game of Tic Tac Toe. (Very Basic)
    """
    # Removed for now: /unit <value> <from_unit> <to_unit> - Convert units.
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def dictionary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a word. Usage: /dict <word>")
        return
    word = context.args[0]
    try:
        response = requests.get(f"{DICTIONARY_API_URL}{word}")
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and data.get('title') == "No Definitions Found":
             await update.message.reply_text(f"Sorry, no definitions found for '{word}'.")
             return

        meanings = data[0]['meanings']
        reply = f"Definitions for *{word}*:\n\n"
        for meaning in meanings:
            reply += f"*{meaning['partOfSpeech']}*:\n"
            for i, definition in enumerate(meaning['definitions'][:3]): # Max 3 definitions per part of speech
                reply += f"  {i+1}. {definition['definition']}\n"
                if 'example' in definition:
                    reply += f"     _Example: {definition['example']}_\n"
            reply += "\n"
        await update.message.reply_text(reply, parse_mode='Markdown')
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            await update.message.reply_text(f"Sorry, no definitions found for '{word}'.")
        else:
            await update.message.reply_text("Sorry, there was an error fetching the definition.")
            logger.error(f"Dictionary API error for {word}: {e}")
    except Exception as e:
        await update.message.reply_text("Sorry, an error occurred.")
        logger.error(f"Error in dictionary_command for {word}: {e}")

async def currency_converter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /currency <amount> <FROM_CURRENCY_CODE> <TO_CURRENCY_CODE>\nExample: /currency 10 USD EUR")
        return

    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return

    from_currency = context.args[1].upper()
    to_currency = context.args[2].upper()

    if from_currency == to_currency:
        await update.message.reply_text(f"{amount} {from_currency} is {amount} {to_currency}")
        return

    try:
        # Using Frankfurter API (no key needed)
        url = f"{CURRENCY_API_URL_FRANKFURTER}/latest?amount={amount}&from={from_currency}&to={to_currency}"
        response = requests.get(url)
        response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
        data = response.json()

        if 'rates' in data and to_currency in data['rates']:
            converted_amount = data['rates'][to_currency]
            await update.message.reply_text(f"{amount} {from_currency} is approximately {converted_amount:.2f} {to_currency}\n_Rates from {data.get('date', 'latest')}_", parse_mode='Markdown')
        else:
            # Check if currencies are supported by listing them if error
            all_currencies_res = requests.get(f"{CURRENCY_API_URL_FRANKFURTER}/currencies")
            all_currencies_data = all_currencies_res.json()
            supported_codes = ", ".join(all_currencies_data.keys())
            await update.message.reply_text(f"Could not convert from {from_currency} to {to_currency}. "
                                            f"Ensure the currency codes are valid.\n"
                                            f"Supported codes include: {supported_codes[:200]}...") # Show some supported codes
    except requests.exceptions.HTTPError as e:
        error_data = e.response.json()
        error_message = error_data.get('message', 'Unknown error from currency API.')
        logger.error(f"Currency API HTTPError: {e} - {error_message}")
        await update.message.reply_text(f"Error from currency service: {error_message}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Currency API RequestException: {e}")
        await update.message.reply_text("Sorry, there was an error connecting to the currency conversion service.")
    except Exception as e:
        logger.error(f"Error in currency_converter_command: {e}")
        await update.message.reply_text("An unexpected error occurred during currency conversion.")


async def fact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_random_fact())

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_random_joke())

async def password_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    length = 12
    if context.args and context.args[0].isdigit():
        length = int(context.args[0])
        if not (8 <= length <= 64):
            await update.message.reply_text("Password length must be between 8 and 64.")
            return
    password = generate_password(length)
    await update.message.reply_text(f"Generated password: `{password}`", parse_mode='Markdown')

async def qr_generator_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide text to encode. Usage: /qr <text>")
        return
    text = " ".join(context.args)
    img = qrcode.make(text)
    bio = BytesIO()
    bio.name = 'qr_code.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    await update.message.reply_photo(photo=bio)

async def url_shortener_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a URL to shorten. Usage: /shorten <url>")
        return
    url_to_shorten = context.args[0]
    try:
        s = Shortener()
        short_url = s.tinyurl.short(url_to_shorten)
        await update.message.reply_text(f"Shortened URL: {short_url}")
    except Exception as e:
        logger.error(f"Error shortening URL {url_to_shorten}: {e}")
        await update.message.reply_text("Sorry, could not shorten the URL. Make sure it's valid.")

async def url_unshortener_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a short URL to unshorten. Usage: /unshorten <url>")
        return
    short_url = context.args[0]
    try:
        response = requests.head(short_url, allow_redirects=True, timeout=10) # Increased timeout
        original_url = response.url
        await update.message.reply_text(f"Original URL: {original_url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error unshortening URL {short_url}: {e}")
        await update.message.reply_text("Sorry, could not unshorten the URL. It might be invalid, unreachable, or timed out.")

# --- Message Handlers (for images, stickers etc.) ---

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    # QR Code Scanner
    if not message.caption or not (message.caption.lower().startswith(('/resize', '/compress', '/removebg'))):
        file_id = message.photo[-1].file_id
        new_file = await context.bot.get_file(file_id)
        img_bytes = BytesIO(await new_file.download_as_bytearray())
        img_bytes.seek(0)
        
        try:
            img = Image.open(img_bytes)
            decoded_objects = qr_decode(img)
            if decoded_objects:
                qr_data = [obj.data.decode('utf-8') for obj in decoded_objects]
                await message.reply_text("QR Code(s) found:\n" + "\n".join(qr_data))
                return 
        except Exception as e:
            logger.error(f"Error decoding QR from image: {e}")

    # Image Manipulation (if command is in caption)
    if message.caption:
        command_parts = message.caption.split()
        command = command_parts[0].lower()

        if command == "/removebg":
            if not REMOVEBG_API_KEY:
                await message.reply_text("RemoveBG API key is not configured. This feature is unavailable.")
                return
            
            await message.reply_chat_action("upload_photo")
            file_id = message.photo[-1].file_id
            new_file = await context.bot.get_file(file_id)
            img_bytes = BytesIO(await new_file.download_as_bytearray())
            
            temp_input_filename = f"temp_input_{message.message_id}.png"
            temp_output_filename = f"no_bg_{message.message_id}.png"

            try:
                r = RemoveBg(REMOVEBG_API_KEY, f"removebg_error_{message.message_id}.log")
                with open(temp_input_filename, "wb") as temp_f:
                    temp_f.write(img_bytes.getvalue())

                r.remove_background_from_img_file(img_path=temp_input_filename, new_file_name=temp_output_filename)

                with open(temp_output_filename, "rb") as processed_image_file:
                    await message.reply_photo(photo=processed_image_file, caption="Background removed!")
            except Exception as e:
                logger.error(f"Error removing background: {e}")
                await message.reply_text(f"Sorry, couldn't remove background. Error: {str(e)[:200]}") # Send part of error
            finally:
                if os.path.exists(temp_input_filename):
                    os.remove(temp_input_filename)
                if os.path.exists(temp_output_filename):
                    os.remove(temp_output_filename)
                if os.path.exists(f"removebg_error_{message.message_id}.log"):
                     os.remove(f"removebg_error_{message.message_id}.log")
            return


        if command == "/resize" and len(command_parts) == 3 and command_parts[1].isdigit() and command_parts[2].isdigit():
            width = int(command_parts[1])
            height = int(command_parts[2])
            
            if not (10 < width < 4096 and 10 < height < 4096):
                await message.reply_text("Width and height must be between 10 and 4096.")
                return

            await message.reply_chat_action("upload_photo")
            file_id = message.photo[-1].file_id
            new_file = await context.bot.get_file(file_id)
            img_bytes = BytesIO(await new_file.download_as_bytearray())
            
            try:
                img = Image.open(img_bytes)
                img_resized = img.resize((width, height))
                
                bio_resized = BytesIO()
                bio_resized.name = 'resized_image.png' 
                img_format = img.format if img.format else 'PNG'
                img_resized.save(bio_resized, img_format)
                bio_resized.seek(0)
                await message.reply_photo(photo=bio_resized, caption=f"Resized to {width}x{height}")
            except Exception as e:
                logger.error(f"Error resizing image: {e}")
                await message.reply_text("Sorry, could not resize the image.")
            return

        if command == "/compress" and len(command_parts) == 2 and command_parts[1].isdigit():
            quality = int(command_parts[1])
            if not (0 <= quality <= 100):
                await message.reply_text("Quality must be between 0 and 100.")
                return

            await message.reply_chat_action("upload_photo")
            file_id = message.photo[-1].file_id
            new_file = await context.bot.get_file(file_id)
            img_bytes = BytesIO(await new_file.download_as_bytearray())

            try:
                img = Image.open(img_bytes)
                bio_compressed = BytesIO()
                bio_compressed.name = 'compressed_image.jpg' 
                
                if img.mode == 'RGBA' or img.mode == 'P': # Handle palette mode too
                    img = img.convert('RGB')
                    
                img.save(bio_compressed, "JPEG", quality=quality, optimize=True) # Added optimize
                bio_compressed.seek(0)
                await message.reply_photo(photo=bio_compressed, caption=f"Compressed with quality {quality}")
            except Exception as e:
                logger.error(f"Error compressing image: {e}")
                await message.reply_text("Sorry, could not compress the image. Try ensuring it's a common format like PNG or JPG.")
            return


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sticker = update.message.sticker
    await update.message.reply_text(f"Sticker received! File ID: `{sticker.file_id}`", parse_mode='Markdown')
    
    if sticker.is_animated or sticker.is_video:
        ext = ".tgs" if sticker.is_animated else ".webm" 
    else:
        ext = ".webp" 

    try:
        await update.message.reply_chat_action("upload_document")
        sticker_file = await context.bot.get_file(sticker.file_id)
        
        downloaded_sticker_bytes = BytesIO(await sticker_file.download_as_bytearray())
        downloaded_sticker_bytes.name = f"sticker_{sticker.file_unique_id}{ext}"
        downloaded_sticker_bytes.seek(0)

        await update.message.reply_document(document=downloaded_sticker_bytes,
                                            caption=f"Here's the sticker file ({ext})!")
    except Exception as e:
        logger.error(f"Error downloading/sending sticker {sticker.file_id}: {e}")
        await update.message.reply_text("Sorry, I couldn't download that sticker.")


# --- Downloaders ---
async def downloader_command(update: Update, context: ContextTypes.DEFAULT_TYPE, platform: str):
    if not context.args:
        await update.message.reply_text(f"Please provide a URL. Usage: /{platform.lower()} <url> [audio|video]")
        return

    url = context.args[0]
    output_format = 'video' 
    if len(context.args) > 1 and context.args[1].lower() == 'audio':
        output_format = 'audio'

    processing_msg = await update.message.reply_text(f"Trying to download {output_format} from {platform}... this might take a while.")
    await update.message.reply_chat_action("upload_video" if output_format == "video" else "upload_audio")

    # Unique filename per request to avoid conflicts in stateless environment
    request_id = update.update_id 
    base_filename = f"{platform}_{request_id}"
    
    # yt-dlp output template - ensuring unique names
    # %(title).20s might create too long filenames or problematic chars, use id
    output_template = f"{base_filename}_%(id)s.%(ext)s"


    ydl_opts_video = {
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best[height<=1080]/best', # Limit height
        'outtmpl': output_template,
        'noplaylist': True,
        'max_filesize': 48 * 1024 * 1024, # Slightly under 50MB to be safe
        'quiet': True, 
        'no_warnings': True,
        'socket_timeout': 30, # Timeout for network operations
        'retries': 2, # Retry failed downloads
        # 'ffmpeg_location': '/usr/bin/ffmpeg', # Explicitly set if needed on runner
    }
    ydl_opts_audio = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best', # m4a is often better quality and size than mp3
        'outtmpl': output_template,
        'noplaylist': True,
        'max_filesize': 48 * 1024 * 1024,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a', # Defaulting to m4a
            'preferredquality': '128', # 128k for audio is a good balance
        }],
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'retries': 2,
        # 'ffmpeg_location': '/usr/bin/ffmpeg',
    }
    if output_format == 'audio' and context.args[1].lower() == 'mp3': # Allow user to request mp3
        ydl_opts_audio['postprocessors'][0]['preferredcodec'] = 'mp3'
    
    ydl_opts = ydl_opts_video if output_format == 'video' else ydl_opts_audio

    downloaded_filepath = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False) 
            
            # Check filesize from info if available *before* download
            filesize_est = info.get('filesize') or info.get('filesize_approx')
            if filesize_est and filesize_est > 48 * 1024 * 1024:
                await processing_msg.edit_text(f"The file is estimated to be too large ({filesize_est // (1024*1024)}MB) to send via Telegram (max ~48MB). Cannot download.")
                return

            await processing_msg.edit_text(f"Downloading and processing '{info.get('title', url)}'...")
            ydl.download([url])
            
            # Determine the actual downloaded filename
            # yt-dlp might change the extension based on postprocessing
            # We used a base_filename pattern, so we can find it
            for f_name in os.listdir('.'):
                if f_name.startswith(base_filename) and os.path.isfile(f_name):
                    downloaded_filepath = f_name
                    break
            
            if not downloaded_filepath or not os.path.exists(downloaded_filepath):
                logger.error(f"Downloaded file not found for {url} with base {base_filename}.")
                await processing_msg.edit_text("Sorry, couldn't find the downloaded file after processing.")
                return

        file_size_on_disk = os.path.getsize(downloaded_filepath)
        if file_size_on_disk > 50 * 1024 * 1024: # Final check
            await processing_msg.edit_text(f"Downloaded file '{downloaded_filepath}' is too large ({file_size_on_disk//(1024*1024)}MB) to send via Telegram.")
            return # Cleanup will happen in finally

        # Send the file
        with open(downloaded_filepath, 'rb') as f:
            caption_text = info.get('title', os.path.basename(downloaded_filepath))
            if output_format == 'video':
                await update.message.reply_video(video=f, caption=caption_text,
                                                 width=info.get('width'), height=info.get('height'),
                                                 duration=info.get('duration'))
            else: # audio
                await update.message.reply_audio(audio=f, caption=caption_text,
                                                 title=info.get('track') or info.get('title'),
                                                 performer=info.get('artist') or info.get('uploader'),
                                                 duration=info.get('duration'))
        await processing_msg.delete() # Clean up "processing" message

    except yt_dlp.utils.MaxFilesizeError:
        logger.warning(f"MaxFilesizeError for {url} ({platform})")
        await processing_msg.edit_text(f"Sorry, the file from {platform} is too large to download (limit set to ~48MB for Telegram).")
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp DownloadError for {url} ({platform}): {e}")
        # Try to give a more user-friendly message for common errors
        if "Unsupported URL" in str(e):
            error_msg_user = f"The URL for {platform} is not supported or is invalid."
        elif "private" in str(e).lower() or "login required" in str(e).lower():
            error_msg_user = f"This {platform} content might be private or require login."
        else:
            error_msg_user = f"Sorry, couldn't download from {platform}. The platform might be blocking downloads or the URL is problematic."
        await processing_msg.edit_text(error_msg_user + f"\n_{str(e)[:150]}_", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Generic error in {platform} downloader for {url}: {e}")
        await processing_msg.edit_text(f"An unexpected error occurred while trying to download from {platform}.")
    finally:
        if downloaded_filepath and os.path.exists(downloaded_filepath):
            os.remove(downloaded_filepath)
        # Clean up any other potential temp files from yt-dlp if pattern is known (less reliable)
        for f_name in os.listdir('.'):
            if f_name.startswith(base_filename): # Clean any file starting with our unique base name
                try:
                    os.remove(f_name)
                except OSError: # File might have been moved or already deleted
                    pass


async def youtube_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await downloader_command(update, context, "YouTube")

async def instagram_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await downloader_command(update, context, "Instagram")

async def facebook_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await downloader_command(update, context, "Facebook")

async def tiktok_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await downloader_command(update, context, "TikTok")


# --- Tic Tac Toe (Very Basic - state will be lost on GitHub Action restarts) ---
def get_ttt_board_markup(chat_id):
    game = ttt_games.get(chat_id)
    if not game:
        return None
    
    board = game['board']
    keyboard = []
    for i in range(0, 9, 3):
        row = [
            InlineKeyboardButton(board[i] or " ", callback_data=f"ttt_{i}"),
            InlineKeyboardButton(board[i+1] or " ", callback_data=f"ttt_{i+1}"),
            InlineKeyboardButton(board[i+2] or " ", callback_data=f"ttt_{i+2}")
        ]
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def check_ttt_winner(board):
    lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Horizontal
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Vertical
        [0, 4, 8], [2, 4, 6]             # Diagonal
    ]
    for line in lines:
        if board[line[0]] and board[line[0]] == board[line[1]] == board[line[2]]:
            return board[line[0]]
    if all(cell for cell in board):
        return "Draw"
    return None

async def tictactoe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in ttt_games and not ttt_games[chat_id]['game_over']:
        await update.message.reply_text("A game is already in progress!", reply_markup=get_ttt_board_markup(chat_id))
        return

    ttt_games[chat_id] = {'board': [None] * 9, 'player_turn': 'X', 'game_over': False, 'message_id': None}
    markup = get_ttt_board_markup(chat_id)
    msg = await update.message.reply_text("Tic Tac Toe! Player X's turn.", reply_markup=markup)
    ttt_games[chat_id]['message_id'] = msg.message_id

async def tictactoe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Acknowledge callback
    chat_id = query.message.chat_id

    if chat_id not in ttt_games or ttt_games[chat_id]['game_over']:
        try:
            await query.edit_message_text(text="Game is over or not started. Use /tictactoe to start a new game.")
        except Exception: # Message might have been deleted or too old
            pass
        return

    game = ttt_games[chat_id]
    try:
        cell_index = int(query.data.split('_')[1])
    except (ValueError, IndexError):
        logger.error(f"Invalid callback data for TTT: {query.data}")
        return

    if game['board'][cell_index] is not None:
        await context.bot.answer_callback_query(query.id, text="Cell already taken!", show_alert=True)
        return

    game['board'][cell_index] = game['player_turn']
    winner = check_ttt_winner(game['board'])

    if winner:
        game['game_over'] = True
        text = f"Game Over! Winner is {winner}." if winner != "Draw" else "Game Over! It's a Draw."
        try:
            await query.edit_message_text(text=text, reply_markup=None) # Remove board on game over
        except Exception:
            pass
        if chat_id in ttt_games: # Clean up game state
            del ttt_games[chat_id] 
    else:
        game['player_turn'] = 'O' if game['player_turn'] == 'X' else 'X'
        text = f"Player {game['player_turn']}'s turn."
        markup = get_ttt_board_markup(chat_id)
        try:
            await query.edit_message_text(text=text, reply_markup=markup)
        except Exception: # Message might be too old to edit
            pass


# --- Error Handler ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    # More detailed error logging
    if context.error:
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = "".join(tb_list)
        logger.error(f"Traceback:\n{tb_string}")

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("Sorry, an internal error occurred.")
        except Exception as e:
            logger.error(f"Error sending error message to user: {e}")


def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN is not set!")
        return
    if not REMOVEBG_API_KEY:
        logger.warning("REMOVEBG_API_KEY is not set! /removebg feature will not work.")


    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("dict", dictionary_command))
    application.add_handler(CommandHandler("currency", currency_converter_command))
    application.add_handler(CommandHandler("fact", fact_command))
    application.add_handler(CommandHandler("joke", joke_command))
    application.add_handler(CommandHandler("password", password_command))
    application.add_handler(CommandHandler("qr", qr_generator_command))
    application.add_handler(CommandHandler("shorten", url_shortener_command))
    application.add_handler(CommandHandler("unshorten", url_unshortener_command))
    
    application.add_handler(CommandHandler("yt", youtube_command))
    application.add_handler(CommandHandler("insta", instagram_command))
    application.add_handler(CommandHandler("fb", facebook_command))
    application.add_handler(CommandHandler("tiktok", tiktok_command))

    application.add_handler(CommandHandler("tictactoe", tictactoe_command))
    application.add_handler(CallbackQueryHandler(tictactoe_callback, pattern="^ttt_"))

    # Message handlers
    # Handle photos with commands in caption for image tools, otherwise try QR scan
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))

    # Error handler
    import traceback # for more detailed error logging
    application.add_error_handler(error_handler)

    # Start the Bot
    logger.info("Starting bot polling...")
    application.run_polling()

if __name__ == '__main__':
    main()