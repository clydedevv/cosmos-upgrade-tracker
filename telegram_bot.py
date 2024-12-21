# telegram_bot.py

import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    Application,
)

# Dictionary: chat_id -> set of networks
chat_subscriptions = {}  # e.g., { 12345678: {"orai", "cosmos"} }

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start - basic welcome message
    """
    await update.message.reply_text(
        "Welcome to the Cosmos Upgrade Tracker Bot!\n\n"
        "Use /subscribe <network> to receive alerts for specific networks (e.g. /subscribe orai cosmos).\n"
        "Use /unsubscribe <network> to remove a subscription.\n"
        "Use /list to see which networks you've subscribed to."
    )

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /subscribe <network1> <network2> ...
    Example: /subscribe orai cosmos
    """
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Usage: /subscribe <network1> <network2> ...")
        return

    if chat_id not in chat_subscriptions:
        chat_subscriptions[chat_id] = set()

    added_networks = []
    for net in context.args:
        net_lower = net.strip().lower()
        if net_lower not in chat_subscriptions[chat_id]:
            chat_subscriptions[chat_id].add(net_lower)
            added_networks.append(net_lower)

    if added_networks:
        await update.message.reply_text(f"Subscribed to: {', '.join(added_networks)}")
    else:
        await update.message.reply_text("You were already subscribed to all of those networks.")

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /unsubscribe <network1> <network2> ...
    Example: /unsubscribe orai cosmos
    """
    chat_id = update.effective_chat.id
    if chat_id not in chat_subscriptions:
        chat_subscriptions[chat_id] = set()

    if not context.args:
        await update.message.reply_text("Usage: /unsubscribe <network1> <network2> ...")
        return

    removed_networks = []
    for net in context.args:
        net_lower = net.strip().lower()
        if net_lower in chat_subscriptions[chat_id]:
            chat_subscriptions[chat_id].remove(net_lower)
            removed_networks.append(net_lower)

    if removed_networks:
        await update.message.reply_text(f"Unsubscribed from: {', '.join(removed_networks)}")
    else:
        await update.message.reply_text("You were not subscribed to any of those networks.")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /list - show which networks you're subscribed to
    """
    chat_id = update.effective_chat.id
    subs = chat_subscriptions.get(chat_id, set())
    if subs:
        subs_str = ", ".join(subs)
        await update.message.reply_text(f"You are subscribed to: {subs_str}")
    else:
        await update.message.reply_text("You are not subscribed to any networks.")

def build_application() -> Application:
    """
    Creates and configures the telegram bot application.
    """
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

    app = ApplicationBuilder().token(telegram_token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    app.add_handler(CommandHandler("list", list_command))

    return app

async def broadcast_message(application: Application, message: str, network: str = None):
    """
    Sends `message` to all chats that have subscribed to `network`.
    If `network` is None, you can send to everyone (optional behavior).
    """
    # If you really only want to broadcast to all, you can skip 'network'
    # But let's assume we want to respect subscriptions:
    from telegram_bot import chat_subscriptions

    if network:
        network = network.lower()

    for chat_id, networks in chat_subscriptions.items():
        # If no network was specified, or this chat subscribed to `network`, send
        if network is None or network in networks:
            try:
                await application.bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                print(f"Failed to send message to {chat_id}: {e}")
