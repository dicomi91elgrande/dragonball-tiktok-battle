"""
Servidor puente entre TikFinity/Interactive y el overlay de Dragon Ball.

  TikFinity (regalo/chat) --POST--> /webhook --SSE--> overlay en OBS

- Sirve el overlay (index.html) en  http://localhost:3000/
- Recibe los eventos de TikFinity por POST en  /webhook
- Los reenvía al overlay en tiempo real por SSE (Server-Sent Events)

No necesita instalar nada: solo la librería estándar de Python.
Arrancar con:   python server.py
"""

import json
import os
import queue
import re
import threading
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote
from urllib.request import Request, urlopen

PORT = int(os.environ.get('PORT', 3000))   # el hosting (Render, etc.) asigna el puerto por env
HOOK_TOKEN = os.environ.get('HOOK_TOKEN')  # opcional: si se define, /webhook exige ?token=...
BASE = os.path.dirname(os.path.abspath(__file__))

# Lista de clientes SSE conectados (cada overlay abierto = una cola)
clients = []
clients_lock = threading.Lock()

# Personajes elegibles desde el chat. Cada entrada: nombre canónico y alias frecuentes.
# El overlay decide los detalles (transformaciones, sprites); aquí solo reconocemos el nombre.
CHARACTERS = {
    'Goku': ['kakaroto', 'kakarot', 'son goku'],
    'Black Goku': ['goku black', 'black goku', 'gokublack'],
    'Vegeta': ['begeta', 'principe vegeta'],
    'Gohan': ['son gohan', 'gohan bestia', 'beast gohan'],
    'Goten': [],
    'Trunks del futuro': ['trunks', 'future trunks'],
    'Trunks niño': ['trunks nino', 'kid trunks', 'trunks pequeno'],
    'Piccolo': ['picolo'],
    'Krilin': ['krillin', 'kuririn'],
    'Ten Shin Han': ['tenshinhan', 'tien', 'ten'],
    'Yamcha': [],
    'Bardock': ['bardok'],
    'Broly': ['broli'],
    'Vegito': ['vegetto', 'vegetto blue'],
    'Gogeta': ['gogeta blue'],
    'Gotenks': [],
    'Freezer': ['frieza', 'freeza', 'golden freezer', 'freezer dorado'],
    'Cell': ['celula', 'cell perfecto', 'perfect cell'],
    'Majin Buu': ['buu', 'majinbuu', 'kid buu', 'super buu'],
    'Beerus': ['bills', 'birus'],
    'Whis': ['wiss'],
    'Jiren': [],
    'Hit': [],
    'Cooler': ['coola', 'cooler metal'],
    'Androide 17': ['android 17', 'a17', '17'],
    'Androide 18': ['android 18', 'a18', '18'],
    'Androide 19': ['android 19', 'a19', '19'],
    'Androide 16': ['android 16', 'a16', '16'],
    'Dr. Gero': ['doctor gero', 'dr gero', 'gero', 'androide 20', 'android 20', 'a20', '20'],
    'Raditz': ['radix', 'radditz'],
    'Nappa': ['napa'],
    'Chaoz': ['chaos', 'chiaotzu', 'chaozu'],
    'Yajirobe': ['yajirobe'],
    'Tao Pai Pai': ['taopaipai', 'tao pai pai', 'tao'],
    'Maestro Roshi': ['roshi', 'mutenroshi', 'muten roshi'],
    'Bulma': [],
    'Chichi': ['chi chi', 'chi-chi'],
    'Shin': ['kaioshin', 'kaio shin', 'supreme kai'],
    'Mr. Popo': ['mr popo', 'mister popo', 'popo'],
    'Dende': [],
    'Videl': [],
    'Pan': [],
    'Caulifla': ['kaulifla'],
    'Kale': [],
    'Kefla': [],
    'Zamasu': ['zamas'],
    'Black': [],
    'Mr. Satan': ['satan', 'hercule'],
    'Dabra': ['dabura'],
    'Babidi': [],
    'Spopovic': ['spopovich', 'spopovitch'],
    'Oolong': ['oolon', 'oolong'],
    'Puar': ['puar'],
    'Dodoria': ['dodoria'],
    'Ginyu': ['capitan ginyu', 'captain ginyu', 'guinyu'],
    'Reecome': ['recoome', 'rikum', 'recoom'],
    'Janemba': ['yanemba'],
    'Turles': ['tullece', 'turlex'],
}


