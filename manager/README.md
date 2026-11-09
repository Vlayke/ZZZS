# Local management service

The default Compose stack runs continuously, hosting a local management GUI and scheduled Telegram alerts.

- Separate recipients, aliases, enabled/paused state, filters and notification preferences.
- Locations, practice types, GP/paediatric, gynaecology and dentistry categories, and accepting-new-patients selection.
- One-use invitation links (24-hour expiry). Recipients tap Start to join and use `/stop` to leave. `/status` reports subscription state.
- Matching-doctor previews, activity and connection status.
- SQLite persistence and individual change baselines. Failed deliveries retain their baseline for retry.

## Start

The GUI header includes a **Theme** selector with System, Light and Dark. It follows device appearance by default and saves an explicit preference in the browser.

Create a `data` directory at the repository root, writable by the container UID/GID (1000 by default). Keep permissions private: the database stores the bot token. From the repository root, run `docker compose up -d` and open `http://localhost:8096`.

In **Settings**, enter the bot token from [@BotFather](https://t.me/BotFather). Explicitly rejected tokens are not saved; network/server errors save the token with verification pending and retry automatically. The token is never returned to the browser. Use **Add subscriber** to choose an alias and filters, create an invitation, and share it privately with the recipient. An existing numeric chat ID can also be entered, provided that user has already started the bot.

For LAN access, configure these non-secret values in the root `.env`, substituting your private server IP and trusted subnet:

```dotenv
ZZZS_BIND_IP=192.168.1.20
ZZZS_ALLOWED_HOSTS=192.168.1.20,localhost,127.0.0.1
ZZZS_ALLOWED_NETWORKS=192.168.1.0/24,127.0.0.0/8
```

`ZZZS_UID`, `ZZZS_GID`, `ZZZS_PORT` and `ZZZS_DATA_DIR` are optional overrides. The default port binds only to loopback. This is a trusted-LAN administration interface without a separate login: do not port-forward it or put it behind a public reverse proxy. Source-IP/Host validation, cross-origin mutation checks and browser security headers are enabled. Forwarded client-IP headers are ignored.

## Checks and alerts

New users joining through an invitation immediately receive the full current matching list, or a clear no-matches message. Failed initial deliveries remain queued across restarts. The delivered list becomes their baseline; filter edits establish a fresh baseline without another initial message. Changes-only subscribers receive later additions/removals; daily-summary subscribers also receive unchanged summaries. Blank filter selections mean all values. The default check is 09:00 Europe/Ljubljana, configurable in Settings. Failed scheduled checks retry after 30 minutes. Refresh data updates previews without sending alerts or suppressing the scheduled notification check.

Manage edits aliases/filters, previews matches, pauses or removes subscribers. Rotating the same bot's token retains Telegram relationships; switching bots requires recipients to start the new bot. Invitations require a verified bot username. Connection failures are shown in the GUI.

One Gunicorn worker owns the scheduler and Telegram polling. Do not increase workers or replicas, which would duplicate schedules and polling. The moving `python:slim` image installs requirements into its temporary filesystem at startup; restarts require PyPI connectivity. The service runs unprivileged with read-only source/root filesystem, dropped capabilities, a restart policy and a healthcheck.

Back up `data` using SQLite's online backup API, or stop the service for a filesystem copy. Never commit the database or credentials. Run `python -m pip install -r manager/requirements.txt`, then `python -m unittest discover -s manager/tests -v` from the repository root. Tests cover filters, aliases, invitation replay protection, unsubscription, failed deliveries, schedules, parsing, credential redaction, pending-token verification and access checks.

The original one-shot script/Dockerfile remain available; the previous Compose configuration is retained as `docker-compose.legacy.yml`. Retire old cron/task-scheduler invocations when migrating to avoid duplicate alerts. Existing hardcoded IDs/tokens must be migrated privately; the public service does not load legacy credentials automatically.

The invitation result is highlighted and automatically scrolled into view when created. In Manage, **Send now** saves the current form settings and sends the full latest downloaded matching list to that subscriber, including when automatic notifications are paused. Successful sends update their change baseline; failures show an error and preserve the delivery baseline.

Telegram lists are grouped by town with separate multiline doctor entries (name, practice type, provider and address). Change alerts use 🟢 + for additions and 🔴 − for removals. Repeated accepting-yes labels are omitted; non-accepting doctors retain a warning when included by the filters. Long messages split between doctor entries when possible.
