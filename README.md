
# Cosmos Upgrade Alert Bot (@CosmosUpgradeBot)

A Telegram bot that sends alerts for upcoming Cosmos chain upgrades. Get notifications when your favorite Cosmos chains have upgrades approaching.

## Features

- Track upgrades for major Cosmos chains
- Get alerts 2 hours before upgrades and at upgrade time
- Filter alerts by subscribing only to networks you care about
- Check upcoming upgrades anytime with a simple command
- Works in both group chats and private messages
- Persistent subscriptions across bot restarts

## How to Use

1. Add @CosmosUpgradeBot to your group (or start a private chat)
2. Subscribe to networks you want alerts for
3. Get automatic notifications for upcoming upgrades

### Commands

- `/start` - Get started with the bot
- `/subscribe <network1> <network2> ...` - Subscribe to upgrade alerts
  - Example: `/subscribe cosmos osmosis juno`
- `/unsubscribe <network1> <network2> ...` - Remove subscriptions
- `/list` - See your current subscriptions
- `/listupgrades` - See upcoming upgrades for your subscribed networks
- `/test` - Test the notification system

### Example Group Setup

1. Add @CosmosUpgradeBot to your group
2. Subscribe to all networks:
`/subscribe akash cosmos juno neutron noble osmosis`
3. Use `/listupgrades` to see any upcoming upgrades
4. Wait for alerts when upgrades approach!

## Alert Timing

The bot will send alerts:
- 24 hours before an upgrade
- 2 hours before an upgrade
- When the upgrade time arrives

## Data Source
- Upgrade information is pulled from Polkachu's API
- Data is updated every 15 minutes
- Only shows verified, upcoming upgrades
  
## Support

If you have questions or issues, please open a GitHub issue or reach out to @clydedev on Telegram.
