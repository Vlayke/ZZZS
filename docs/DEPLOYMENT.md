# Deploy ZZZS Doctor Alerts v2.0

## Requirements

- A Linux Docker host with Docker Engine, the Docker Compose plugin and Git installed.
- Outbound HTTPS access to the container registry, PyPI, ZZZS and Telegram.
- A Telegram bot owned by you. Create or manage it with the official [@BotFather](https://t.me/BotFather).
- A trusted local network. The management GUI has no separate authentication and is not intended for public hosting.

## 1. Download and prepare storage

```sh
git clone https://github.com/Vlayke/ZZZS.git
cd ZZZS
git checkout v2.0.0
cp .env.example .env
mkdir -p data
sudo chown 1000:1000 data
chmod 700 data
```

The container runs as UID/GID 1000 by default. If you choose different `ZZZS_UID`/`ZZZS_GID` values in `.env`, give those IDs ownership of the data directory instead. Keep source files readable by the container. The source mount is read-only; only `data/` and the temporary dependency directory are writable.

## 2. Choose local-only or LAN access

The example environment file binds to `127.0.0.1:8096`. This allows access from the Docker host at **http://localhost:8096**. For a remote server, an SSH tunnel also works:

```sh
ssh -L 8096:127.0.0.1:8096 your-user@your-server
```

Then open http://localhost:8096 on your own computer.

For direct LAN access, edit `.env` using your server's actual private address and trusted subnet. Example values below are illustrative:

```dotenv
ZZZS_BIND_IP=192.168.1.20
ZZZS_PORT=8096
ZZZS_ALLOWED_HOSTS=192.168.1.20,localhost,127.0.0.1
ZZZS_ALLOWED_NETWORKS=192.168.1.0/24,127.0.0.0/8
```

Add a local DNS hostname to `ZZZS_ALLOWED_HOSTS` only if you will use it. Hostnames contain no scheme or port. Network entries use CIDR notation. Docker bridge addresses may be needed for host-side access if Docker presents those as the client IP; add only the required trusted bridge subnet if your deployment needs it.

Do not bind a public IP, forward this port from the Internet, or place it behind a public reverse proxy. The app validates source IP and Host, ignores forwarded client-IP headers, blocks cross-origin mutations and serves browser security headers. Every allowed LAN client can administer subscriptions and replace the bot token. Use a trusted network or SSH tunnel.

## 3. Start and check

```sh
docker compose config --quiet
docker compose up -d
docker compose ps
docker compose logs --tail=100 zzzs-manager
```

Initial startup installs requirements from PyPI and downloads the current workbooks. Allow a few minutes. The container healthcheck has a three-minute startup allowance. Open the GUI at the configured address; `/health` returns status and version without disclosing credentials.

If you use Dockhand, register this checkout's original Compose source in the correct environment and verify it is readable. Automatic container discovery alone does not register source. Preserve the `.env` file and host data paths when adopting the stack.

## 4. Connect Telegram

1. Open [@BotFather](https://t.me/BotFather) in Telegram.
2. Use `/newbot` for a new bot, or `/mybots` and **API Token** for an existing bot.
3. Open the app's **Settings**, paste the token and save.
4. Confirm the connected bot username appears. If Telegram is temporarily unavailable, the token can be saved pending verification and the app retries automatically. Explicitly rejected tokens are not saved.

The token is stored only in your private runtime database, never in source or a public environment file, and is never returned to the browser. Treat it as a password. Bot identification has a fallback for Telegram `getMe` timeouts. If another integration has a webhook or polls the same bot, migrate that integration deliberately: a bot should have one update consumer.

## 5. Add people and set alerts

Use **Add subscriber → Invitation link**, enter an alias and individual filters, create the link, then share it privately. The recipient taps **Start** in Telegram. Links are one-use and expire after 24 hours. No chat ID lookup is needed. The recipient receives a current full matching list, including a clear no-matches message if applicable.

An existing numeric chat ID can also be added manually if that recipient has already started this bot. Manual ID entry alone does not trigger the invitation welcome flow; use **Send now** for an initial full list.

Each subscriber can use changes-only or daily summaries, and can be paused or removed. **Send now** saves the open form and sends the full current list. **Send test notification** sends fictional green-plus/red-minus examples without saving edits or changing delivery baselines. `/stop` removes a subscriber; `/status` returns their status.

The default scheduled check is **09:00 Europe/Ljubljana**, including daylight-saving changes. Configure it in Settings. The service is not a live feed from ZZZS. Source dates can differ by workbook. Failed scheduled checks retry after 30 minutes; queued initial lists retry automatically. **Refresh data** updates the catalog without sending alerts or consuming the scheduled notification check.

## Updates

Back up runtime data first, then fetch the release you intend to use:

```sh
git fetch origin --tags
git checkout v2.0.0
docker compose pull
docker compose up -d --force-recreate
docker compose ps
```

Substitute a newer release tag when upgrading. `python:slim` is a moving image reference; do not replace it with a bare image ID or digest if you want image-update tracking. Dependencies install at startup and are not version-pinned. Review upstream Python/dependency changes and any migration notes before upgrades. Run exactly one service replica and one Gunicorn worker.

## Backups and restore

The `data/` directory contains the SQLite database (bot token, subscriber IDs, filters, baselines and invitations) and cached doctor data. Never upload it or include it in a public release.

For a straightforward consistent backup, stop the service briefly:

```sh
docker compose stop zzzs-manager
umask 077
tar -czf ../zzzs-private-data-backup.tar.gz data .env
docker compose start zzzs-manager
```

Keep this archive outside the repository and protect/encrypt it as appropriate for your storage. Alternatively use SQLite's online backup API for a live database backup; do not copy only the live `.sqlite` file while ignoring its WAL. Back up the source revision and non-secret deployment configuration too.

To restore, stop the service, restore `data/` and `.env` into the intended checkout, restore private permissions/UID/GID ownership, then start and check health. Database schema additions are applied automatically at startup. Retain a backup before downgrading: older releases are not guaranteed to understand newer schemas.

## Migrate from the one-shot script

1. Keep a private backup of the original script, Dockerfile, CSV history, token/chat-ID settings and cron entry.
2. Start v2.0 and enter the same bot's token through Settings.
3. Re-create aliases and filters; invite users or add their existing IDs privately. Legacy credentials are intentionally not read from public source automatically.
4. Verify data, the Telegram connection and a test message to an intended recipient.
5. Retire the old cron/task-scheduler job to avoid duplicate messages. Keep the old files and schedule as rollback evidence.

v2.0 establishes its own baseline and does not import legacy CSV comparisons. The original script and `docker-compose.legacy.yml` remain available, but restarting the old cron without its required local image reproduces the old missing-image failure.

## Troubleshooting

- **403:** check the configured Host and the actual client IP against the allowlists; forwarded IP headers are intentionally ignored.
- **Permission denied / database cannot open:** check ownership and write permission on the host data directory for the configured UID/GID.
- **Container cannot start after restart:** verify registry/PyPI access and read container logs; requirements install at each start.
- **Telegram pending/rejected:** verify the token in BotFather and inspect the app's connection status. Rotating the same bot's token retains Telegram relationships; changing to another bot requires users to start that new bot.
- **Duplicate/conflicting polling:** ensure the bot has only one update consumer and the service has exactly one worker/replica.
- **No matches:** category and practice-type filters apply together. Blank selections include all values; incompatible selections produce zero matches.

Do not paste tokens, private database files, full environment exports or private backups into bug reports.
