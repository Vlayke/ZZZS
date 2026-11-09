# Changelog

## v2.0.0 — 2026-11-09

### New management application

- Replaced the default one-shot cron workflow with a continuously running local Docker service and web GUI.
- Added individual Telegram subscribers, aliases, pause/removal controls, location filters, broad doctor categories and specific practice types.
- Added GP/paediatric, gynaecology and dentistry sources, result previews, activity and connection status.
- Added one-use invitations with a highlighted result, copy action and automatic scrolling.
- New invitation registrations receive a full initial matching list with durable retry after delivery failure.
- Added per-subscriber **Send now** and **Send test notification** controls.
- Added daily or changes-only alerts, configurable daily check time and manual catalog refresh.

### Notification presentation

- Green-plus additions and red-minus removals, with separate multiline entries for each doctor.
- Explicit town headings, including continuation headings across long Telegram messages.
- Removed repeated accepting-yes labels while retaining non-accepting warnings when relevant.
- Clearly labelled fictional test examples that leave real subscription baselines unchanged.

### Interface and operations

- System/Light/Dark appearance with a saved browser preference.
- Rod of Asclepius favicon, matching brand icon and visible v2.0 label.
- Persistent SQLite data, per-user delivery baselines, retry handling and bot-identity fallback.
- Trusted-LAN source-IP/Host checks, cross-origin mutation protection and credential redaction.
- Unprivileged, read-only runtime with healthcheck and restart policy; configurable local-only/LAN Compose deployment.
- Deployment, migration, backup/restore and troubleshooting documentation. No runtime credentials or subscriber records are distributed.

### Compatibility

The default Compose service is now the management application. The original script/Dockerfile and `docker-compose.legacy.yml` remain available. Migrate credentials and subscriptions privately and retire the old scheduler; legacy CSV history is not imported automatically. The runtime follows moving Python/dependency releases and requires PyPI connectivity on startup. This GUI has no separate login and must remain on a trusted LAN or behind an SSH tunnel.

### Validation

18 automated tests cover parsing, isolated filters, registration, initial delivery/retries, message formatting/chunking, manual/test sends, token handling, secret redaction and access restrictions. Live deployment validation checks health, versioned assets, Telegram connectivity and Dockhand source registration.

## v1.0.0 — 2025-12-16

Initial public release of the one-shot doctor-filtering script with Docker and Telegram alerts.
