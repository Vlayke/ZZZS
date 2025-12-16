# ZZZS GP availability alert (Telegram)



This tool checks the public ZZZS list of GPs, filters it by your criteria (location + service type + accepting new patients),

stores a daily CSV, and sends a Telegram message with changes compared to the previous run.



## What you need

- Docker (recommended), or Python 3.11 locally

- A Telegram bot token (via BotFather)

- Your Telegram chat ID (or a group chat ID)



## Setup (Docker + compose)

1) Clone the repo

2) Create `.env` from `.env.example` and fill in your values:

&nbsp;  - `TELEGRAM\_BOT\_TOKEN`

&nbsp;  - `TELEGRAM\_CHAT\_ID`



3) Start:

```bash

docker compose up --build



4) Schedule:
0 8 * * * cd /path/to/repo && docker compose run --rm zzzs-gp-alert
