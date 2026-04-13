import sqlite3, uvicorn, hashlib, base64, os
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from datetime import datetime

app = FastAPI()
DB = 'tegegrom_v29_titan.db'

# --- База данных (всё сохранено по твоему GitHub) ---
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

# Эндпоинт Service Worker (КЛЮЧ К УВЕДОМЛЕНИЯМ)
@app.get("/sw.js", response_class=PlainTextResponse)
async def get_sw():
    return """
    self.addEventListener('install', (e) => self.skipWaiting());
    self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
    
    self.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'PUSH_NOTIF') {
            self.registration.showNotification(event.data.title, {
                body: event.data.body,
                icon: 'https://cdn-icons-png.flaticon.com/512/5968/5968841.png',
                vibrate: [200, 100, 200],
                badge: 'https://cdn-icons-png.flaticon.com/512/5968/5968841.png'
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
    <title>TegeGrom V29</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --bg: #0e1621; --side: #17212b; --blue: #0088cc; --txt: #f5f5f5; --in: #182533; --out: #2b5278; }
        * { box-sizing: border-box; font-family: -apple-system, sans-serif; -webkit-tap-highlight-color: transparent; }
        body { margin: 0; background: var(--bg); color: var(--txt); height: 100vh; display: flex; overflow: hidden; width: 100vw; }
        
        #auth { position: fixed; inset: 0; z-index: 9999; background: var(--bg); display: flex; align-items: center; justify-content: center; padding: 15px; }
        .auth-box { background: var(--side); padding: 25px; border-radius: 20px; text-align: center; width: 100%; max-width: 320px; }
        .auth-box input { width: 100%; padding: 12px; margin: 8px 0; border-radius: 10px; border: 1px solid #242f3d; background: #0b1118; color: white; outline: none; font-size: 16px; }
        
        #side { width: 300px; background: var(--side); border-right: 1px solid #000; display: flex; flex-direction: column; z-index: 500; transition: 0.3s ease; }
        .chat-item { padding: 14px; cursor: pointer; border-bottom: 1px solid rgba(0,0,0,0.1); display: flex; align-items: center; gap: 10px; }
        .chat-item.active { background: var(--out); }
        .ava { width: 42px; height: 42px; background: var(--blue); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; }

        #main { flex: 1; display: flex; flex-direction: column; background: #0e1117; position: relative; width: 100%; }
        #feed { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; padding-bottom: 160px; scroll-behavior: smooth; }
        
        .msg { max-width: 85%; padding: 10px 14px; border-radius: 18px; font-size: 15px; line-height: 1.4; position: relative; }
        .msg.out { align-self: flex-end; background: var(--out); border-bottom-right-radius: 4px; }
        .msg.in { align-self: flex-start; background: var(--in); border-bottom-left-radius: 4px; }
        
        .bar { 
            padding: 10px 12px; background: var(--side); display: none; align-items: center; gap: 8px; 
            padding-bottom: calc(55px + env(safe-area-inset-bottom)); 
            border-top: 1px solid rgba(255,255,255,0.05); position: absolute; bottom: 0; left: 0; right: 0; z-index: 1000;
        }
        .inp { flex: 1; background: #0b1118; border: none; padding: 10px 15px; color: white; border-radius: 20px; font-size: 16px; min-width: 0; }
        .btn-send { width: 40px; height: 40px; background: none; border: none; color: var(--blue); font-size: 24px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .icon { color: var(--blue); font-size: 22px; cursor: pointer; flex-shrink: 0; }
        .rec-active { color: #ff5f5f !important; animation: pulse 1s infinite; }
        @keyframes pulse { 50% { opacity: 0.5; } }

        @media (max-width: 700px) {
            #side { position: absolute; width: 100%; height: 100%; left: 0; }
            body.chatting #side { transform: translateX(-100%); }
            .back { display: block !important; }
        }
        .back { display: none; margin-right: 10px; cursor: pointer; font-size: 22px; color: var(--blue); }
    </style>
</head>
<body>

<div id="auth">
    <div class="auth-box">
        <h3 style="color:var(--blue); margin-bottom:15px;">TegeGrom</h3>
        <input type="text" id="a-user" placeholder="Логин">
        <input type="password" id="a-pass" placeholder="Пароль">
        <button onclick="doAuth()" style="width:100%; padding:12px; background:var(--blue); border:none; color:white; border-radius:10px; font-weight:bold; cursor:pointer;">ВОЙТИ</button>
        <p id="auth-err" style="color:#ff5f5f; font-size:12px;"></p>
    </div>
</div>

<div id="side">
    <div style="padding:20px 15px; font-weight:bold; font-size:20px;">Чаты</div>
    <div class="chat-item" id="btn-all" onclick="selectChat('all')">
        <div class="ava" style="background:#0088cc">📢</div> <b>Общий чат</b>
    </div>
    <div id="contacts-list" style="overflow-y:auto; flex:1;"></div>
</div>

<div id="main">
    <div style="padding:12px 15px; background:var(--side); display:flex; align-items:center; min-height:55px;">
        <i class="fa-solid fa-chevron-left back" onclick="closeChat()"></i>
        <b id="h-title" style="font-size:17px;">TegeGrom</b>
    </div>
    <div id="feed"></div>
    <div class="bar" id="input-bar">
        <label class="icon"><i class="fa-solid fa-paperclip"></i><input type="file" id="f-in" hidden onchange="upFile()"></label>
        <input type="text" id="m-in" class="inp" placeholder="Текст..." onkeypress="if(event.key==='Enter')send('text')">
        <i class="fa-solid fa-microphone icon" id="mic" onclick="toggleMic()"></i>
        <button class="btn-send" onclick="send('text')"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
</div>

<audio id="snd" src="https://raw.githubusercontent.com/Anonym761/archive/main/msg.mp3" preload="auto"></audio>

<script>
    let myName = localStorage.getItem('tg_v29_u') || "";
    let target = "";
    let lastId = 0;
    let mediaRec;
    let chunks = [];
    let swReg = null;

    // РЕГИСТРАЦИЯ SW ДЛЯ УБОЙНЫХ ПУШЕЙ
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').then(reg => {
            swReg = reg;
            console.log("SW Ready");
        });
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
            localStorage.setItem('tg_v29_u', res.user); 
            if (Notification.permission !== "granted") await Notification.requestPermission();
            location.reload(); 
        } else { document.getElementById('auth-err').innerText = res.msg; }
    }

    function startApp() {
        setInterval(sync, 1500);
        setInterval(loadUsers, 5000);
        loadUsers();
    }

    function selectChat(t) {
        target = t; lastId = 0;
        document.getElementById('h-title').innerText = t === 'all' ? 'Общий чат' : t;
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
                <div class="ava" style="background:#2b5278">${u[0].toUpperCase()}</div> <b>${u}</b>
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
                    let b = m.type==='img' ? `<img src="${m.file}" style="max-width:100%;border-radius:10px;">` : (m.type==='audio' ? `<audio controls src="${m.file}" style="width:180px;"></audio>` : `<span>${m.content}</span>`);
                    div.innerHTML = `<b style="font-size:11px; color:var(--blue)">${m.sender}</b><br>${b}<div style="font-size:10px; opacity:0.5; text-align:right;">${m.timestamp}</div>`;
                    f.appendChild(div);
                    f.scrollTop = f.scrollHeight;
                    
                    if(m.sender !== myName) {
                        document.getElementById('snd').play().catch(()=>{});
                        if(navigator.vibrate) navigator.vibrate([100, 50, 100]);
                        
                        // ОТПРАВЛЯЕМ КОМАНДУ В SERVICE WORKER ДЛЯ ПУША
                        if (swReg && Notification.permission === "granted") {
                            swReg.active.postMessage({
                                type: 'PUSH_NOTIF',
                                title: "TegeGrom: " + m.sender,
                                body: m.content
                            });
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
            mic.classList.add('rec-active');
        } else {
            mediaRec.stop();
            mic.classList.remove('rec-active');
        }
    }
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
