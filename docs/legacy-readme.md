# ZZZS – obvestila o prostih osebnih zdravnikih (Telegram)
# ZZZS – notifications about available doctors (Telegram)

🇸🇮 **Slovenska različica je na začetku.**  
🇬🇧 **English version is available at the end of this document.**

---

## Kaj je to?

Ta projekt pomaga spremljati, **kateri osebni zdravniki trenutno sprejemajo nove paciente**, na podlagi **javnih podatkov ZZZS**.

Namesto vsakodnevnega ročnega preverjanja spletne strani ZZZS orodje:
- samodejno prenese najnovejšo Excel datoteko
- filtrira zdravnike glede na izbrane kriterije
- shrani rezultate (CSV)
- pošlje **Telegram obvestilo**, ko pride do sprememb

Projekt je nastal iz praktične potrebe in je pomagal tudi avtorju do stalnega osebnega zdravnika.

Projekt **ni povezan z ZZZS** in uporablja izključno **javno dostopne podatke**.

Upam, da vam projekt pomaga lažje priti do osebnega zdravnika zase ali svoje bližnje.

---

## Vir podatkov (ZZZS)

Uradna spletna stran ZZZS (javno dostopno):

https://zavarovanec.zzzs.si/izbira-in-zamenjava-osebnega-zdravnika/seznami-zdravnikov/

Na tej strani ZZZS objavlja **Excel datoteko**, ki se spreminja dnevno in vsebuje:
- seznam zdravnikov
- kraje in naslove ambulant
- vrste zdravstvenih dejavnosti
- podatek, ali zdravnik sprejema nove paciente

Datoteko lahko vsakdo:
- ročno prenese
- odpre v Excelu ali LibreOffice
- pregleda brez prijave

Skripta zgolj **avtomatizira postopek**, ki bi ga sicer izvajali ročno.

---

## Hitri začetek – nastavitev in zagon

### Kaj potrebujete
- Idealno, napravo, ki je stalno prižgana (Windows, macOS ali Linux) ali NAS/strežnik
- Docker in Docker Compose
- Telegram račun
- Telegram bota in Chat ID

---

### 1) Ustvarjanje Telegram bota

1. Odprite Telegram
2. Poiščite **BotFather**
3. Pošljite `/start`
4. Nato pošljite `/newbot`
5. Izberite ime in uporabniško ime (mora se končati z `bot`)
6. BotFather vam bo dal **BOT TOKEN**

---

### 2) Pridobitev Chat ID

**Najlažje – osebni chat**
1. V Telegramu poiščite `@userinfobot`
2. Start
3. Bot izpiše vaš numerični ID

**Skupina**
- dodajte svojega bota v skupino
- pošljite vsaj eno sporočilo
- s pomočjo `@userinfobot` pridobite group chat ID (običajno se začne z `-`)

---

### 3) Prenos projekta

Če uporabljate Git:
- klonirajte repozitorij
- premaknite se v mapo projekta

Če Git ne uporabljate:
- na GitHub strani kliknite **Code → Download ZIP**
- razširite ZIP datoteko
- odprite mapo projekta

---

### 4) Nastavitev `.env`

V mapi projekta je datoteka `.env.legacy.example`.

1. Naredite kopijo in jo preimenujte v `.env`
2. Odprite `.env` in vnesite:

TELEGRAM_BOT_TOKEN=VAŠ_TOKEN  
TELEGRAM_CHAT_ID=VAŠ_CHAT_ID  

---

### 5) Prilagoditev filtrov (po želji)

Odprite `filter_doctors.py` in poiščite:
- `LOCATION_FILTER` → stolpec **Kraj**
- `SERVICE_FILTER` → stolpec **Naziv ZZZS dejavnosti**
- `ACCEPTING_NEW_VALUE` → stolpec **Zdravnik še sprejema zavarovane osebe**

Priporočeno je, da Excel datoteko najprej **ročno prenesete** in vrednosti **kopirate neposredno iz nje**.

---

### 6) Zagon (Docker Compose – priporočeno)

Prvi zagon v mapi projekta:

docker compose up --build

Pričakovano:
- skripta se zažene enkrat
- pošlje Telegram obvestilo (če je nastavljen)
- ustvari CSV datoteke

---

### Shranjevanje CSV zgodovine (zelo pomembno)

⚠️ Za primerjavo “danes proti včeraj” morajo CSV datoteke ostati shranjene med zagoni.

Priporočena nastavitev v `docker-compose.yml`:

services:
  zzzs-gp-alert:
    build: .
    env_file:
      - .env
    volumes:
      - /location/of/csv/files:/app

---

## Samodejni dnevni zagon

### Linux / NAS (cron)

Primer: vsak dan ob 08:00

0 8 * * * cd /pot/do/projekta && docker compose run --rm zzzs-gp-alert

---

### Windows (Task Scheduler)

- Program: `docker`
- Arguments: `compose run --rm zzzs-gp-alert`
- Start in: mapa projekta (obvezno)

---

## Excel datoteka – uporabljeni stolpci

Skripta uporablja naslednje stolpce:
- **Kraj**
- **Naziv ZZZS dejavnosti**
- **Zdravnik še sprejema zavarovane osebe**
- Priimek in ime zdravnika
- Naziv izvajalca
- Ulica

Filtriranje temelji na **natančnem ujemanju besedila**.

---

## Filtriranje – pomembne opombe

ZZZS uporablja **specifična poimenovanja dejavnosti**. Ne ugibajte imen.

Primer dejanske vrednosti za zdravnike za otroke:
- Splošna dej.-otroški in šolski dispanzer

Vedno kopirajte vrednosti neposredno iz Excel datoteke.

---

## Pogoste težave

- Telegram obvestila ne delujejo → preverite bot token, chat ID in ali ste bota zagnali
- Vedno piše “Ni sprememb” → preverite, da se CSV datoteke shranjujejo med zagoni
- Skripta ne najde Excel povezave → ZZZS je spremenil tekst na strani

---

## Licenca

MIT License – uporaba, spreminjanje in deljenje je dovoljeno ob ohranitvi navedbe avtorja.

---

# English version

## What is this?

This project monitors **which doctors are currently accepting new patients** using **public ZZZS data**.

It automatically:
- downloads the daily ZZZS Excel file
- filters doctors by location and service type
- stores daily CSV results
- sends Telegram notifications when changes occur

Official data source:
https://zavarovanec.zzzs.si/izbira-in-zamenjava-osebnega-zdravnika/seznami-zdravnikov/

---

## Quick start (setup & run)

### Requirements
- computer/server/NAS
- Docker + Docker Compose
- Telegram account
- Telegram bot token and chat ID

### Setup summary
1. Create a Telegram bot using BotFather
2. Obtain your chat ID
3. Download or clone this repository
4. Copy `.env.legacy.example` to `.env` and fill in credentials
5. (Optional) Adjust filters in `filter_doctors.py`
6. Run `docker compose up --build`

### Scheduling
Run once per day using cron (Linux/NAS) or Task Scheduler (Windows):

docker compose run --rm zzzs-gp-alert

---

## License

MIT License – reuse, modification and redistribution are allowed with attribution.
