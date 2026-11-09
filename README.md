# ZZZS Doctor Alerts · v2.0

A self-hosted, local-network management app for Telegram notifications about doctors accepting new patients in Slovenia. Uses public ZZZS data; **not affiliated with ZZZS**.

## What's new in v2.0

- Always-running Docker service with a web GUI, replacing disposable cron runs.
- Separate Telegram subscribers, editable aliases and individual location, category and practice-type filters.
- One-use registration links, an immediate initial matching list, `/stop` unsubscription and `/status`.
- Changes-only or daily notifications, plus **Send now** and fictional **Send test notification** controls.
- Structured lists grouped by town, green-plus additions and red-minus removals.
- GP/paediatric, gynaecology and dentistry data; current-match previews and activity/status.
- Persistent subscriptions, delivery baselines and initial-message retries.
- System, Light and Dark appearance; medical staff favicon and visible version.

## Deploy

See **[Deployment guide](docs/DEPLOYMENT.md)** for Linux Docker setup, local-network configuration, Telegram onboarding, updates, backups and migration from the original script.

```sh
git clone https://github.com/Vlayke/ZZZS.git
cd ZZZS
git checkout v2.0.0
cp .env.example .env
mkdir -p data
sudo chown 1000:1000 data
chmod 700 data
docker compose up -d
```

Open **http://localhost:8096** on the Docker host. For access from another device, configure the host's private IP, allowed hostname and trusted subnet in `.env` as described in the guide. Enter the Telegram bot token privately in the app's **Settings**; it is not included in source or Compose configuration.

The GUI is intended for a **trusted LAN and has no separate login**. Do not expose it to the public Internet. The default published port binds only to loopback.

## Register a subscriber

1. Choose **Add subscriber → Invitation link**.
2. Set their alias, filters and notification preferences.
3. Create the invitation and copy the highlighted link.
4. Share it privately. The recipient opens it in Telegram and taps **Start**.

Links expire after 24 hours and can be used once. The recipient receives the initial list immediately. Category selects a broad group; practice type narrows that group, and both filters must match. Blank selections include all values.

## Security and data

Runtime data lives in the private `data/` directory, including the bot credential and subscriber IDs. It is excluded from Git, along with environment files, databases, backups and keys. Tokens are never returned by the app API. Keep your database and backups private; see the deployment guide for safe backups and secret rotation.

## Development

```sh
python -m pip install -r manager/requirements.txt
python -m unittest discover -s manager/tests -v
```

Production uses one Gunicorn worker with eight HTTP threads. Do not scale workers or replicas: the same process owns scheduling and Telegram polling. The Docker image follows the moving `python:slim` tag. Dependencies are installed from PyPI at startup, so restarts require registry/PyPI connectivity.

See [release notes](CHANGELOG.md), [management behavior](manager/README.md) and the [archived legacy instructions](docs/legacy-readme.md). The original script, Dockerfile and `docker-compose.legacy.yml` remain available for compatibility. MIT licensed.
