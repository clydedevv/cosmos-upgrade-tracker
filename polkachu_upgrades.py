import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

POLKACHU_API = "https://polkachu.com/api/v2/chain_upgrades"

# Store upgrade info and alert flags here
last_upgrades = {}

# Cache of valid networks from Polkachu
valid_networks = set()

def fetch_upgrades():
    """
    Fetch upcoming chain upgrades from Polkachu.
    Returns a list (JSON array) of upgrades.
    """
    try:
        logger.info("Fetching upgrades from Polkachu API")
        response = requests.get(POLKACHU_API, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Update valid networks cache
        global valid_networks
        valid_networks = {upgrade.get("network").lower() for upgrade in data if upgrade.get("network")}

        logger.info(f"Found {len(data)} total upgrades")
        return data
    except Exception as e:
        logger.error(f"Failed to fetch Polkachu upgrades: {e}")
        return []

def is_valid_network(network):
    """Check if a network name is valid"""
    return network.lower() in valid_networks

def parse_upgrades(data):
    """
    Parse relevant fields from the Polkachu JSON data.
    Returns a list of dicts with only the fields we care about.
    """
    upgrades = []
    for upgrade in data:
        logger.debug(f"Parsing upgrade for network: {upgrade.get('network')}")
        upgrades.append({
            "network": upgrade.get("network"),
            "chain_name": upgrade.get("chain_name"),
            "node_version": upgrade.get("node_version"),
            "block": upgrade.get("block"),
            "estimated_upgrade_time": upgrade.get("estimated_upgrade_time"),
        })
    return upgrades

def filter_upgrades(upgrades):
    """Return all valid upgrades."""
    return upgrades

def check_for_new_or_changed_upgrades(relevant_upgrades):
    """
    Compare relevant_upgrades with last_upgrades (cache).
    Returns a list of upgrades that are newly added or changed.
    """
    new_or_changed = []
    for upg in relevant_upgrades:
        net = upg["network"]
        version = upg["node_version"]
        block = upg["block"]

        if net not in last_upgrades:
            logger.info(f"New upgrade found for {net}")
            upg["alerts_sent"] = {
                "2_days_before": False,
                "1_day_before": False,
                "2_hours_before": False,
                "upgrade_time": False
            }
            last_upgrades[net] = upg
            new_or_changed.append(upg)
        else:
            old_upg = last_upgrades[net]
            if (old_upg["node_version"] != version) or (old_upg["block"] != block):
                logger.info(f"Changed upgrade detected for {net}")
                alerts_sent = old_upg.get("alerts_sent", {
                    "2_days_before": False,
                    "1_day_before": False,
                    "2_hours_before": False,
                    "upgrade_time": False
                })
                upg["alerts_sent"] = alerts_sent
                last_upgrades[net] = upg
                new_or_changed.append(upg)

    return new_or_changed

def parse_iso_time(iso_string):
    """Parse ISO 8601 time string into datetime object."""
    try:
        iso_string = iso_string.replace('Z', '')
        dt = datetime.fromisoformat(iso_string)
        return dt
    except ValueError as e:
        logger.error(f"Error parsing time {iso_string}: {e}")
        return None

def hours_until_upgrade(iso_string):
    """Return hours until upgrade time."""
    upgrade_dt = parse_iso_time(iso_string)
    if not upgrade_dt:
        return -1
    now = datetime.utcnow()
    delta = upgrade_dt - now
    return delta.total_seconds() / 3600.0
