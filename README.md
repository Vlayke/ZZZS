# ZZZS · Obvestila o prostih zdravnikih · v2.0

🇸🇮 **Slovenska različica je prva.** [English version below](#english-version).

Aplikacija za samostojno gostovanje v lokalnem omrežju, ki prek Telegrama obvešča o zdravnikih, ki sprejemajo nove paciente. Uporablja javne podatke ZZZS. **Projekt ni povezan z ZZZS.**

## Novosti v različici v2.0

- Stalno delujoča storitev Docker s spletnim vmesnikom namesto posameznih zagonov prek crona.
- Ločeni prejemniki obvestil, urejanje prikaznih imen in osebni filtri po kraju, kategoriji ter vrsti ambulante.
- Enkratne povezave za prijavo, takojšen začetni seznam zadetkov, odjava z `/stop` in pregled stanja z `/status`.
- Obvestila samo ob spremembah ali dnevni povzetki; gumba **Send now** in **Send test notification**.
- Pregledni seznami po krajih; zeleni plusi za dodane in rdeči minusi za odstranjene zdravnike.
- Podatki o splošnih in otroških zdravnikih, ginekologih ter zobozdravnikih; predogled zadetkov in pregled delovanja.
- Trajno shranjene prijave, primerjalni seznami in ponovni poskusi dostave začetnih obvestil.
- Svetla, temna ali sistemska tema, medicinska ikona in vidna oznaka različice.

## Namestitev

**[Navodila za namestitev](docs/DEPLOYMENT.md)** opisujejo Docker na Linuxu, dostop iz lokalnega omrežja, povezavo s Telegramom, posodobitve, varnostne kopije in prehod s stare skripte.

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

Na gostitelju Docker odprite **http://localhost:8096**. Za dostop iz druge naprave v `.env` nastavite zasebni naslov strežnika, dovoljeno ime gostitelja in zaupanja vredno podomrežje, kot je opisano v navodilih. Žeton bota Telegram vnesite zasebno v **Settings**; ni del izvorne kode ali konfiguracije Compose.

Vmesnik je namenjen **zaupanja vrednemu lokalnemu omrežju in nima ločene prijave**. Ne izpostavljajte ga javnemu internetu. Privzeto so vrata dostopna samo prek povratnega naslova na gostitelju.

## Prijava novega prejemnika

1. Izberite **Add subscriber → Invitation link**.
2. Vnesite prikazno ime, filtre in nastavitve obvestil.
3. Ustvarite vabilo in kopirajte poudarjeno povezavo.
4. Povezavo zasebno pošljite prejemniku. Ta jo odpre v Telegramu in pritisne **Start**.

Povezava velja 24 ur in jo je mogoče uporabiti enkrat. Prejemnik takoj prejme začetni seznam. Kategorija določa širšo skupino, vrsta ambulante pa jo dodatno zoži; izpolnjena morata biti oba pogoja. Prazna izbira vključuje vse vrednosti.

## Varnost in podatki

Podatki aplikacije so shranjeni v zasebni mapi `data/`, vključno z žetonom bota in identifikatorji prejemnikov. Mapa je izključena iz Gita, prav tako datoteke z nastavitvami okolja, podatkovne zbirke, varnostne kopije in ključi. API aplikacije nikoli ne vrne shranjenega žetona. Podatkovno zbirko in kopije hranite zasebno; navodila opisujejo varno kopiranje in menjavo žetona.

## Razvoj

```sh
python -m pip install -r manager/requirements.txt
python -m unittest discover -s manager/tests -v
```

Produkcijska storitev uporablja en proces Gunicorn z osmimi nitmi HTTP. Ne povečujte števila procesov ali replik, saj isti proces izvaja urnik preverjanja in prevzema sporočila iz Telegrama. Slika Docker uporablja premično oznako `python:slim`. Odvisnosti se ob zagonu namestijo iz PyPI, zato ponovni zagon potrebuje dostop do registra in PyPI.

Glejte tudi [opis sprememb](CHANGELOG.md), [podrobnosti upravljanja v angleščini](manager/README.md) in [arhivirana navodila za staro skripto](docs/legacy-readme.md). Izvirna skripta, Dockerfile in `docker-compose.legacy.yml` ostajajo na voljo zaradi združljivosti. Licenca MIT.

## Začasna ustavitev obvestil

Ko prejemnik najde zdravnika, pri njem kliknite **Suspend** ali v **Manage** izberite **Suspend notifications**. Samodejna obvestila in začetne dostave na čakanju se ustavijo, prijava, prikazno ime in filtri pa ostanejo shranjeni. **Resume** oziroma **Resume notifications** obveščanje znova omogoči brez novega vabila ali ukazov Telegram. Gumba **Send now** in **Send test notification** ostaneta na voljo kot ročni dejanji. Po nadaljevanju se ob rednem preverjanju lahko pokažejo tudi spremembe od zadnje dostave pred ustavitvijo.

---

# English version

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

## Suspend and resume a subscriber

Use **Suspend** in the subscriber list or **Manage → Suspend notifications** to stop automatic alerts and queued initial messages while keeping the registration, alias, filters and history. **Resume** / **Resume notifications** enables delivery again without another invitation or Telegram command. Explicit manual/test sends remain available. A later scheduled check may report changes since the last delivery before suspension.
