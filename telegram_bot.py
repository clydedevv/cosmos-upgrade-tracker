import os
import json
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    Application,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dictionary: chat_id -> set of networks
chat_subscriptions = {}  # e.g., { 12345678: {"orai", "cosmos"} }
SUBSCRIPTIONS_FILE = "subscriptions.json"

def get_chat_subscriptions(chat_id: int) -> set:
    """Get subscriptions for a specific chat"""
    global chat_subscriptions
    # Ensure we have latest data
    load_subscriptions()
    return chat_subscriptions.get(chat_id, set())

def load_subscriptions():
    """Load subscriptions from file"""
    global chat_subscriptions
    try:
        logger.info("===== LOADING SUBSCRIPTIONS =====")
        if os.path.exists(SUBSCRIPTIONS_FILE):
            with open(SUBSCRIPTIONS_FILE, 'r') as f:
                data = json.load(f)
                logger.info(f"Raw data from file: {data}")
                chat_subscriptions = {
                    int(k): set(v) for k, v in data.items()
                }
            logger.info(f"Converted subscriptions: {chat_subscriptions}")
        else:
            logger.warning("No subscriptions file found!")
    except Exception as e:
        logger.error(f"Error loading subscriptions: {e}", exc_info=True)

def save_subscriptions():
    """Save subscriptions to file"""
    try:
        # Convert sets to lists for JSON serialization
        data = {
            str(k): list(v) for k, v in chat_subscriptions.items()
        }
        with open(SUBSCRIPTIONS_FILE, 'w') as f:
            json.dump(data, f)
        logger.info("Saved subscriptions to file")
        logger.debug(f"Saved data: {data}")
    except Exception as e:
        logger.error(f"Error saving subscriptions: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message and help text"""
    await update.message.reply_text(
        "Welcome to the Cosmos Upgrade Tracker Bot!\n\n"
        "Use /subscribe <network> to receive alerts for specific networks (e.g. /subscribe cosmos osmosis).\n"
        "Use /unsubscribe <network> to remove a subscription.\n"
        "Use /list to see which networks you've subscribed to.\n"
        "Use /listupgrades to see upcoming upgrades for your subscribed networks."
    )

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe to updates for specific networks"""
    chat_id = update.effective_chat.id
    logger.info(f"Subscribe command from chat_id: {chat_id}")

    if not context.args:
        await update.message.reply_text("Usage: /subscribe <network1> <network2> ...")
        return

    if chat_id not in chat_subscriptions:
        chat_subscriptions[chat_id] = set()

    added_networks = []
    # Join all args and split by commas or spaces
    networks = ' '.join(context.args).replace(',', ' ').split()

    for net in networks:
        net_lower = net.strip().lower()
        if net_lower and net_lower not in chat_subscriptions[chat_id]:  # Check if not empty
            chat_subscriptions[chat_id].add(net_lower)
            added_networks.append(net_lower)

    if added_networks:
        save_subscriptions()  # Save after successful subscription
        await update.message.reply_text(f"Successfully subscribed to: {', '.join(added_networks)}")
    else:
        await update.message.reply_text("You were already subscribed to all of those networks.")

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unsubscribe from updates for specific networks"""
    chat_id = update.effective_chat.id
    logger.info(f"Unsubscribe command from chat_id: {chat_id}")

    if chat_id not in chat_subscriptions:
        chat_subscriptions[chat_id] = set()

    if not context.args:
        await update.message.reply_text("Usage: /unsubscribe <network1> <network2> ...")
        return

    removed_networks = []
    networks = ' '.join(context.args).replace(',', ' ').split()

    for net in networks:
        net_lower = net.strip().lower()
        if net_lower in chat_subscriptions[chat_id]:
            chat_subscriptions[chat_id].remove(net_lower)
            removed_networks.append(net_lower)

    if removed_networks:
        save_subscriptions()  # Save after successful unsubscription
        await update.message.reply_text(f"Successfully unsubscribed from: {', '.join(removed_networks)}")
    else:
        await update.message.reply_text("You weren't subscribed to any of those networks.")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current subscriptions"""
    chat_id = update.effective_chat.id
    logger.info("================ LIST COMMAND DEBUG ================")
    logger.info(f"List command from chat_id: {chat_id}")
    logger.info(f"chat_subscriptions object id: {id(chat_subscriptions)}")
    logger.info(f"Full chat_subscriptions dict: {chat_subscriptions}")
    logger.info(f"Type of chat_id: {type(chat_id)}")
    logger.info(f"Keys in chat_subscriptions: {chat_subscriptions.keys()}")
    logger.info(f"chat_id exists in dict: {chat_id in chat_subscriptions}")

    subs = chat_subscriptions.get(chat_id, set())
    if subs:
        subs_str = ", ".join(sorted(subs))
        await update.message.reply_text(f"You are subscribed to: {subs_str}")
    else:
        await update.message.reply_text("You are not subscribed to any networks.")

def build_application() -> Application:
    """Build and configure the bot application"""
    global chat_subscriptions
    # Load existing subscriptions
    load_subscriptions()
    logger.info(f"Loaded subscriptions at startup: {chat_subscriptions}")

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

    logger.debug(f"Building application with token length: {len(token)}")

    application = ApplicationBuilder().token(token).build()

    # Verify subscriptions loaded
    logger.info(f"Verifying subscriptions after build: {chat_subscriptions}")

    return application
async def broadcast_message(application: Application, message: str, network: str = None):
    """Send message to subscribed chats"""
    if network:
        network = network.lower()

    logger.info(f"Broadcasting message for network: {network}")
    logger.info(f"Message content: {message}")
    logger.info(f"Current subscriptions: {chat_subscriptions}")

    sent_count = 0
    for chat_id, networks in chat_subscriptions.items():
        if network is None or network in networks:
            try:
                await application.bot.send_message(chat_id=chat_id, text=message)
                logger.info(f"Successfully sent message to chat_id: {chat_id}")
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send message to {chat_id}: {e}", exc_info=True)

    logger.info(f"Broadcast complete. Sent to {sent_count} chats")