def slug(text):
    text = (text or '').strip().lower().replace('♀', 'f').replace('♂', 'm')
    text = unicodedata.normalize('NFD', text)
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
    text = re.sub(r"[.'’\-\s]", '', text)
    return re.sub(r'[^a-z0-9]', '', text)


# Índice plano: cada slug (nombre o alias) -> nombre canónico
ROSTER = []
for canonical, aliases in CHARACTERS.items():
    ROSTER.append({'name': canonical, 'slug': slug(canonical)})
    for al in aliases:
        ROSTER.append({'name': canonical, 'slug': slug(al)})


def log(*args):
    print(*args, flush=True)


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def fuzzy_limit(text):
    return 2 if len(text) >= 8 else 1


def find_char(text):
    base = slug(text)
    if not base:
        return None
    candidates = [base]
    for word in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ.'’-]+", text or ''):
        word_slug = slug(word)
        if word_slug and word_slug not in candidates:
            candidates.append(word_slug)
    for query in candidates:
        exact = next((c for c in ROSTER if c['slug'] == query), None)
        if exact:
            return exact['name']
    for query in candidates:
        if len(query) >= 4:
            partial = next((c for c in ROSTER if c['slug'].startswith(query) or query in c['slug'] or c['slug'] in query), None)
            if partial:
                return partial['name']
    best = None
    for query in candidates:
        for c in ROSTER:
            dist = edit_distance(query, c['slug'])
            if dist <= fuzzy_limit(query) and (best is None or dist < best['dist']):
                best = {'name': c['name'], 'dist': dist}
    return best['name'] if best else None


def command_char(text):
    """Reconoce comandos tipo !Goku, !MRPOPO o !Yancha dentro del comentario."""
    m = re.search(r'!(\S+)', text or '')
    if not m:
        return None
    return find_char(m.group(1))


def normalize_avatar_url(value):
    url = str(value or '').strip()
    if not url or '{' in url:
        return ''
    for _ in range(2):
        decoded = unquote(url)
        if decoded == url:
            break
        url = decoded
    return url


