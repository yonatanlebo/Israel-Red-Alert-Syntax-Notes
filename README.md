
# Israel Home Front Command Red Alert Monitor (Customized Version)

![Banner](graphics/banner.png)

## Disclaimer

These notes describe a **customized version** of the Red Alert Monitor, updated on September 20, 2025.  
No warranty is offered as to their accuracy — neither now nor at any future date.

This version builds upon the original [Israel-Red-Alert-Syntax-Notes](https://github.com/danielrosehill/Israel-Red-Alert-Syntax-Notes) repository, adding enhancements for:

- Dynamic target areas
- Improved MQTT publishing
- Automatic handling of all-clear scenarios
- Robust JSON parsing and logging

**Important:** Non-official alerting systems are intended only as additional sources. If personal safety depends on alerts, rely on official Home Front Command systems first.

---

## Intended Usage

This monitor allows you to:

- Poll the Home Front Command `Alerts.json` feed
- Track alerts for a specified area
- Publish MQTT events for Prewarning, Active, and All Clear alerts

It is fully compatible with Home Assistant or other smart home setups that support MQTT subscriptions.

---

## Information Security / InfoSec Considerations

- The monitor fetches JSON data directly from official endpoints.
- URLs are geo-restricted but easily discoverable through network inspection.
- Use this system responsibly; avoid exposing your alerts publicly to minimize risk.

---

## Alerting Endpoints

| Description     | URL                                                                                          | Format |
|-----------------|----------------------------------------------------------------------------------------------|--------|
| Active Alerts   | [Alerts.json](https://www.oref.org.il/warningMessages/alert/Alerts.json)                      | ![JSON](https://img.shields.io/badge/format-JSON-blue) |
| Alert History   | [AlertsHistory.json](https://www.oref.org.il/warningMessages/alert/History/AlertsHistory.json) | ![JSON](https://img.shields.io/badge/format-JSON-blue) |

---

## Alerting Cadence

Alerts are issued by the IDF for early warnings and active red alerts.  
Category meanings in the JSON:

| Hebrew Title | Category | Common Name | English Translation |
|--------------|----------|-------------|-------------------|
| `ירי רקטות וטילים` | 1 | Active Red Alert | Rocket and missile fire |
| `ירי רקטות וטילים - האירוע הסתיים` | 13 | All Clear | Rocket and missile fire - the event has ended |
| `בדקות הקרובות צפויות להתקבל התרעות באיזורים הבאים:` | 14 | Prewarning | Pre-warning: alerts expected soon |

---

## Custom Features in This Version

### 1. Dynamic Target Area
- Specify your monitored area via the environment variable `TARGET_AREA`.

### 2. Robust MQTT Integration
- Publishes alerts with JSON payloads to configurable topics:
  - `TOPIC_PREWARNING`
  - `TOPIC_ACTIVE`
  - `TOPIC_ALLCLEAR`
- Supports username/password authentication if needed.

### 3. All Clear Handling
- Automatically sends "All Clear" messages when:
  - No active alerts exist
  - A monitored alert transitions from Prewarning/Active to cleared

### 4. Resilient JSON Parsing
- Handles empty or malformed JSON responses gracefully
- Avoids errors from UTF-8 BOM or empty feeds

### 5. Logging & Debugging
- Logs to console and `red_alert_monitor.log`
- Levels: DEBUG, INFO, WARNING, ERROR

### 6. Environment Configuration
All settings can be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ALERTS_URL` | `https://www.oref.org.il/warningMessages/alert/Alerts.json` | Alerts API endpoint |
| `POLL_INTERVAL` | `5` | Seconds between polls |
| `REQUEST_TIMEOUT` | `10` | HTTP request timeout in seconds |
| `TARGET_AREA` | `ירושלים - מרכז` | Monitored area |
| `MQTT_BROKER` | `localhost` | MQTT broker host |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_USERNAME` | `None` | MQTT username (optional) |
| `MQTT_PASSWORD` | `None` | MQTT password (optional) |
| `MQTT_CLIENT_ID` | `red_alert_monitor` | MQTT client identifier |
| `TOPIC_PREWARNING` | `redalert/prewarning` | Topic for pre-warning alerts |
| `TOPIC_ACTIVE` | `redalert/active` | Topic for active alerts |
| `TOPIC_ALLCLEAR` | `redalert/allclear` | Topic for all-clear alerts |

---

## Running the Monitor

1. Set environment variables if you need custom configuration:
```bash
export TARGET_AREA="רחובות"
export MQTT_BROKER="192.168.0.44"
export MQTT_PORT=1883
```

2. Run the monitor:
```bash
python3 red_alert_monitor.py
```

3. The monitor will poll alerts, process them for the specified area, and publish MQTT events automatically.

---

## Logging

- Logs are written to both console and `red_alert_monitor.log`.
- Example log entries:
```
2025-09-20 17:12:15,647 - INFO - There are no alerts in the target area, everything is good.
2025-09-20 17:12:15,900 - WARNING - Disconnected from MQTT broker with code 7
2025-09-20 17:12:16,906 - INFO - Successfully connected to MQTT broker
```

---

## File Structure

```text
project-root/
│
├─ red_alert_monitor.py        # Main Python script
├─ red_alert_monitor.log       # Log file (created on run)
├─ graphics/
│   └─ banner.png              # Project banner
├─ README.md                   # This file
└─ requirements.txt            # Dependencies (if needed)
```

> Make sure to keep `graphics/banner.png` in place so that the README image renders correctly.

---

## Original Repository

This customized monitor builds on the original work:

[Israel-Red-Alert-Syntax-Notes by Daniel Rosehill](https://github.com/danielrosehill/Israel-Red-Alert-Syntax-Notes)

---

## License

Refer to the original repository for license information. Use responsibly and for personal alerting purposes only.
