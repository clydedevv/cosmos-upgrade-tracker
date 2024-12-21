# main.py

import asyncio
from telegram_bot import build_application, broadcast_message
from polkachu_upgrades import (
    fetch_upgrades,
    parse_upgrades,
    filter_upgrades,
    check_for_new_or_changed_upgrades,
    hours_until_upgrade,
    last_upgrades
)

POLL_INTERVAL_SECONDS = 3600  # 1 hour

async def poll_loop(application):
    """
    This loop will run forever, polling Polkachu every X seconds
    and sending Telegram alerts to subscribed chats (for each relevant network).
    """
    while True:
        # 1) Fetch & parse
        raw_data = fetch_upgrades()
        parsed = parse_upgrades(raw_data)
        relevant = filter_upgrades(parsed)

        # 2) Detect new/changed
        changed = check_for_new_or_changed_upgrades(relevant)
        if changed:
            for upg in changed:
                network = upg["network"]
                version = upg["node_version"]
                est_time = upg["estimated_upgrade_time"]
                msg = (
                    f"New/Updated upgrade detected!\n"
                    f"Network: {network}\n"
                    f"Version: {version}\n"
                    f"Estimated Time: {est_time}\n"
                )
                # Pass network to broadcast_message so only subscribers of that network get alerts
                await broadcast_message(application, msg, network=network)

        # 3) Time-based alerts
        await check_time_based_alerts(application)

        # 4) Wait, then loop
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

async def check_time_based_alerts(application):
    """
    Example: 2 days, 1 day, 2 hours, or at upgrade time.
    We'll reuse 'hours_until_upgrade' from polkachu_upgrades.
    """
    for net, upg in last_upgrades.items():
        est_time_str = upg.get("estimated_upgrade_time")
        if not est_time_str:
            continue

        h_left = hours_until_upgrade(est_time_str)
        alerts_sent = upg.get("alerts_sent", {})

        # 2 days before
        if h_left <= 48 and not alerts_sent.get("2_days_before", False):
            alerts_sent["2_days_before"] = True
            msg = f"[Alert] Upgrade for {net} ~2 days away ({est_time_str})!"
            await broadcast_message(application, msg, network=net)

        # 1 day before
        if h_left <= 24 and not alerts_sent.get("1_day_before", False):
            alerts_sent["1_day_before"] = True
            msg = f"[Alert] Upgrade for {net} ~1 day away ({est_time_str})!"
            await broadcast_message(application, msg, network=net)

        # 2 hours before
        if h_left <= 2 and not alerts_sent.get("2_hours_before", False):
            alerts_sent["2_hours_before"] = True
            msg = f"[Alert] Upgrade for {net} ~2 hours away ({est_time_str})!"
            await broadcast_message(application, msg, network=net)

        # At or past upgrade time
        if h_left <= 0 and not alerts_sent.get("upgrade_time", False):
            alerts_sent["upgrade_time"] = True
            msg = f"[Alert] Upgrade time has arrived for {net} ({est_time_str})!"
            await broadcast_message(application, msg, network=net)

        upg["alerts_sent"] = alerts_sent

async def main():
    """
    Entry point: build the Telegram application, start polling, etc.
    """
    # 1) Build the Telegram Bot
    application = build_application()

    # 2) Run the application (bot) in parallel with our poll_loop
    polling_task = asyncio.create_task(poll_loop(application))

    # Start the Telegram bot
    await application.initialize()
    await application.start()
    try:
        # Wait for the polling task to finish (which won't happen unless an exception occurs)
        await polling_task
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
