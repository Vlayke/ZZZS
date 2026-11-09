"""LAN-only ZZZS subscriptions. One Gunicorn worker owns the scheduler/poller."""
import hashlib
import io
import ipaddress
import json
import os
import re
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from contextlib import contextmanager
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from flask import Flask, abort, jsonify, request, send_from_directory
from openpyxl import load_workbook

DATA = Path(os.environ.get('DATA_DIR', '/data'))
DATA.mkdir(parents=True, exist_ok=True)
TZ = ZoneInfo('Europe/Ljubljana')
PAGE = 'https://zavarovanec.zzzs.si/izbira-in-zamenjava-osebnega-zdravnika/seznami-zdravnikov/'
SOURCES = {'gp': 'pri splošnih zdravnikih', 'gynaecology': 'pri ginekologih', 'dentistry': 'pri zobozdravnikih'}
app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024
scan_lock = threading.Lock()
worker_seen = time.time()


@contextmanager
def db():
    c = sqlite3.connect(DATA / 'manager.sqlite', timeout=30)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    try:
        with c:
            yield c
    finally:
        c.close()


def initialize():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users(chat_id TEXT PRIMARY KEY,alias TEXT NOT NULL DEFAULT '',
          username TEXT NOT NULL DEFAULT '',enabled INTEGER NOT NULL DEFAULT 1,
          filters TEXT NOT NULL DEFAULT '{}',mode TEXT NOT NULL DEFAULT 'changes',
          baseline TEXT,last_sent TEXT,status TEXT NOT NULL DEFAULT 'Ready',initial_pending INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS invites(token TEXT PRIMARY KEY,expires REAL,alias TEXT,filters TEXT,used INTEGER DEFAULT 0,mode TEXT DEFAULT 'changes',enabled INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,at TEXT,kind TEXT,message TEXT);
        ''')
        if 'initial_pending' not in {r['name'] for r in c.execute('PRAGMA table_info(users)')}:
            c.execute('ALTER TABLE users ADD COLUMN initial_pending INTEGER NOT NULL DEFAULT 0')
        for k, v in {'hour': '09:00', 'last_check': '', 'last_success': '', 'last_error': '', 'offset': 0, 'next_retry': 0}.items():
            c.execute('INSERT OR IGNORE INTO settings VALUES(?,?)', (k, json.dumps(v)))
    # Only produced by the on-host migration; never part of source or API responses.
    bootstrap = DATA / 'bootstrap.json'
    if bootstrap.exists():
        b = json.loads(bootstrap.read_text())
        with db() as c:
            c.execute('INSERT OR IGNORE INTO settings VALUES(?,?)', ('bot_token', json.dumps(b['token'])))
            c.execute('INSERT OR IGNORE INTO settings VALUES(?,?)', ('bot_username', json.dumps(b['username'])))
            for uid in b['chat_ids']:
                c.execute('INSERT OR IGNORE INTO users(chat_id,alias,filters) VALUES(?,?,?)',
                          (str(uid), 'Existing subscriber ' + str(uid)[-4:], json.dumps(b['filters'])))
        bootstrap.unlink()


def setting(k, default=None):
    with db() as c:
        r = c.execute('SELECT value FROM settings WHERE key=?', (k,)).fetchone()
    return json.loads(r[0]) if r else default


def put(k, v):
    with db() as c:
        c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (k, json.dumps(v)))


def now():
    return datetime.now(TZ).isoformat(timespec='seconds')


def event(kind, message):
    with db() as c:
        c.execute('INSERT INTO events(at,kind,message) VALUES(?,?,?)', (now(), kind, message))
        c.execute('DELETE FROM events WHERE id < (SELECT COALESCE(MAX(id),0)-500 FROM events)')


def telegram(method, body=None, timeout=40, token=None):
    token = token or setting('bot_token', '')
    if not token:
        raise RuntimeError('Telegram bot is not configured')
    # Requests exceptions contain the token-bearing URL: never persist or log them.
    try:
        r = requests.post(f'https://api.telegram.org/bot{token}/{method}', json=body or {}, timeout=timeout)
        data = r.json()
    except Exception:
        raise RuntimeError('Telegram connection failed') from None
    if not data.get('ok'):
        raise RuntimeError('Telegram rejected request: ' + str(data.get('error_code', r.status_code)))
    return data['result']


def bot_identity(token=None):
    try:
        return telegram('getMe', timeout=8, token=token)
    except RuntimeError as e:
        if str(e).endswith((': 401', ': 404')):
            raise
        # Telegram can time out getMe for an otherwise functioning bot. The
        # bot's own chat provides its username without blocking update polling.
        bot_id = (token or setting('bot_token', '')).split(':')[0]
        return telegram('getChat', {'chat_id': bot_id}, timeout=12, token=token)


def send(chat_id, text):
    # Keep doctor blocks together; only split oversized blocks at line boundaries.
    blocks = []
    for block in text.split('\n\n'):
        while len(block) > 3500:
            cut = block.rfind('\n', 0, 3501)
            if cut <= 0:
                cut = 3500
            blocks.append(block[:cut])
            block = block[cut:].lstrip('\n')
        if block:
            blocks.append(block)
    part = ''
    location = None
    for block in blocks:
        heading = next((line for line in block.splitlines() if line.startswith('KRAJ: ')), None)
        if part and len(part) + len(block) + 2 > 3500:
            telegram('sendMessage', {'chat_id': chat_id, 'text': part})
            part = ''
            if not heading and location and block.startswith(('• ', '🟢 + ', '🔴 − ')):
                continuation = location + ' (nadaljevanje)\n'
                if len(continuation) + len(block) <= 3500:
                    block = continuation + block
        if heading:
            location = heading
        part += ('\n\n' if part else '') + block
    if part:
        telegram('sendMessage', {'chat_id': chat_id, 'text': part})


def parse_workbook(content, source):
    w = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    result = []
    date = ''
    try:
        for sheet in w:
            header = None
            for index, cells in enumerate(sheet.iter_rows(values_only=True)):
                vals = [str(x).strip() if x is not None else '' for x in cells]
                if header is None:
                    for raw, v in zip(cells, vals):
                        if isinstance(raw, datetime):
                            date = raw.strftime('%d.%m.%Y')
                        elif re.search(r'\b\d{1,2}\.\d{1,2}\.\d{4}\b', v):
                            try:
                                date = datetime.strptime(re.search(r'\b\d{1,2}\.\d{1,2}\.\d{4}\b', v)[0], '%d.%m.%Y').strftime('%d.%m.%Y')
                            except ValueError:
                                pass
                if header is None:
                    if 'Kraj' in vals and 'Priimek in ime zdravnika' in vals:
                        header = vals
                    continue
                row = dict(zip(header, vals))
                name = row.get('Priimek in ime zdravnika', '')
                if not name or not row.get('Kraj'):
                    continue
                accepting_key = next((k for k in header if 'še sprejema' in k), None)
                if not accepting_key:
                    raise RuntimeError('ZZZS accepting-patients column is missing')
                record = {'name': name, 'location': row['Kraj'], 'service': row.get('Naziv ZZZS dejavnosti', source),
                          'provider': row.get('Naziv izvajalca', ''), 'address': row.get('Ulica', ''),
                          'accepting': row[accepting_key].upper(), 'source': source}
                record['id'] = hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
                result.append(record)
    finally:
        w.close()
    if not result:
        raise RuntimeError('ZZZS spreadsheet contains no recognized doctors')
    return {'date': date or 'Unknown', 'doctors': result}


def download_data():
    r = requests.get(PAGE, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    collected, dates = [], {}
    for source, phrase in SOURCES.items():
        a = next((a for a in soup.find_all('a', href=True) if 'Število opredeljenih' in a.get_text() and phrase in a.get_text()), None)
        if not a:
            raise RuntimeError('ZZZS download link is missing: ' + source)
        url = urljoin(PAGE, a['href'])
        if urlparse(url).scheme != 'https' or urlparse(url).hostname not in {'partner.zzzs.si', 'zavarovanec.zzzs.si', 'www.zzzs.si'}:
            raise RuntimeError('Unexpected ZZZS download host')
        data = requests.get(url, timeout=90)
        data.raise_for_status()
        parsed = parse_workbook(data.content, source)
        collected.extend(parsed['doctors'])
        dates[source] = parsed['date']
    return {'fetched_at': now(), 'dates': dates, 'doctors': collected}


def cached():
    f = DATA / 'catalog.json'
    return json.loads(f.read_text()) if f.exists() else {'dates': {}, 'doctors': []}


def matching(rows, filters):
    return [r for r in rows
            if (not filters.get('locations') or r['location'] in filters['locations'])
            and (not filters.get('services') or r['service'] in filters['services'])
            and (not filters.get('sources') or r['source'] in filters['sources'])
            and (not filters.get('accepting_only', True) or r['accepting'] == 'DA')]


def doctor_list(rows, marker='•'):
    blocks = []
    location = None
    for r in sorted(rows, key=lambda r: (r['location'], r['name'], r['service'])):
        clean = lambda key: ' '.join(str(r.get(key, '')).split())
        heading = ''
        if r['location'] != location:
            location = r['location']
            heading = 'KRAJ: ' + clean('location') + '\n'
        details = [marker + ' ' + clean('name')]
        details.extend('   ' + clean(k) for k in ['service', 'provider', 'address'] if clean(k))
        if r.get('accepting') == 'NE':
            details.append('   ⚠ Trenutno ne sprejema novih pacientov.')
        elif r.get('accepting') not in ('DA', '', None):
            details.append('   Sprejemanje novih pacientov: ' + clean('accepting'))
        blocks.append(heading + '\n'.join(details))
    return '\n\n'.join(blocks)


def message_footer(data):
    return '📅 Podatki ZZZS: ' + ', '.join(sorted(set(data['dates'].values()))) + '\n/stop za odjavo · /status za stanje'


def full_list_message(rows, data, enabled=True, initial=False):
    lines = ['✅ Prijava na ZZZS obvestila je uspela.\n\n📋 ZZZS · Celoten seznam' if initial else '📋 ZZZS · Celoten seznam',
             f'{"Začetni seznam" if initial else "Trenutni seznam"}: {len(rows)} zdravnikov ustreza vašim filtrom.']
    if rows:
        lines.append('Zdravniki so združeni po krajih.')
        lines.append('\n' + doctor_list(rows))
    else:
        lines.append('Trenutno ni zdravnikov, ki bi ustrezali vašim filtrom.')
    if not enabled:
        lines.append('Nadaljnja obvestila so začasno ustavljena.')
    lines.append('\n' + message_footer(data))
    return '\n'.join(lines)


def deliver_initial(uid):
    with db() as c:
        u = c.execute('SELECT * FROM users WHERE chat_id=? AND initial_pending=1', (uid,)).fetchone()
    if not u:
        return
    data = cached()
    if not data.get('fetched_at'):
        return  # Keep the durable request until the first successful download.
    rows = sorted(matching(data['doctors'], json.loads(u['filters'])),
                  key=lambda r: (r['location'], r['name'], r['service']))
    try:
        send(uid, full_list_message(rows, data, u['enabled'], initial=True))
    except RuntimeError as e:
        with db() as c:
            c.execute('UPDATE users SET status=? WHERE chat_id=? AND initial_pending=1', (str(e), uid))
        return  # Retry after failure or restart without requiring another invite.
    with db() as c:
        c.execute('UPDATE users SET initial_pending=0,baseline=?,last_sent=?,status=? WHERE chat_id=? AND filters=? AND initial_pending=1',
                  (json.dumps({r['id']: r for r in rows}), now(), f'{len(rows)} matching doctors', uid, u['filters']))


def check(notify=True):
    if not scan_lock.acquire(False):
        return False
    try:
        put('last_check', now())
        data = download_data()
        tmp = DATA / 'catalog.tmp'
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')
        tmp.replace(DATA / 'catalog.json')
        with db() as c:
            users = [dict(x) for x in c.execute('SELECT * FROM users WHERE enabled=1 AND initial_pending=0')]
        errors = 0
        for u in users:
            rows = matching(data['doctors'], json.loads(u['filters']))
            current = {r['id']: r for r in rows}
            old = json.loads(u['baseline']) if u['baseline'] else None
            added = set(current) - set(old or {})
            removed = set(old or {}) - set(current)
            # First scan/filter edit establishes a baseline without surprise alerts.
            daily_due = u['mode'] == 'daily' and not (u['last_sent'] or '').startswith(datetime.now(TZ).date().isoformat())
            due = old is not None and (daily_due or added or removed)
            status = f'{len(rows)} matching doctors'
            if due and notify:
                lines = ['🔔 ZZZS · Spremembe zdravnikov', datetime.now(TZ).strftime('%d.%m.%Y'), f'Ustreznih zdravnikov: {len(rows)}']
                for label, marker, ids, records in [('🟢 Dodani', '🟢 +', added, current), ('🔴 Odstranjeni', '🔴 −', removed, old or {})]:
                    if ids:
                        lines.append(f'\n{label}: {len(ids)}')
                        lines.append(doctor_list([records[k] for k in ids], marker))
                if not added and not removed:
                    lines.append('\n✓ Ni sprememb v vašem izboru.')
                lines.append('\n' + message_footer(data))
                try:
                    send(u['chat_id'], '\n'.join(lines))
                    with db() as c:
                        c.execute('UPDATE users SET last_sent=? WHERE chat_id=?', (now(), u['chat_id']))
                except RuntimeError as e:
                    errors += 1
                    with db() as c:
                        c.execute('UPDATE users SET status=? WHERE chat_id=?', (str(e), u['chat_id']))
                    continue  # Preserve baseline so a failed delivery is retried.
            if notify or old is None:
                with db() as c:
                    # Do not overwrite a concurrently edited subscription's new baseline.
                    c.execute('UPDATE users SET baseline=?,status=? WHERE chat_id=? AND filters=? AND enabled=1',
                              (json.dumps(current), status, u['chat_id'], u['filters']))
        put('last_success', now())
        put('last_error', f'{errors} Telegram deliveries failed' if errors else '')
        if notify and not errors:
            put('last_scheduled_day', datetime.now(TZ).date().isoformat())
        event('check', f'Loaded {len(data["doctors"])} doctors; {errors} delivery failures')
        return True
    except Exception as e:
        message = str(e) if isinstance(e, RuntimeError) else 'ZZZS download or parsing failed (' + type(e).__name__ + ')'
        put('last_error', message)
        event('error', message)
        return False
    finally:
        scan_lock.release()


def validate_filters(f):
    if not isinstance(f, dict):
        abort(400, 'Filters must be an object')
    out = {}
    for k in ['locations', 'services', 'sources']:
        v = f.get(k, [])
        if not isinstance(v, list) or len(v) > 1000 or any(not isinstance(s, str) or len(s) > 250 for s in v):
            abort(400, 'Invalid ' + k)
        out[k] = sorted(set(v))
    if any(s not in SOURCES for s in out['sources']):
        abort(400, 'Unknown doctor category')
    out['accepting_only'] = bool(f.get('accepting_only', True))
    return out


def handle_update(update):
    m = update.get('message', {})
    if m.get('chat', {}).get('type') != 'private':
        return
    uid = str(m['chat']['id'])
    text = m.get('text', '').strip()
    if text == '/stop':
        with db() as c:
            c.execute('DELETE FROM users WHERE chat_id=?', (uid,))
        send(uid, 'Odjavljeni ste iz ZZZS obvestil. Za ponovno prijavo prosite skrbnika za novo povezavo.')
    elif text.startswith('/start '):
        token = text.split(maxsplit=1)[1]
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            inv = c.execute('SELECT * FROM invites WHERE token=? AND used=0 AND expires>?', (token, time.time())).fetchone()
            if not inv:
                return
            c.execute("INSERT INTO users(chat_id,alias,username,filters,mode,enabled,initial_pending,status) VALUES(?,?,?,?,?,?,1,'Initial list pending') ON CONFLICT(chat_id) DO UPDATE SET alias=excluded.alias,username=excluded.username,filters=excluded.filters,mode=excluded.mode,enabled=excluded.enabled,baseline=NULL,initial_pending=1,status='Initial list pending'",
                      (uid, inv['alias'] or m.get('from', {}).get('first_name', ''), m.get('from', {}).get('username', ''), inv['filters'], inv['mode'], inv['enabled']))
            c.execute('UPDATE invites SET used=1 WHERE token=?', (token,))
        event('registration', 'A subscriber joined using an invitation')
        deliver_initial(uid)
    elif text == '/status':
        with db() as c:
            u = c.execute('SELECT enabled,status FROM users WHERE chat_id=?', (uid,)).fetchone()
        if u:
            send(uid, ('Obvestila aktivna. ' if u['enabled'] else 'Obvestila začasno ustavljena. ') + u['status'])


def worker():
    global worker_seen
    retry_at = 0
    initial_retry_at = 0
    while True:
        worker_seen = time.time()
        try:
            local = datetime.now(TZ)
            due = local.strftime('%H:%M') >= setting('hour', '09:00') and setting('last_scheduled_day', '') != local.date().isoformat()
            if (not (DATA / 'catalog.json').exists() or due) and time.time() > retry_at:
                check()
                retry_at = time.time() + 1800
            if time.time() >= initial_retry_at:
                initial_retry_at = time.time() + 60
                with db() as c:
                    pending = [r['chat_id'] for r in c.execute('SELECT chat_id FROM users WHERE initial_pending=1')]
                for uid in pending:
                    deliver_initial(uid)
            if setting('bot_token'):
                if not setting('bot_username'):
                    me = bot_identity()
                    put('bot_username', me['username'])
                updates = telegram('getUpdates', {'offset': setting('offset', 0), 'timeout': 20, 'allowed_updates': ['message']})
                for update in updates:
                    try:
                        handle_update(update)
                    except RuntimeError as e:
                        event('telegram', str(e))
                    put('offset', update['update_id'] + 1)
                put('poll_error', '')
            else:
                time.sleep(10)
        except Exception as e:
            put('poll_error', str(e) if isinstance(e, RuntimeError) else type(e).__name__)
            time.sleep(15)


@app.before_request
def local_only():
    try:
        ip = ipaddress.ip_address(request.remote_addr)
        networks = os.environ.get('ALLOWED_NETWORKS', '127.0.0.0/8').split(',')
        if not any(ip in ipaddress.ip_network(n) for n in networks):
            abort(403)
    except ValueError:
        abort(403)
    host = request.host.split(':')[0].lower()
    if host not in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(','):
        abort(403)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        if request.headers.get('X-ZZZS-Request') != '1':
            abort(403)
        if request.headers.get('Origin') and request.headers['Origin'] != request.host_url.rstrip('/'):
            abort(403)


@app.after_request
def security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(409)
@app.errorhandler(502)
def error(e):
    return jsonify(error=e.description), e.code


@app.get('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.get('/health')
def health():
    alive = os.environ.get('NO_WORKER') == '1' or time.time() - worker_seen < 300
    return jsonify(status='ok' if alive else 'worker stalled'), 200 if alive else 503


@app.get('/api/state')
def state():
    data = cached()
    with db() as c:
        users = []
        for r in c.execute('SELECT * FROM users ORDER BY alias,chat_id'):
            u = dict(r)
            u['filters'] = json.loads(u['filters'])
            u['matches'] = len(matching(data['doctors'], u['filters']))
            u.pop('baseline')
            users.append(u)
        events = [dict(x) for x in c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 20')]
    keys = ['hour', 'last_check', 'last_success', 'last_error', 'poll_error', 'bot_username']
    return jsonify(users=users, events=events, settings={k: setting(k, '') for k in keys},
                   bot_configured=bool(setting('bot_token')), checking=scan_lock.locked(), dates=data['dates'],
                   catalog={'locations': sorted(set(r['location'] for r in data['doctors'])),
                            'services': sorted(set(r['service'] for r in data['doctors'])), 'total': len(data['doctors'])})


@app.post('/api/users')
def save_user():
    b = request.get_json()
    uid = str(b.get('chat_id', '')).strip()
    if not uid.lstrip('-').isdigit() or len(uid) > 20:
        abort(400, 'Enter a valid numeric Telegram chat ID')
    alias = str(b.get('alias', '')).strip()[:120]
    filters = json.dumps(validate_filters(b.get('filters', {})))
    mode = b.get('mode', 'changes')
    if mode not in ['daily', 'changes']:
        abort(400, 'Unknown notification mode')
    with db() as c:
        c.execute('''INSERT INTO users(chat_id,alias,filters,mode,enabled) VALUES(?,?,?,?,?)
          ON CONFLICT(chat_id) DO UPDATE SET alias=excluded.alias,filters=excluded.filters,mode=excluded.mode,
          enabled=excluded.enabled,baseline=CASE WHEN users.filters!=excluded.filters THEN NULL ELSE users.baseline END''',
                  (uid, alias, filters, mode, int(bool(b.get('enabled', True)))))
    return jsonify(ok=True)


@app.delete('/api/users/<uid>')
def delete_user(uid):
    with db() as c:
        c.execute('DELETE FROM users WHERE chat_id=?', (uid,))
    return jsonify(ok=True)


@app.post('/api/users/<uid>/send')
def send_now(uid):
    if not scan_lock.acquire(False):
        abort(409, 'A data check or delivery is running. Please try again shortly.')
    try:
        with db() as c:
            u = c.execute('SELECT * FROM users WHERE chat_id=?', (uid,)).fetchone()
        if not u:
            abort(404, 'Subscriber not found')
        data = cached()
        if not data.get('fetched_at'):
            abort(409, 'No doctor data is available yet. Refresh data first.')
        rows = sorted(matching(data['doctors'], json.loads(u['filters'])),
                      key=lambda r: (r['location'], r['name'], r['service']))
        try:
            send(uid, full_list_message(rows, data, u['enabled']))
        except RuntimeError as e:
            with db() as c:
                c.execute('UPDATE users SET status=? WHERE chat_id=?', (str(e), uid))
            abort(502, str(e))
        with db() as c:
            c.execute('UPDATE users SET initial_pending=0,baseline=?,last_sent=?,status=? WHERE chat_id=? AND filters=?',
                      (json.dumps({r['id']: r for r in rows}), now(), f'{len(rows)} matching doctors', uid, u['filters']))
        event('delivery', f'Manual list delivered: {len(rows)} matching doctors')
        return jsonify(ok=True, count=len(rows))
    finally:
        scan_lock.release()


@app.post('/api/invites')
def invite():
    username = setting('bot_username')
    if not username:
        abort(400, 'Configure and verify the Telegram bot first')
    b = request.get_json()
    token = secrets.token_urlsafe(24)
    with db() as c:
        c.execute('DELETE FROM invites WHERE expires<? OR used=1', (time.time(),))
        mode = b.get('mode', 'changes')
        if mode not in ('changes', 'daily'):
            abort(400, 'Unknown notification mode')
        c.execute('INSERT INTO invites(token,expires,alias,filters,mode,enabled) VALUES(?,?,?,?,?,?)',
                  (token, time.time() + 86400, str(b.get('alias', ''))[:120], json.dumps(validate_filters(b.get('filters', {}))), mode, int(bool(b.get('enabled', True)))))
    return jsonify(url=f'https://t.me/{username}?start={token}', expires='24 hours; one use')


@app.post('/api/settings')
def settings():
    b = request.get_json()
    hour = b.get('hour', setting('hour'))
    try:
        datetime.strptime(hour, '%H:%M')
    except (ValueError, TypeError):
        abort(400, 'Use HH:MM for the daily check time')
    warning = None
    if b.get('bot_token'):
        token = str(b['bot_token']).strip()
        if len(token) > 200 or not re.fullmatch(r'\d{5,16}:[A-Za-z0-9_-]{30,}', token):
            abort(400, 'Invalid bot token')
        verified = None
        try:
            verified = bot_identity(token)
        except RuntimeError as e:
            if str(e).endswith((': 401', ': 404')):
                abort(400, 'Telegram rejected this bot token')
        put('bot_token', token)
        put('bot_username', verified['username'] if verified else '')
        warning = None if verified else 'Token saved. Telegram verification is pending; the service will keep retrying.'
        put('poll_error', '' if verified else 'Token saved; Telegram verification pending')
    put('hour', hour)
    return jsonify(ok=True, warning=warning)


@app.post('/api/check')
def manual_check():
    # Refresh-only intentionally sends no notifications.
    if scan_lock.locked():
        abort(409, 'A refresh is already running')
    threading.Thread(target=check, kwargs={'notify': False}, daemon=True).start()
    return jsonify(ok=True), 202


@app.post('/api/preview')
def preview():
    filters = validate_filters(request.get_json().get('filters', {}))
    rows = matching(cached()['doctors'], filters)
    return jsonify(count=len(rows), doctors=rows[:100])


initialize()
if os.environ.get('NO_WORKER') != '1':
    threading.Thread(target=worker, daemon=True).start()
