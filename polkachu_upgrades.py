import requests
from datetime import datetime

POLKACHU_API = "https://polkachu.com/api/v2/chain_upgrades"

# Let’s include 'orai' for testing
SG1_RELEVANT_NETWORKS = {
    "akash",
    "atomone",
    "cosmos",
    "evmos",
    "juno",
    "kava",
    "lum",
    "neutron",
    "noble",
    "osmosis",
    "passage",
    "saga",
    "stride",
    "orai",  # for testing
}

# We'll store upgrade info and alert flags here
last_upgrades = {}

def fetch_upgrades():
    """
    Fetch upcoming chain upgrades from Polkachu.
    Returns a list (JSON array) of upgrades.
    """
    try:
        response = requests.get(POLKACHU_API, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"[Error] Failed to fetch Polkachu upgrades: {e}")
        return []

def parse_upgrades(data):
    """
    Parse relevant fields from the Polkachu JSON data.
    Returns a list of dicts with only the fields we care about.
    """
    upgrades = []
    for upgrade in data:
        upgrades.append({
            "network": upgrade.get("network"),
            "chain_name": upgrade.get("chain_name"),
            "node_version": upgrade.get("node_version"),
            "block": upgrade.get("block"),
            "estimated_upgrade_time": upgrade.get("estimated_upgrade_time"),
        })
    return upgrades

def filter_upgrades(upgrades):
    """
    Return only the upgrades for the networks we care about (SG-1 + 'orai').
    """
    return [
        u for u in upgrades
        if u["network"] in SG1_RELEVANT_NETWORKS
    ]

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
            # brand new
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
            # If version or block changed, consider it changed
            if (old_upg["node_version"] != version) or (old_upg["block"] != block):
                # preserve existing alerts_sent so we don’t lose the flags
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
    """
    Helper to parse the ISO 8601 string (e.g. '2024-12-26T18:27:39.000000Z') into a datetime object.
    """
    # e.g. '2024-12-26T18:27:39.000000Z'
    try:
        # We can ignore the 'Z' if needed by trimming it
        iso_string = iso_string.replace('Z', '')
        dt = datetime.fromisoformat(iso_string)
        return dt
    except ValueError:
        return None

def hours_until_upgrade(iso_string):
    """
    Return how many hours from now until the upgrade time, as a float.
    If the time is in the past or invalid, return a negative or 0.
    """
    upgrade_dt = parse_iso_time(iso_string)
    if not upgrade_dt:
        return -1  # invalid
    now = datetime.utcnow()
    delta = upgrade_dt - now
    return delta.total_seconds() / 3600.0

