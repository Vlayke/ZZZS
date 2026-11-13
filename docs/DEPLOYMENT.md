# Namestitev ZZZS Doctor Alerts v2.0

🇸🇮 Slovenska navodila so prva. [English instructions below](#english-instructions).

## Zahteve

- Strežnik Linux z nameščenimi Docker Engine, vtičnikom Docker Compose in Gitom.
- Izhodni dostop HTTPS do registra slik, PyPI, ZZZS in Telegrama.
- Bot Telegram, ki ga upravljate sami. Ustvarite ali uredite ga z uradnim [@BotFather](https://t.me/BotFather).
- Zaupanja vredno lokalno omrežje. Vmesnik nima ločene prijave in ni namenjen javnemu gostovanju.

## 1. Prenos in priprava prostora za podatke

```sh
git clone https://github.com/Vlayke/ZZZS.git
cd ZZZS
git checkout v2.0.0
cp .env.example .env
mkdir -p data
sudo chown 1000:1000 data
chmod 700 data
```

Vsebnik se privzeto izvaja z UID/GID 1000. Če v `.env` izberete drugačni vrednosti `ZZZS_UID` in `ZZZS_GID`, temu prilagodite lastništvo podatkovne mape. Izvorne datoteke morajo biti berljive za uporabnika vsebnika. Izvorna koda je priklopljena samo za branje; zapisovanje je omogočeno v `data/` in začasno mapo odvisnosti.

## 2. Dostop samo z gostitelja ali iz lokalnega omrežja

Vzorčna datoteka nastavi naslov `127.0.0.1:8096`. Na gostitelju Docker odprite **http://localhost:8096**. Pri oddaljenem strežniku lahko uporabite tunel SSH:

```sh
ssh -L 8096:127.0.0.1:8096 vas-uporabnik@vas-streznik
```

Nato na svojem računalniku odprite http://localhost:8096.

Za neposreden dostop iz lokalnega omrežja v `.env` vnesite dejanski zasebni naslov strežnika in zaupanja vredno podomrežje. Spodnje vrednosti so samo primer:

```dotenv
ZZZS_BIND_IP=192.168.1.20
ZZZS_PORT=8096
ZZZS_ALLOWED_HOSTS=192.168.1.20,localhost,127.0.0.1
ZZZS_ALLOWED_NETWORKS=192.168.1.0/24,127.0.0.0/8
```

V `ZZZS_ALLOWED_HOSTS` dodajte lokalno ime DNS, če ga boste uporabljali. Imena ne vsebujejo protokola ali vrat. Omrežja so zapisana v obliki CIDR. Pri dostopu z gostitelja je v nekaterih okoljih potreben tudi naslov mostu Docker, če ga Docker predstavi kot naslov odjemalca; v tem primeru dodajte le potrebno zaupanja vredno podomrežje mostu.

Ne uporabljajte javnega naslova IP, ne posredujte teh vrat iz interneta in vmesnika ne objavite prek javnega povratnega posrednika. Aplikacija preverja izvorni naslov IP in ime gostitelja, ne zaupa posredovanim glavam z naslovom odjemalca ter preprečuje spremembe z drugih spletnih mest. Vsak dovoljen odjemalec v lokalnem omrežju lahko upravlja prijave in zamenja žeton bota. Uporabite zaupanja vredno omrežje ali tunel SSH.

## 3. Zagon in preverjanje

```sh
docker compose config --quiet
docker compose up -d
docker compose ps
docker compose logs --tail=100 zzzs-manager
```

Ob prvem zagonu se odvisnosti namestijo iz PyPI in prenesejo trenutne preglednice. Počakajte nekaj minut. Preverjanje zdravja vsebnika ima triminutno začetno obdobje. Vmesnik odprite na nastavljenem naslovu; `/health` vrne stanje in različico brez razkritja žetonov.

Če uporabljate Dockhand, izvirni vir Compose iz tega delovnega imenika registrirajte v pravilnem okolju in preverite, da je berljiv. Samodejno zaznavanje vsebnika še ne pomeni registracije vira. Ob prevzemu sklada ohranite datoteko `.env` in poti do podatkov na gostitelju.

## 4. Povezava s Telegramom

1. V Telegramu odprite [@BotFather](https://t.me/BotFather).
2. Za novega bota uporabite `/newbot`; za obstoječega `/mybots` in **API Token**.
3. V aplikaciji odprite **Settings**, prilepite žeton in shranite.
4. Preverite, da se prikaže uporabniško ime povezanega bota. Če Telegram začasno ni dosegljiv, se žeton shrani s čakajočim preverjanjem, aplikacija pa samodejno ponavlja poskuse. Izrecno zavrnjen žeton se ne shrani.

Žeton je shranjen samo v zasebni podatkovni zbirki aplikacije, nikoli v izvorni kodi ali javni datoteki z nastavitvami, in se nikoli ne vrne v brskalnik. Obravnavajte ga kot geslo. Aplikacija ima nadomestni način prepoznavanja bota ob časovnih prekoračitvah metode `getMe`. Če isti bot že uporablja drugo integracijo s klici webhook ali prevzemanjem sporočil, prehod izvedite načrtno: bot naj ima enega odjemalca za prevzem novih sporočil.

## 5. Prejemniki in obvestila

Izberite **Add subscriber → Invitation link**, vnesite prikazno ime in osebne filtre, ustvarite povezavo ter jo zasebno pošljite prejemniku. Ta v Telegramu pritisne **Start**. Povezava je enkratna in velja 24 ur. Iskanje identifikatorja klepeta ni potrebno. Prejemnik takoj dobi celoten trenutni seznam ali jasno sporočilo, da ni zadetkov.

Identifikator obstoječega klepeta lahko dodate tudi ročno, če je prejemnik tega bota že zagnal. Sam ročni vnos ne sproži začetnega obvestila prek vabila; za začetni seznam uporabite **Send now**.

Vsak prejemnik lahko izbira med obvestili samo ob spremembah in dnevnimi povzetki. Z **Suspend / Resume** v seznamu ali **Suspend notifications / Resume notifications** v Manage samodejna obvestila ustavite ali znova omogočite brez izbrisa prijave. Prikazno ime, filtri in primerjalni seznami se ohranijo; začetna sporočila na čakanju med ustavitvijo počakajo. Novo vabilo ali ukaz Telegram ni potreben. Naslednje redno preverjanje lahko pokaže spremembe od zadnje dostave. **Send now** shrani odprti obrazec in pošlje celoten trenutni seznam. **Send test notification** pošlje izmišljeni primer zelenega plusa in rdečega minusa brez shranjevanja sprememb ali spreminjanja primerjalnega seznama. `/stop` prejemnika odjavi, `/status` pa vrne stanje.

Privzeti čas preverjanja je **09:00 Europe/Ljubljana**, z upoštevanjem poletnega časa. Nastavite ga v **Settings**. Aplikacija ni neposreden sprotni vir podatkov ZZZS; datumi posameznih preglednic se lahko razlikujejo. Neuspelo redno preverjanje se ponovi po 30 minutah, začetna obvestila na čakanju pa se ponovno poskušajo dostaviti samodejno. **Refresh data** osveži podatke brez pošiljanja obvestil in ne nadomesti rednega preverjanja.

## Posodobitve

Najprej varnostno kopirajte podatke, nato prenesite želeno izdajo:

```sh
git fetch origin --tags
git checkout v2.0.0
docker compose pull
docker compose up -d --force-recreate
docker compose ps
```

Pri nadgradnji uporabite oznako novejše izdaje. `python:slim` je premična oznaka slike; če želite spremljanje novih slik, je ne zamenjajte z golim identifikatorjem slike ali povzetkom digest. Odvisnosti se namestijo ob zagonu in niso vezane na točno določene različice. Pred nadgradnjo preverite spremembe Pythona, odvisnosti in morebitna navodila za migracijo. Uporabljajte natanko eno repliko storitve in en proces Gunicorn.

## Varnostne kopije in obnova

Mapa `data/` vsebuje podatkovno zbirko SQLite z žetonom bota, identifikatorji prejemnikov, filtri, primerjalnimi seznami in vabili ter predpomnjene podatke o zdravnikih. Nikoli je ne nalagajte v javni repozitorij ali izdajo.

Za preprosto in skladno kopijo storitev začasno ustavite:

```sh
docker compose stop zzzs-manager
umask 077
tar -czf ../zzzs-private-data-backup.tar.gz data .env
docker compose start zzzs-manager
```

Arhiv hranite zunaj repozitorija in ga ustrezno zaščitite oziroma šifrirajte. Za kopiranje med delovanjem uporabite spletni API za varnostno kopiranje SQLite; ne kopirajte samo žive datoteke `.sqlite` brez upoštevanja datoteke WAL. Shranite tudi oznako izvorne različice in nejavne nastavitve namestitve.

Za obnovo ustavite storitev, obnovite `data/` in `.env` v izbrano kopijo repozitorija, uredite zasebna dovoljenja in lastništvo UID/GID, nato storitev zaženite in preverite zdravje. Dodatki v shemo zbirke se uveljavijo samodejno ob zagonu. Pred prehodom na starejšo različico obdržite kopijo: starejše izdaje morda ne razumejo novejših shem.

## Prehod s stare skripte

1. Zasebno shranite staro skripto, Dockerfile, zgodovino CSV, žeton, identifikatorje klepetov in vnos cron.
2. Zaženite v2.0 in v **Settings** vnesite žeton istega bota.
3. Znova nastavite prikazna imena in filtre ter prejemnike povabite ali njihove identifikatorje vnesite zasebno. Javna izvorna koda namenoma ne bere starih žetonov samodejno.
4. Preverite podatke, povezavo s Telegramom in testno sporočilo izbranemu prejemniku.
5. Izključite stari vnos cron oziroma drugo načrtovano opravilo, da preprečite podvojena obvestila. Stare datoteke in urnik ohranite za morebitno vrnitev.

v2.0 ustvari svoj primerjalni seznam in ne uvozi stare zgodovine CSV. Stara skripta in `docker-compose.legacy.yml` ostajata na voljo, vendar ponovni zagon starega opravila brez zahtevane lokalne slike spet povzroči napako manjkajoče slike.

## Odpravljanje težav

- **403:** preverite dovoljeno ime gostitelja in dejanski naslov odjemalca. Posredovane glave z naslovi IP se namenoma ne upoštevajo.
- **Zavrnjeno dovoljenje ali ni mogoče odpreti zbirke:** preverite lastništvo in pravico pisanja v podatkovno mapo za nastavljeni UID/GID.
- **Vsebnik se po ponovnem zagonu ne zažene:** preverite dostop do registra in PyPI ter dnevnike vsebnika; odvisnosti se namestijo ob vsakem zagonu.
- **Preverjanje Telegrama čaka ali je zavrnjeno:** preverite žeton v BotFatherju in stanje povezave v aplikaciji. Zamenjava žetona istega bota ohrani povezave s prejemniki; pri drugem botu ga morajo prejemniki najprej zagnati.
- **Podvojeno ali neusklajeno prevzemanje sporočil:** zagotovite enega odjemalca za bota ter natanko en proces in eno repliko storitve.
- **Ni zadetkov:** kategorija in vrsta ambulante morata ustrezati hkrati. Prazna izbira vključuje vse vrednosti, nezdružljiva izbira pa ne vrne zadetkov.

V prijave napak ne vključujte žetonov, zasebnih podatkovnih zbirk, celotnih izvozov okolja ali zasebnih varnostnih kopij.

---

# English instructions

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

Each subscriber can use changes-only or daily summaries. Use **Suspend** / **Resume** in the list, or **Suspend notifications** / **Resume notifications** in Manage, to stop or resume automatic messages without deleting the subscriber. Registration, alias, filters and baselines are retained; queued initial messages wait during suspension. No new invitation or Telegram commands are needed. A subsequent scheduled check may include changes since the previous delivery. **Send now** saves the open form and sends the full current list. **Send test notification** sends fictional green-plus/red-minus examples without saving edits or changing delivery baselines. `/stop` removes a subscriber; `/status` returns their status.

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
