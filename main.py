
import logging
import asyncio
from telegram.ext import CommandHandler
from telegram_bot import (
    build_application,
    broadcast_message,
    subscribe_command,
    unsubscribe_command,
    list_command,
    start_command,
    load_subscriptions,
    chat_subscriptions,
)

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

POLL_INTERVAL_SECONDS = 900  # 15 minutes, Polkachu if this is to much tell me and I'll make it less

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
    from telegram_bot import get_chat_subscriptions  # Add this import

    chat_id = update.effective_chat.id
    logger.info("================ LIST UPGRADES DEBUG ================")
    logger.info(f"List upgrades requested by chat_id: {chat_id}")

    # Get subscriptions using the new function
    subs = get_chat_subscriptions(chat_id)
    logger.info(f"Subscriptions found for chat_id {chat_id}: {subs}")

    if not subs:
        logger.warning(f"No subscriptions found for chat_id {chat_id}")
        await update.message.reply_text("You haven't subscribed to any networks yet. Use /subscribe to add networks.")
        return

    # Fetch current upgrades
    logger.info("Fetching upgrades from Polkachu")
    raw_data = fetch_upgrades()
    parsed = parse_upgrades(raw_data)

    # Filter for subscribed networks
    subscribed_upgrades = [upg for upg in parsed if upg["network"].lower() in subs]
    logger.info(f"Found {len(subscribed_upgrades)} upgrades for subscribed networks")

    if not subscribed_upgrades:
        await update.message.reply_text("No upcoming upgrades found for your subscribed networks.")
        return

    # Build response message...
    msg = "📊 Upcoming Upgrades\n\n"
    for upg in subscribed_upgrades:
        network = upg["network"]
        version = upg["node_version"]
        est_time = upg["estimated_upgrade_time"]
        h_left = hours_until_upgrade(est_time)

        if h_left > 24:
            days_left = round(h_left / 24, 1)
            time_str = f"~{days_left} days"
        elif h_left > 0:
            time_str = f"~{round(h_left, 1)} hours"
        elif h_left > -24:
            hours_past = abs(round(h_left, 1))
            time_str = f"started {hours_past} hours ago"
        else:
            continue  # Skip old upgrades

        msg += (
            f"🔸 {network.upper()}\n"
            f"   Version: {version}\n"
            f"   Time: {est_time}\n"
            f"   Status: {time_str}\n\n"
        )

    await update.message.reply_text(msg)

async def check_upgrades(context):
    """Background task to check for upgrades"""
    application = context.application
    try:
        logger.info("Checking for upgrades...")
        raw_data = fetch_upgrades()
        parsed = parse_upgrades(raw_data)
        relevant = filter_upgrades(parsed)

        # Log current state
        logger.info(f"Found {len(relevant)} relevant upgrades")
        for upg in relevant:
            logger.info(f"Processing upgrade: {upg['network']} -> {upg['node_version']} at {upg['estimated_upgrade_time']}")

            network = upg["network"]
            version = upg["node_version"]
            est_time = upg["estimated_upgrade_time"]

            # Get or initialize alert flags
            if network not in last_upgrades:
                last_upgrades[network] = upg.copy()
                last_upgrades[network]["alerts_sent"] = {
                    "24_hours": False,
                    "2_hours": False,
                    "upgrade_time": False
                }

            alerts_sent = last_upgrades[network].get("alerts_sent", {})
            h_left = hours_until_upgrade(est_time)
            logger.info(f"{network}: {h_left:.1f} hours until upgrade. Alerts sent: {alerts_sent}")

            try:
                # 24 hour alert
                if 23 <= h_left <= 24 and not alerts_sent.get("24_hours", False):
                    logger.info(f"Sending 24-hour alert for {network}")
                    alerts_sent["24_hours"] = True
                    msg = (
                        f"⚠️ [24 HOUR ALERT] Chain upgrade approaching!\n"
                        f"Network: {network}\n"
                        f"Version: {version}\n"
                        f"Time: {est_time}\n"
                        f"Status: Upgrade in approximately 24 hours"
                    )
                    await broadcast_message(application, msg, network=network)

                # 2 hour alert
                if 1.9 <= h_left <= 2.1 and not alerts_sent.get("2_hours", False):
                    logger.info(f"Sending 2-hour alert for {network}")
                    alerts_sent["2_hours"] = True
                    msg = (
                        f"🚨 [2 HOUR ALERT] Chain upgrade imminent!\n"
                        f"Network: {network}\n"
                        f"Version: {version}\n"
                        f"Time: {est_time}\n"
                        f"Status: Upgrade in approximately 2 hours"
                    )
                    await broadcast_message(application, msg, network=network)

                # Upgrade time alert
                if -0.1 <= h_left <= 0.1 and not alerts_sent.get("upgrade_time", False):
                    logger.info(f"Sending upgrade-time alert for {network}")
                    alerts_sent["upgrade_time"] = True
                    msg = (
                        f"🚨 [UPGRADE TIME] Chain upgrade now!\n"
                        f"Network: {network}\n"
                        f"Version: {version}\n"
                        f"Time: {est_time}\n"
                        f"Status: Upgrade time has arrived"
                    )
                    await broadcast_message(application, msg, network=network)

                # Update alert flags
                last_upgrades[network]["alerts_sent"] = alerts_sent

            except Exception as e:
                logger.error(f"Error sending alerts for {network}: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Error in check_upgrades: {e}", exc_info=True)

        logger.debug("Sleeping before next check...")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

def main():
    """Start the bot"""
    print("Bot has started!")

    # Initialize application
    application = build_application()

    # Register all command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("test", test_alert))
    application.add_handler(CommandHandler("listupgrades", list_upgrades))

    # Start upgrade checking in the background
    application.job_queue.run_repeating(check_upgrades, interval=POLL_INTERVAL_SECONDS)

    # Run the bot (this will block until stopped)
    application.run_polling()

if __name__ == "__main__":
    main()
