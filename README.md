# <img src="custom_components/shielddns/brand/logo.png" height="50"> ShieldDNS for Home Assistant

[![GitHub Release](https://img.shields.io/github/release/FaserF/ha-shielddns.svg?style=flat-square)](https://github.com/FaserF/ha-shielddns/releases)
[![License](https://img.shields.io/github/license/FaserF/ha-shielddns.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![CI Orchestrator](https://github.com/FaserF/ha-shielddns/actions/workflows/ci-orchestrator.yml/badge.svg)](https://github.com/FaserF/ha-shielddns/actions/workflows/ci-orchestrator.yml)
[![Renovate](https://img.shields.io/badge/renovate-enabled-brightgreen.svg?style=flat-square)](https://renovatebot.com)

Monitor and manage your privately hosted [ShieldDNS](https://github.com/FaserF/ShieldDNS) ad-blocking and DNS resolver directly from Home Assistant. Track DNS queries, monitor blocklist effectiveness, and instantly toggle global web-filtering protection with ease.

## 🧭 Quick Links

| | | | |
| :--- | :--- | :--- | :--- |
| [✨ Features](#-features) | [📦 Installation](#-installation) | [⚙️ Configuration](#️-configuration) | [🧱 Entities](#-entities) |
| [📖 Automations](#-automation-examples) | [❓ FAQ](#-troubleshooting--faq) | [🧑‍💻 Development](#-development) | |

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FaserF&repository=ha-shielddns&category=integration)

### Why use this integration?
ShieldDNS provides high-performance encrypted DoH/DoT DNS resolution with powerful ad and malware blocking. This integration provides **native monitoring** via the ShieldDNS API, allowing you to track daily queries, view how many ads were blocked, and control the entire protection mechanism (On/Off) instantly from your Home Assistant dashboard.

No manual script-polling or complex setup is required — everything is handled via a modern, auto-discovering Config Flow.

## ✨ Features

- **DNS Monitoring**:
  - **Total Queries**: Track exactly how many DNS requests were made across your network today.
  - **Blocked Queries**: See how many ads, trackers, and malicious domains were stopped.
  - **Block Percentage**: Real-time ratio of blocked vs allowed traffic.
  - **Unique Clients**: Monitor how many individual devices are currently utilizing ShieldDNS.
  - **Performance Metrics**: Monitor **Average Response Time** (latency) and **Cache Hit Ratio** to ensure peak resolution speed.
- **Instance Management**:
  - **Global Filtering (Toggle)**: Instantly suspend or resume all blocklists and filtering across your entire network with a single switch.
  - **Refresh Blocklists**: Native button to sync and update your blocklists on demand.
- **System Information**:
  - Track your ShieldDNS instance performance directly via sensors.
- **Native Experience**:
  - **Full Localization**: English translations included (more coming soon).
  - **Modern UI**: High-quality icons and branding for a premium dashboard look.

> [!TIP]
> **Running ShieldDNS directly within Home Assistant OS?**
> Use the official [ShieldDNS Home Assistant Addon](https://github.com/FaserF/hassio-addons/tree/master/ShieldDNS) to install ShieldDNS as a supervised Add-on — no Docker setup required!
> Once the addon is running, come back here to install this integration to connect it to your HA dashboard.

## ❤️ Support This Project

> I maintain this integration in my **free time alongside my regular job** — bug hunting, new features, and keeping up with OCI updates. Every donation helps me stay independent and dedicate more time to open-source work.
>
> **This project is and will always remain 100% free.**
>
> Donations are completely voluntary — but the more support I receive, the more time I can realistically invest into these projects. 💪

<div align="center">

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20on-GitHub-%23EA4AAA?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/FaserF)&nbsp;&nbsp;
[![PayPal](https://img.shields.io/badge/Donate%20via-PayPal-%2300457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/FaserF)

</div>

## 📦 Installation

### HACS (Recommended)

1. Open HACS in Home Assistant.
2. Click the three dots -> **Custom repositories**.
3. Add `FaserF/ha-shielddns` with category **Integration**.
4. Search for **ShieldDNS**.
5. Install and restart Home Assistant.

### Manual Installation

1. Download the latest release from the [Releases](https://github.com/FaserF/ha-shielddns/releases) page.
2. Extract the `custom_components/shielddns` folder to your Home Assistant `custom_components` directory.
3. Restart Home Assistant.

## ⚙️ Configuration

### 1. ShieldDNS API Token Setup (Required)
The integration requires an API Token to communicate with your ShieldDNS instance securely.

1. Open the ShieldDNS Web UI and navigate to **Settings** > **API Keys**.
2. Create a new API key with the following permissions:
    - `read:stats` (Required for sensors and status)
    - `write:filtering` (Required for toggling protection and refreshing lists)
3. Copy the generated token.
4. Note down the generated API Token.

### 2. Home Assistant Integration Setup
1. Go to **Settings > Devices & Services**.
2. Click **Add Integration** and search for **ShieldDNS**.
3. Enter the following details:
   - **Host**: The IP address or hostname of your ShieldDNS server (e.g. `192.168.1.100`).
   - **Port**: The Admin port of your ShieldDNS instance (usually `443` or `8080`).
   - **API Token**: The token you generated in Step 1.
4. The integration will now connect, authenticate, and automatically add your sensors and switches.

> [!NOTE]
> **Adjust later**: You can update your **API Token** or change the **Update Interval** (default: 5 minutes) at any time by going to the integration page in Home Assistant and clicking **Configure**.

## 🧱 Entities

The integration provides the following entities to monitor and control your DNS network:

### Sensors
- **Total Queries Today**: Absolute count of all DNS requests processed today.
- **Blocked Queries Today**: Absolute count of requests blocked by your filter lists.
- **Block Percentage**: The percentage of today's total traffic that was blocked.
- **Unique Clients**: How many client IPs have made queries in the last 24 hours.
- **Avg. Response Time**: The average latency of DNS resolutions in milliseconds.
- **Cache Hit Ratio**: Effectiveness of the local cache (percentage of queries served from cache).
- **CPU Load (1m)**: The current 1-minute system load average.
- **Memory Usage**: Amount of RAM currently utilized by the system (in MB).
- **Database Size**: Current size of the SQLite query database on disk.
- **Auto-Blocked Clients**: Number of clients currently under automated abuse protection.
- **Connected Clients**: Real-time count of all unique devices that have utilized ShieldDNS for resolution.

### Binary Sensors
- **ShieldDNS Update Available**: On if a newer version of the ShieldDNS app is available on GitHub.
- **CoreDNS Update Available**: On if a newer version of the CoreDNS engine is available.
- **Abuse Protection Active**: On if any client is currently blocked due to malicious behavior patterns.

### Switch
- **Global Filtering**: Turn this off to temporarily disable all ad-blocking and filtering. Turn it back on to resume normal protection.

### Button
- **Refresh Blocklists**: Push this button to force ShieldDNS to fetch the latest updates for all subscribed filter lists immediately.

### Services
- **`shielddns.block_domain`**: Instantly add a domain to the blocklist.
- **`shielddns.allow_domain`**: Instantly add a domain to the allowlist.
- **`shielddns.remove_rule`**: Remove a domain rule from both lists.
- **`shielddns.set_client_alias`**: Assign a friendly name (alias) to a client's IP address.
- **`shielddns.block_client`**: Toggle blocking status for a specific client device by its IP.

## 📖 Automation Examples

<details>
<summary><strong>🚨 Notification on High Block Rate Warning</strong></summary>

```yaml
alias: "ShieldDNS: High Block Rate Alert"
trigger:
  - platform: numeric_state
    entity_id: sensor.shielddns_block_percentage
    above: 80
action:
  - service: notify.notify
    data:
      title: "🛡️ ShieldDNS Traffic Alert"
      message: "Warning: Over {{ states('sensor.shielddns_block_percentage') }}% of your DNS queries are being blocked. A device might be compromised or aggressively pinging tracking domains."
```
</details>

<details>
<summary><strong>🔁 Night Mode: Disable Filtering for Specific Maintenance</strong></summary>

```yaml
alias: "ShieldDNS: Temporarily Disable Filtering for Backup Jobs"
trigger:
  - platform: time
    at: "03:00:00"
action:
  - service: switch.turn_off
    target:
      entity_id: switch.shielddns_global_filtering
  - delay:
      hours: 1
  - service: switch.turn_on
    target:
      entity_id: switch.shielddns_global_filtering
```
</details>

<details>
<summary><strong>🕒 Parental Control: Block TikTok at Night</strong></summary>

```yaml
alias: "ShieldDNS: Block TikTok at 8 PM"
trigger:
  - platform: time
    at: "20:00:00"
action:
  - service: shielddns.block_domain
    data:
      domain: "tiktok.com"
```
</details>

## ❓ Troubleshooting & FAQ

### "Failed to connect" during setup
- Double-check your **Host** and **Port**. If your ShieldDNS is behind a reverse proxy, ensure the port matches the external proxy port.
- Ensure the **API Token** was copied correctly and hasn't been revoked.

### The Global Filtering switch turns back on/off immediately after I click it
- This usually indicates a permissions issue. Ensure your API Token has the `write:filtering` permission to toggle state modifications.

## 🧑‍💻 Development

```bash
# Setup development environment
pip install requirements_test.txt

# Run tests
pytest

# Run linter
ruff check .
```

## 📄 License
MIT License. See [LICENSE](LICENSE) for details.
