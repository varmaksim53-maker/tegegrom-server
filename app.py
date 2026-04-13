import sqlite3, uvicorn, hashlib, base64, os
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from datetime import datetime

app = FastAPI()
DB = 'tegegrom_v30_elite.db'

# --- Инициализация БД ---
def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE, password TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            sender TEXT, receiver TEXT, content TEXT, 
            timestamp TEXT, type TEXT DEFAULT 'text', file TEXT DEFAULT '')''')
        conn.commit()

init_db()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

@app.get("/sw.js", response_class=PlainTextResponse)
async def get_sw():
    return """
    self.addEventListener('install', (e) => self.skipWaiting());
    self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
    self.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'PUSH') {
            self.registration.showNotification(event.data.title, {
                body: event.data.body,
                icon: 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Telegram_logo.svg/2048px-Telegram_logo.svg.png',
                vibrate: [200, 100, 200]
            });
        }
    });
    """

@app.get("/", response_class=HTMLResponse)
async def index(): return UI

@app.post("/api/auth")
async def auth(d: dict):
    u, p = d.get('u'), hash_pass(d.get('p'))
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE username = ?", (u,)).fetchone()
        if user:
            if user['password'] == p: return {"ok": True, "user": u}
            else: return {"ok": False, "msg": "Неверный пароль"}
        else:
            conn.execute("INSERT INTO users (username, password) VALUES (?,?)", (u, p))
            conn.commit()
            return {"ok": True, "user": u}

@app.get("/api/get_users")
async def get_users():
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        return [r['username'] for r in conn.execute("SELECT username FROM users").fetchall()]

@app.get("/api/get/{me}/{to}")
async def get_msgs(me: str, to: str, last: int = 0):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        if to == "all":
            q = "SELECT * FROM messages WHERE receiver='all' AND id > ? ORDER BY id ASC"
            params = (last,)
        else:
            q = "SELECT * FROM messages WHERE ((sender=? AND receiver=?) OR (sender=? AND receiver=?)) AND id > ? ORDER BY id ASC"
            params = (me, to, to, me, last)
        return [dict(r) for r in conn.execute(q, params).fetchall()]

@app.post("/api/send")
async def send_msg(d: dict):
    with sqlite3.connect(DB) as conn:
        t = datetime.now().strftime("%H:%M")
        conn.execute("INSERT INTO messages (sender, receiver, content, timestamp, type, file) VALUES (?,?,?,?,?,?)",
                     (d['s'], d['r'], d['c'], t, d['t'], d.get('f', '')))
        conn.commit()
    return {"ok": True}

UI = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover, maximum-scale=1.0, user-scalable=0">
    
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="TegeGrom">
    <link rel="apple-touch-icon" href="https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Telegram_logo.svg/2048px-Telegram_logo.svg.png">
    
    <title>TegeGrom</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { 
            --bg: #0e1621; --side: #17212b; --blue: #2481cc; --txt: #ffffff; 
            --in: #182533; --out: #2b5278; --glass: rgba(23, 33, 43, 0.85);
        }
        * { box-sizing: border-box; font-family: 'Segoe UI', Roboto, Helvetica, sans-serif; -webkit-tap-highlight-color: transparent; }
        body { margin: 0; background: var(--bg); color: var(--txt); height: 100vh; display: flex; overflow: hidden; width: 100vw; }
        
        /* Элитная авторизация */
        #auth { position: fixed; inset: 0; z-index: 9999; background: radial-gradient(circle at center, #1e2c3a, #0e1621); display: flex; align-items: center; justify-content: center; padding: 20px; }
        .auth-box { background: var(--glass); backdrop-filter: blur(10px); padding: 40px; border-radius: 30px; text-align: center; width: 100%; max-width: 350px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 20px 50px rgba(0,0,0,0.5); }
        .auth-box input { width: 100%; padding: 15px; margin: 12px 0; border-radius: 15px; border: none; background: rgba(0,0,0,0.3); color: white; font-size: 16px; transition: 0.3s; }
        .auth-box input:focus { background: rgba(0,0,0,0.5); box-shadow: 0 0 0 2px var(--blue); }
        .auth-btn { width: 100%; padding: 15px; background: var(--blue); border: none; color: white; border-radius: 15px; font-weight: 600; font-size: 18px; cursor: pointer; margin-top: 10px; box-shadow: 0 4px 15px rgba(36, 129, 204, 0.4); }

        /* Список чатов */
        #side { width: 320px; background: var(--side); border-right: 1px solid rgba(0,0,0,0.3); display: flex; flex-direction: column; z-index: 500; }
        .side-head { padding: 25px 20px; font-size: 22px; font-weight: 700; color: var(--blue); letter-spacing: -0.5px; }
        .chat-item { padding: 15px 18px; cursor: pointer; display: flex; align-items: center; gap: 15px; transition: 0.2s; position: relative; }
        .chat-item:hover { background: rgba(255,255,255,0.03); }
        .chat-item.active { background: var(--out); }
        .ava { width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); background: linear-gradient(135deg, #2481cc, #005588); }

        /* Чат */
        #main { flex: 1; display: flex; flex-direction: column; background: #0e1117; position: relative; }
        .top-bar { padding: 12px 18px; background: var(--glass); backdrop-filter: blur(10px); display: flex; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); z-index: 400; min-height: 65px; }
        
        #feed { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 10px; padding-bottom: 200px; }
        
        .msg { max-width: 82%; padding: 12px 16px; border-radius: 20px; font-size: 15.5px; line-height: 1.4; position: relative; box-shadow: 0 2px 5px rgba(0,0,0,0.1); animation: slideIn 0.2s ease-out; }
        @keyframes slideIn { from { transform: translateY(10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .msg.out { align-self: flex-end; background: var(--out); border-bottom-right-radius: 4px; }
        .msg.in { align-self: flex-start; background: var(--in); border-bottom-left-radius: 4px; }
        .msg b { color: #82b1ff; font-size: 12px; }
        .time { font-size: 10px; opacity: 0.5; text-align: right; margin-top: 4px; }

        /* ПРЕМИАЛЬНАЯ ПАНЕЛЬ ВВОДА */
        .bar { 
            padding: 10px 15px; 
            background: var(--glass); 
            backdrop-filter: blur(15px);
            display: none; 
            align-items: center; 
            gap: 12px; 
            padding-bottom: calc(65px + env(safe-area-inset-bottom)); 
            position: absolute; bottom: 0; left: 0; right: 0; z-index: 1000;
            border-top: 1px solid rgba(255,255,255,0.05);
        }
        .inp-container { flex: 1; background: rgba(0,0,0,0.2); border-radius: 25px; padding: 5px 15px; display: flex; align-items: center; }
        .inp { width: 100%; background: none; border: none; padding: 10px 0; color: white; font-size: 16px; outline: none; }
        .icon-btn { color: var(--blue); font-size: 24px; cursor: pointer; transition: 0.2s; flex-shrink: 0; }
        .icon-btn:active { transform: scale(0.9); opacity: 0.7; }
        .send-btn { background: var(--blue); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; border: none; box-shadow: 0 4px 10px rgba(36, 129, 204, 0.3); }

        @media (max-width: 700px) {
            #side { position: absolute; width: 100%; height: 100%; left: 0; }
            body.chatting #side { transform: translateX(-100%); }
            .back { display: block !important; }
        }
        .back { display: none; margin-right: 15px; font-size: 22px; color: var(--blue); cursor: pointer; }
    </style>
</head>
<body>

<div id="auth">
    <div class="auth-box">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Telegram_logo.svg/2048px-Telegram_logo.svg.png" style="width:70px; margin-bottom:15px;">
        <h2 style="margin:0; font-weight:700;">TegeGrom Elite</h2>
        <p style="opacity:0.5; font-size:14px; margin-bottom:20px;">Premium Messaging Experience</p>
        <input type="text" id="a-user" placeholder="Логин">
        <input type="password" id="a-pass" placeholder="Пароль">
        <button class="auth-btn" onclick="doAuth()">Войти</button>
        <p id="auth-err" style="color:#ff5f5f; font-size:12px; margin-top:10px;"></p>
    </div>
</div>

<div id="side">
    <div class="side-head">Tegegrom✔</div>
    <div class="chat-item" id="btn-all" onclick="selectChat('all')">
        <div class="ava" style="background: linear-gradient(135deg, #0088cc, #00c6ff)">📨</div>
        <div><b>🟥Главный Чат🟥</b><br><small style="opacity:0.5">Могут переписыватся все</small></div>
    </div>
    <div id="contacts-list" style="overflow-y:auto; flex:1;"></div>
</div>

<div id="main">
    <div class="top-bar">
        <i class="fa-solid fa-chevron-left back" onclick="closeChat()"></i>
        <div class="ava" id="h-ava" style="width:35px; height:35px; font-size:15px; margin-right:12px;">📢</div>
        <b id="h-title" style="font-size:18px;">TegeGrom</b>
    </div>
    <div id="feed"></div>
    <div class="bar" id="input-bar">
        <label class="icon-btn"><i class="fa-solid fa-paperclip"></i><input type="file" id="f-in" hidden onchange="upFile()"></label>
        <div class="inp-container">
            <input type="text" id="m-in" class="inp" placeholder="Написать сообщение..." onkeypress="if(event.key==='Enter')send('text')">
            <i class="fa-solid fa-microphone icon-btn" id="mic" onclick="toggleMic()" style="margin-left:10px;"></i>
        </div>
        <button class="send-btn" onclick="send('text')"><i class="fa-solid fa-arrow-up"></i></button>
    </div>
</div>

<audio id="snd" src="https://raw.githubusercontent.com/Anonym761/archive/main/msg.mp3" preload="auto"></audio>

<script>
    let myName = localStorage.getItem('tg_v30_u') || "";
    let target = "";
    let lastId = 0;
    let mediaRec;
    let chunks = [];
    let swReg = null;

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').then(r => swReg = r);
    }

    if(myName) { 
        document.getElementById('auth').style.display='none'; 
        startApp(); 
    }

    async function doAuth() {
        const u = document.getElementById('a-user').value.trim();
        const p = document.getElementById('a-pass').value.trim();
        if(!u || !p) return;
        const r = await fetch('/api/auth', {method:'POST', body:JSON.stringify({u, p}), headers:{'Content-Type':'application/json'}});
        const res = await r.json();
        if(res.ok) { 
            localStorage.setItem('tg_v30_u', res.user); 
            Notification.requestPermission();
            location.reload(); 
        } else { document.getElementById('auth-err').innerText = res.msg; }
    }

    function startApp() {
        setInterval(sync, 1500);
        setInterval(loadUsers, 5000);
        loadUsers();
        navigator.mediaDevices.getUserMedia({ audio: true }).catch(()=>{});
    }

    function selectChat(t) {
        target = t; lastId = 0;
        document.getElementById('h-title').innerText = t === 'all' ? 'Общий чат' : t;
        document.getElementById('h-ava').innerText = t === 'all' ? '📢' : t[0].toUpperCase();
        document.getElementById('feed').innerHTML = '';
        document.getElementById('input-bar').style.display = 'flex';
        document.body.classList.add('chatting');
        sync();
    }

    function closeChat() {
        document.body.classList.remove('chatting');
        document.getElementById('input-bar').style.display = 'none';
        target = "";
    }

    async function loadUsers() {
        const r = await fetch('/api/get_users');
        const users = await r.json();
        const list = document.getElementById('contacts-list');
        list.innerHTML = users.filter(u => u !== myName).map(u => `
            <div class="chat-item ${target===u?'active':''}" onclick="selectChat('${u}')">
                <div class="ava">${u[0].toUpperCase()}</div>
                <div><b>${u}</b><br><small style="opacity:0.4">Нажмите, чтобы открыть</small></div>
            </div>`).join('');
    }

    async function send(type, content='', file='') {
        const inp = document.getElementById('m-in');
        const txt = content || inp.value.trim();
        if(!txt && !file) return;
        await fetch('/api/send', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({s:myName, r:target, c:txt, t:type, f:file})});
        inp.value = '';
        sync();
    }

    async function sync() {
        if(!target || !myName) return;
        try {
            const r = await fetch(`/api/get/${myName}/${target}?last=${lastId}`);
            const data = await r.json();
            const f = document.getElementById('feed');
            data.forEach(m => {
                if(m.id > lastId) {
                    lastId = m.id;
                    const div = document.createElement('div');
                    div.className = `msg ${m.sender === myName ? 'out' : 'in'}`;
                    let b = m.type==='img' ? `<img src="${m.file}" style="max-width:100%;border-radius:15px;">` : (m.type==='audio' ? `<audio controls src="${m.file}" style="width:200px;"></audio>` : `<span>${m.content}</span>`);
                    div.innerHTML = `<b>${m.sender}</b><br>${b}<div class="time">${m.timestamp}</div>`;
                    f.appendChild(div);
                    f.scrollTop = f.scrollHeight;
                    
                    if(m.sender !== myName) {
                        document.getElementById('snd').play().catch(()=>{});
                        if(navigator.vibrate) navigator.vibrate(200);
                        if(swReg && Notification.permission === "granted") {
                            swReg.active.postMessage({ type: 'PUSH', title: m.sender, body: m.content });
                        }
                    }
                }
            });
        } catch(e) {}
    }

    function upFile() {
        const file = document.getElementById('f-in').files[0];
        const reader = new FileReader();
        reader.onload = () => send('img', '[Фото]', reader.result);
        reader.readAsDataURL(file);
    }

    async function toggleMic() {
        const mic = document.getElementById('mic');
        if (!mediaRec || mediaRec.state === "inactive") {
            const s = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRec = new MediaRecorder(s);
            chunks = [];
            mediaRec.ondataavailable = e => chunks.push(e.data);
            mediaRec.onstop = () => {
                const b = new Blob(chunks, { type: 'audio/webm' });
                const r = new FileReader();
                r.onload = () => send('audio', '[Голосовое]', r.result);
                r.readAsDataURL(b);
            };
            mediaRec.start();
            mic.style.color = '#ff5f5f';
        } else {
            mediaRec.stop();
            mic.style.color = 'var(--blue)';
        }
    }
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
