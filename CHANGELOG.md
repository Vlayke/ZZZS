# Dnevnik sprememb

## Posodobitev po v2.0.0 — 2026-11-13

- Jasna gumba Suspend / Resume v seznamu prejemnikov in oknu za urejanje.
- Ustavitev ohrani prijavo, prikazno ime, filtre in zgodovino ter zadrži začetne dostave na čakanju.
- Ponovno preverjanje stanja pred samodejnim pošiljanjem prepreči pošiljanje prejemniku, ki je bil med preverjanjem ustavljen.
- 21 testov pokriva tudi ohranitev nastavitev, nadaljevanje in ustavljene začetne dostave.

## v2.0.0 — 2026-11-09

ZZZS Doctor Alerts je neodvisna aplikacija za spremljanje javnih seznamov zdravnikov in pošiljanje osebnih obvestil prek Telegrama. **Projekt ni povezan z ZZZS.**

### Nova aplikacija za upravljanje

- Stalno delujoča storitev Docker s spletnim vmesnikom nadomešča posamezne zagone prek crona.
- Vsak prejemnik ima svoje prikazno ime, filtre po kraju, kategoriji in vrsti ambulante ter možnost začasne ustavitve ali odstranitve.
- Podprti so splošni in otroški zdravniki, ginekologi ter zobozdravniki, s predogledom zadetkov in pregledom delovanja.
- Enkratna vabila vključujejo poudarjeno povezavo, kopiranje in samodejni pomik do nje.
- Ob prijavi prejemnik takoj dobi celoten začetni seznam; neuspele dostave se ponovno poskušajo tudi po ponovnem zagonu.
- **Send now** pošlje trenutni seznam, **Send test notification** pa izmišljeni primer zelenega plusa in rdečega minusa.
- Obvestila se lahko pošiljajo samo ob spremembah ali kot dnevni povzetek; čas preverjanja je nastavljiv.

### Preglednejša obvestila

- Zeleni plus označuje dodane, rdeči minus pa odstranjene zdravnike.
- Vsak zdravnik ima večvrstični zapis; seznami so jasno razvrščeni po krajih, z oznako nadaljevanja pri daljših sporočilih.
- Ponavljajoči se podatek »Sprejema: DA« je odstranjen. Opozorilo za zdravnike, ki ne sprejemajo novih pacientov, ostane, kadar jih filtri vključujejo.
- Testna sporočila so jasno označena in ne spreminjajo dejanskih primerjalnih seznamov.

### Vmesnik in delovanje

- Sistemska, svetla ali temna tema s shranjeno izbiro v brskalniku.
- Medicinska ikona z Asklepijevo palico in vidna oznaka v2.0.
- Trajno shranjevanje v SQLite, osebni primerjalni seznami, ponovni poskusi dostave in nadomestni način prepoznavanja bota.
- Preverjanje dovoljenih naslovov IP in imen gostiteljev, zaščita pred spremembami z drugih spletnih mest ter zaščita žetonov pred razkritjem prek API-ja.
- Neprivilegiran proces, datotečni sistem samo za branje, preverjanje zdravja in samodejni ponovni zagon.
- Navodila za namestitev, prehod s stare skripte, varnostne kopije, obnovo in odpravljanje težav. Žetoni in podatki prejemnikov niso del objavljene kode.

### Združljivost in preverjanje

Privzeta storitev Compose je zdaj nova aplikacija. Stara skripta, Dockerfile in `docker-compose.legacy.yml` ostajajo na voljo. Žetone in prejemnike prenesite zasebno ter izključite stari urnik; zgodovina CSV se ne uvozi samodejno. Ob zagonu se odvisnosti namestijo iz PyPI, zato je potrebna omrežna povezava. Vmesnik nima ločene prijave in mora ostati v zaupanja vrednem lokalnem omrežju ali za tunelom SSH.

Uspešno je opravljenih 18 samodejnih testov. Preverjeni so bili tudi delovanje nameščene storitve, različica, ikona, povezava s Telegramom in registracija vira Compose v Dockhandu. Pregled izvorne kode in zgodovine Git ni našel dejanskih žetonov, identifikatorjev prejemnikov ali zasebnih podatkov o domačem okolju.

**[Navodila za namestitev](https://github.com/Vlayke/ZZZS/blob/main/docs/DEPLOYMENT.md)** · **[Hitri začetek](https://github.com/Vlayke/ZZZS#namestitev)**


## v1.0.0 — 2025-12-16

Prva javna izdaja skripte za filtriranje zdravnikov z Dockerjem in obvestili Telegram.

---

# English changelog

## Update after v2.0.0 — 2026-11-13

- Explicit Suspend / Resume actions in the subscriber list and edit window.
- Suspension preserves registration, alias, filters and history while holding automatic initial deliveries.
- Live eligibility is rechecked immediately before automatic sending.
- 21 tests include preservation, resumption and pending-initial suppression.

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
