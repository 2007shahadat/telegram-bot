import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Replace with your actual bot token
TOKEN = "8089194654:AAHumYeaeqsfQsGvWmLE6HvBlCi8iNEtn4c"

# User states storage (in a real app, use a database)
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_states[user.id] = {"interaction_count": 1, "last_command": "/start"}
    
    # Create inline keyboard
    keyboard = [
        [InlineKeyboardButton("📊 Info", callback_data="show_info")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! 👋\nI'm your information bot. Use buttons below to interact.",
        reply_markup=reply_markup
    )

async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display information about the user."""
    user = update.effective_user
    chat = update.effective_chat
    
    # Update user state
    if user.id not in user_states:
        user_states[user.id] = {"interaction_count": 0, "last_command": "info"}
    user_states[user.id]["interaction_count"] += 1
    user_states[user.id]["last_command"] = "info"
    
    # Basic user info
    info_text = (
        "📋 <b>User Information</b>\n\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>First Name:</b> {user.first_name}\n"
    )
    
    # Optional fields
    if user.last_name:
        info_text += f"👥 <b>Last Name:</b> {user.last_name}\n"
    if user.username:
        info_text += f"🔖 <b>Username:</b> @{user.username}\n"
    if user.language_code:
        info_text += f"🌐 <b>Language:</b> {user.language_code}\n"
    
    # Chat info (if different from user)
    if chat and chat.id != user.id:
        info_text += "\n💬 <b>Chat Information</b>\n\n"
        info_text += f"🆔 <b>Chat ID:</b> <code>{chat.id}</code>\n"
        info_text += f"🏷 <b>Type:</b> {chat.type}\n"
        if chat.title:
            info_text += f"📛 <b>Title:</b> {chat.title}\n"
    
    # Add interaction stats
    stats = user_states.get(user.id, {"interaction_count": 1})
    info_text += (
        f"\n📊 <b>Interaction Stats</b>\n"
        f"🔄 <b>Interactions:</b> {stats['interaction_count']}\n"
        f"⏱ <b>Last Command:</b> {stats.get('last_command', 'None')}\n"
    )
    
    # Add bot info
    bot_user = await context.bot.get_me()
    info_text += (
        f"\n🤖 <b>Bot:</b> {bot_user.full_name} (@{bot_user.username})\n"
        f"🆔 <b>Bot ID:</b> <code>{bot_user.id}</code>"
    )
    
    # Add inline buttons
    keyboard = [
        [InlineKeyboardButton("📊 Info", callback_data="show_info")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_html(info_text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user = update.effective_user
    user_states[user.id] = {
        "interaction_count": user_states.get(user.id, {}).get("interaction_count", 0) + 1, 
        "last_command": "/help"
    }
    
    help_text = (
        "ℹ️ <b>User Info Bot Help</b>\n\n"
        "This bot shows information about Telegram users.\n\n"
        "<b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/info - Show your information\n"
        "/stats - Show interaction statistics\n"
        "/help - Show this help message\n\n"
        "<b>Features:</b>\n"
        "- View your Telegram profile info\n"
        "- Track your interactions with the bot\n"
        "- Refresh your information anytime"
    )
    
    # Add inline buttons
    keyboard = [
        [InlineKeyboardButton("📊 Info", callback_data="show_info")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(help_text, reply_markup=reply_markup)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user interaction statistics."""
    user = update.effective_user
    stats = user_states.get(user.id, {"interaction_count": 1})
    user_states[user.id] = {
        "interaction_count": stats["interaction_count"] + 1, 
        "last_command": "/stats"
    }
    
    stats_text = (
        "📈 <b>Your Interaction Statistics</b>\n\n"
        f"🔄 <b>Total Interactions:</b> {stats['interaction_count']}\n"
        f"⏱ <b>Last Command:</b> {stats.get('last_command', 'None')}\n\n"
        "Keep interacting to increase your count!"
    )
    
    # Add inline buttons
    keyboard = [
        [InlineKeyboardButton("📊 Info", callback_data="show_info")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(stats_text, reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks."""
    query = update.callback_query
    user = query.from_user
    
    # Initialize user state if not exists
    if user.id not in user_states:
        user_states[user.id] = {"interaction_count": 0, "last_command": "button_click"}
    user_states[user.id]["interaction_count"] += 1
    
    if query.data == "show_info":
        user_states[user.id]["last_command"] = "info_button"
        await show_info(update, context)
    elif query.data == "refresh_info":
        user_states[user.id]["last_command"] = "refresh_button"
        await query.answer("♻️ Information refreshed!")
        await show_info(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all other messages."""
    user = update.effective_user
    
    # Initialize user state if not exists
    if user.id not in user_states:
        user_states[user.id] = {"interaction_count": 0, "last_command": "message"}
    user_states[user.id]["interaction_count"] += 1
    user_states[user.id]["last_command"] = "regular_message"
    
    await show_info(update, context)

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", show_info))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("help", help_command))

    # Button click handler
    application.add_handler(CallbackQueryHandler(button_click))

    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()