def broadcast(obj):
    """Envía un evento (dict) a todos los overlays conectados."""
    data = json.dumps(obj, ensure_ascii=False)
    with clients_lock:
        for q in list(clients):
            q.put(data)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # silencioso

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    # ---- CORS preflight ----
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    # ---- GET: overlay, SSE y estáticos ----
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ('/', '/index.html'):
            self.serve_file('index.html', 'text/html; charset=utf-8')
        elif path == '/events':
            self.handle_sse()
        elif path == '/health':
            self.send_json({'ok': True, 'clients': len(clients)})
        elif path == '/avatar':
            self.serve_avatar()
        else:
            self.serve_file(path.lstrip('/'), None)

    def serve_avatar(self):
        qs = parse_qs(urlparse(self.path).query)
        url = (qs.get('u', [''])[0] or '').strip()
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'bad avatar url')
            return
        try:
            req = Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Referer': 'https://www.tiktok.com/',
            })
            with urlopen(req, timeout=8) as resp:
                body = resp.read(3 * 1024 * 1024 + 1)
                if len(body) > 3 * 1024 * 1024:
                    raise ValueError('avatar too large')
                ctype = resp.headers.get('Content-Type', 'image/jpeg').split(';', 1)[0]
                if not ctype.startswith('image/'):
                    ctype = 'image/jpeg'
        except Exception as exc:
            print('avatar proxy error:', exc)
            self.send_response(502)
            self.end_headers()
            self.wfile.write(b'avatar load failed')
            return
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'public, max-age=3600')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, rel, ctype):
        fp = os.path.normpath(os.path.join(BASE, rel))
        if not fp.startswith(BASE) or not os.path.isfile(fp):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404')
            return
        if ctype is None:
            ctype = 'text/html; charset=utf-8' if rel.endswith('.html') \
                else 'application/javascript' if rel.endswith('.js') \
                else 'text/css' if rel.endswith('.css') \
                else 'image/png' if rel.endswith('.png') \
                else 'image/jpeg' if rel.endswith(('.jpg', '.jpeg')) \
                else 'image/gif' if rel.endswith('.gif') \
                else 'image/webp' if rel.endswith('.webp') \
                else 'audio/mpeg' if rel.endswith('.mp3') \
                else 'application/octet-stream'
        with open(fp, 'rb') as f:
            body = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_sse(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self._cors()
        self.end_headers()
        q = queue.Queue()
        with clients_lock:
            clients.append(q)
        try:
            self.wfile.write(b': conectado\n\n')
            self.wfile.flush()
            while True:
                try:
                    data = q.get(timeout=15)
                    self.wfile.write(('data: ' + data + '\n\n').encode('utf-8'))
                except queue.Empty:
                    self.wfile.write(b': ping\n\n')  # keepalive
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with clients_lock:
                if q in clients:
                    clients.remove(q)

    # ---- POST: eventos de TikFinity ----
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != '/webhook':
            self.send_response(404)
            self.end_headers()
            return
        # token opcional: solo se exige si HOOK_TOKEN está definido
        if HOOK_TOKEN:
            token = parse_qs(parsed.query).get('token', [''])[0]
            if token != HOOK_TOKEN:
                self.send_response(403)
                self._cors()
                self.end_headers()
                self.wfile.write(b'{"ok":false,"error":"token"}')
                return
        length = int(self.headers.get('Content-Length', '0') or 0)
        raw = self.rfile.read(length) if length else b''
        try:
            obj = json.loads(raw.decode('utf-8')) if raw else {}
        except Exception:
            obj = {'event': 'raw', 'raw': raw.decode('utf-8', 'replace')}
        if not isinstance(obj, dict):
            obj = {'event': 'raw', 'raw': obj}
        # Reconoce el personaje escrito en el chat. Acepta "Goku" y tambien comandos tipo "!Goku".
        text = obj.get('comment') or obj.get('message') or obj.get('text') or obj.get('content') or ''
        matched = command_char(text) or find_char(text)
        if matched:
            obj['character'] = matched
        avatar = normalize_avatar_url(obj.get('imgprofile') or obj.get('img') or obj.get('avatar') or obj.get('avatarUrl') or obj.get('profileImage') or obj.get('profilePicture') or obj.get('profilePictureUrl') or '')
        if avatar:
            obj['imgprofile'] = avatar
        broadcast(obj)
        log('webhook:', {
            'event': obj.get('event'),
            'username': obj.get('username') or obj.get('user'),
            'nickname': obj.get('nickname'),
            'imgprofile': avatar if avatar and '{' not in str(avatar) else None,
            'comment': obj.get('comment') or obj.get('message') or obj.get('text') or obj.get('content'),
            'character': obj.get('character'),
            'coins': obj.get('coins'),
            'giftname': obj.get('giftname') or obj.get('giftName'),
            'repeatcount': obj.get('repeatcount'),
        })
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    log('=' * 56)
    log(' Dragon Ball TikTok Battle - servidor puente')
    log(f' Overlay para OBS : http://localhost:{PORT}/')
    log(f' URL del WebHook  : http://localhost:{PORT}/webhook')
    log('=' * 56)
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
