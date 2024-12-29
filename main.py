import logging
import asyncio
from telegram.ext import CommandHandler
from telegram_bot import build_application, chat_subscriptions
from polkachu_upgrades import (
    fetch_upgrades,
    parse_upgrades,
    filter_upgrades,
    check_for_new_or_changed_upgrades,
    hours_until_upgrade,
    last_upgrades
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 300  # 5 minutes

async def test_alert(update, context):
    """Test command to verify alerting functionality"""
    chat_id = update.effective_chat.id
    logger.info(f"Test alert requested by chat_id: {chat_id}")

    test_msg = (
        "🔔 Test Alert!\n"
        "This is a test upgrade notification.\n"
        "Network: test-chain\n"
        "Version: v1.0.0-test\n"
        "Estimated Time: in 2 days\n"
        "\nCurrent subscriptions for this chat:"
    )

    subs = chat_subscriptions.get(chat_id, set())
    if subs:
        test_msg += "\n" + ", ".join(sorted(subs))
    else:
        test_msg += "\nNo subscriptions yet"

    await update.message.reply_text(test_msg)

async def list_upgrades(update, context):
    """Show upcoming upgrades for subscribed networks"""
    chat_id = update.effective_chat.id
    logger.info(f"List upgrades requested by chat_id: {chat_id}")

    # Get this chat's subscriptions
    subs = chat_subscriptions.get(chat_id, set())
    logger.info(f"Chat subscriptions: {subs}")

    if not subs:
        await update.message.reply_text("You haven't subscribed to any networks yet. Use /subscribe to add networks.")
        return

    # Fetch current upgrades
    raw_data = fetch_upgrades()
    logger.info(f"Raw upgrades data: {raw_data}")

    parsed = parse_upgrades(raw_data)
    logger.info(f"Parsed upgrades: {parsed}")

    relevant = filter_upgrades(parsed)
    logger.info(f"Relevant upgrades: {relevant}")

    # Filter for subscribed networks
    subscribed_upgrades = [upg for upg in relevant if upg["network"] in subs]
    logger.info(f"Subscribed upgrades: {subscribed_upgrades}")

    if not subscribed_upgrades:
        await update.message.reply_text("No upcoming upgrades found for your subscribed networks.")
        return

    # Build response message
    msg = "📊 Upcoming Upgrades\n\n"
    for upg in subscribed_upgrades:
        network = upg["network"]
        version = upg["node_version"]
        est_time = upg["estimated_upgrade_time"]
        h_left = hours_until_upgrade(est_time)

        if h_left > 0:
            days_left = round(h_left / 24, 1)
            time_str = f"~{days_left} days" if days_left >= 1 else f"~{round(h_left, 1)} hours"
        else:
            time_str = "upgrade time has passed"

        msg += (
            f"🔸 {network.upper()}\n"
            f"   Version: {version}\n"
            f"   Time: {est_time}\n"
            f"   Status: {time_str}\n\n"
        )

    await update.message.reply_text(msg)

async def check_upgrades(application):
    """Background task to check for upgrades"""
    while True:
        try:
            raw_data = fetch_upgrades()
            parsed = parse_upgrades(raw_data)
            relevant = filter_upgrades(parsed)

            changed = check_for_new_or_changed_upgrades(relevant)
            if changed:
                for upg in changed:
                    network = upg["network"]
                    version = upg["node_version"]
                    est_time = upg["estimated_upgrade_time"]
                    msg = (
                        f"🔔 New/Updated upgrade detected!\n"
                        f"Network: {network}\n"
                        f"Version: {version}\n"
                        f"Estimated Time: {est_time}\n"
                    )
                    # TODO: implement broadcast

            # Time-based alerts
            for net, upg in last_upgrades.items():
                est_time_str = upg.get("estimated_upgrade_time")
                if not est_time_str:
                    continue

                h_left = hours_until_upgrade(est_time_str)
                alerts_sent = upg.get("alerts_sent", {})

                if h_left <= 24 and not alerts_sent.get("1_day_before", False):
                    alerts_sent["1_day_before"] = True
                    msg = f"⚠️ [Alert] Upgrade for {net} is tomorrow! (~24 hours)\n" \
                         f"Time: {est_time_str}\n" \
                         f"Version: {upg['node_version']}"
                    await broadcast_message(application, msg, network=net)

                if h_left <= 2 and not alerts_sent.get("2_hours_before", False):
                    alerts_sent["2_hours_before"] = True
                    msg = f"🚨 [Alert] Upgrade for {net} in ~2 hours!\n" \
                         f"Time: {est_time_str}\n" \
                         f"Version: {upg['node_version']}"
                    await broadcast_message(application, msg, network=net)

                if h_left <= 0 and not alerts_sent.get("upgrade_time", False):
                    alerts_sent["upgrade_time"] = True
                    msg = f"🚨 [Alert] Upgrade time has arrived for {net}!\n" \
                         f"Time: {est_time_str}\n" \
                         f"Version: {upg['node_version']}"
                    await broadcast_message(application, msg, network=net)

                upg["alerts_sent"] = alerts_sent

        except Exception as e:
            logger.error(f"Error in check_upgrades: {e}", exc_info=True)

        await asyncio.sleep(POLL_INTERVAL_SECONDS)

def main():
    """Start the bot"""
    print("Bot has started!")

    # Initialize application
    application = build_application()

    # Add command handlers
    application.add_handler(CommandHandler("test", test_alert))
    application.add_handler(CommandHandler("listupgrades", list_upgrades))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
