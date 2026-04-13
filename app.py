import sqlite3, uvicorn, hashlib, base64, os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from datetime import datetime

app = FastAPI()
# База данных с "выживающим" названием
DB = 'tegegrom_ultra_v26_final_core.db'

# --- СЕРВЕРНАЯ ЛОГИКА И БД ---
def init_db():
    with sqlite3.connect(DB) as conn:
        # Индексы ускоряют поиск, когда база разрастется до тысяч строк
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            sender TEXT, receiver TEXT, content TEXT, 
            timestamp TEXT, type TEXT DEFAULT 'text', file TEXT DEFAULT '')''')
        conn.execute("CREATE INDEX IF NOT EXISTS idx_receiver ON messages(receiver)")
        conn.commit()

init_db()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

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
            return {"ok": True, "user": u, "msg": "Аккаунт создан"}

@app.get("/api/get_users")
async def get_users():
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        res = conn.execute("SELECT username FROM users").fetchall()
        return [r['username'] for r in res]

@app.get("/api/get/{me}/{to}")
async def get_msgs(me: str, to: str, last: int = 0):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        if to == "all":
            q = "SELECT * FROM messages WHERE receiver='all' AND id > ? ORDER BY id ASC LIMIT 100"
            params = (last,)
        else:
            q = "SELECT * FROM messages WHERE ((sender=? AND receiver=?) OR (sender=? AND receiver=?)) AND id > ? ORDER BY id ASC LIMIT 100"
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

# --- ИНТЕРФЕЙС TegeGrom Ultra ---
UI = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover, user-scalable=no">
    <title>TegeGrom Ultra V26</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --bg: #0e1621; --side: #17212b; --blue: #0088cc; --txt: #f5f5f5; --in: #182533; --out: #2b5278; --accent: #2481cc; }
        * { box-sizing: border-box; font-family: -apple-system, system-ui, sans-serif; -webkit-tap-highlight-color: transparent; outline: none; }
        body { margin: 0; background: var(--bg); color: var(--txt); height: 100vh; display: flex; overflow: hidden; position: fixed; width: 100%; }
        
        /* Экран авторизации */
        #auth { position: fixed; inset: 0; z-index: 9999; background: var(--bg); display: flex; align-items: center; justify-content: center; padding: 20px; }
        .auth-box { background: var(--side); padding: 35px; border-radius: 30px; text-align: center; width: 100%; max-width: 400px; box-shadow: 0 20px 60px rgba(0,0,0,0.7); }
        .auth-box input { width: 100%; padding: 16px; margin: 10px 0; border-radius: 15px; border: 1px solid #242f3d; background: #0b1118; color: white; font-size: 16px; }
        .auth-box button { width: 100%; padding: 16px; background: var(--blue); border: none; color: white; border-radius: 15px; font-weight: bold; font-size: 17px; cursor: pointer; margin-top: 10px; }

        /* Список чатов */
        #side { width: 320px; background: var(--side); border-right: 1px solid #000; display: flex; flex-direction: column; z-index: 500; transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .side-head { padding: 30px 20px 20px; font-weight: bold; font-size: 26px; color: var(--blue); }
        .chat-item { padding: 15px 20px; cursor: pointer; border-bottom: 1px solid rgba(0,0,0,0.1); display: flex; align-items: center; gap: 15px; transition: 0.2s; }
        .chat-item.active { background: var(--out); }
        .ava { width: 52px; height: 52px; background: var(--blue); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 22px; color: #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }

        /* Чат */
        #main { flex: 1; display: flex; flex-direction: column; background: #0e1117; position: relative; }
        .main-head { padding: 15px 20px; background: var(--side); display: flex; align-items: center; border-bottom: 1px solid rgba(0,0,0,0.3); z-index: 400; min-height: 70px; }
        
        #feed { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; padding-bottom: 220px; scroll-behavior: smooth; }
        
        /* Сообщения */
        .msg { max-width: 85%; padding: 12px 18px; border-radius: 20px; font-size: 16px; line-height: 1.4; position: relative; animation: msgFade 0.3s ease; }
        @keyframes msgFade { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        
        .msg.out { align-self: flex-end; background: var(--out); border-bottom-right-radius: 4px; }
        .msg.in { align-self: flex-start; background: var(--in); border-bottom-left-radius: 4px; }
        .msg-sender { font-size: 11px; font-weight: bold; color: var(--blue); margin-bottom: 4px; display: block; }
        .time { font-size: 10px; opacity: 0.5; text-align: right; margin-top: 5px; }

        /* ПАНЕЛЬ ВВОДА - ФИКС ДЛЯ ТЕЛЕФОНОВ */
        .bar { 
            padding: 15px 20px; 
            background: var(--side); 
            display: none; 
            align-items: center; 
            gap: 15px; 
            padding-bottom: calc(75px + env(safe-area-inset-bottom)); 
            border-top: 1px solid rgba(255,255,255,0.05);
            position: absolute; bottom: 0; left: 0; right: 0;
            z-index: 1000;
            box-shadow: 0 -10px 30px rgba(0,0,0,0.5);
        }
        .inp { flex: 1; background: #0b1118; border: none; padding: 14px 20px; color: white; border-radius: 30px; font-size: 16px; }
        .icon { color: var(--blue); font-size: 28px; cursor: pointer; transition: 0.2s; }
        .icon:active { transform: scale(0.8); }
        .mic-rec { color: #ff4d4d !important; animation: blink 1s infinite; }
        @keyframes blink { 50% { opacity: 0.3; } }

        @media (max-width: 750px) {
            #side { position: absolute; width: 100%; height: 100%; left: 0; }
            body.chatting #side { transform: translateX(-100%); }
            .back-btn { display: block !important; }
        }
        .back-btn { display: none; margin-right: 15px; font-size: 24px; color: var(--blue); }
    </style>
</head>
<body>

<div id="auth">
    <div class="auth-box">
        <h2 style="color:var(--blue); margin-bottom:10px;">TegeGrom Ultra</h2>
        <p style="opacity:0.6; margin-bottom:20px;">Вход или Регистрация</p>
        <input type="text" id="a-user" placeholder="Ваш никнейм" autocomplete="off">
        <input type="password" id="a-pass" placeholder="Пароль">
        <button onclick="doAuth()">ВОЙТИ В АККАУНТ</button>
        <p id="auth-err" style="color:#ff5f5f; margin-top:15px; font-size:14px;"></p>
    </div>
</div>

<div id="side">
    <div class="side-head">TegeGrom</div>
    <div class="chat-item" id="btn-all" onclick="selectChat('all')">
        <div class="ava" style="background: linear-gradient(45deg, #0088cc, #00c6ff);"><i class="fa-solid fa-earth-americas"></i></div>
        <div style="flex:1">
            <div style="font-weight:bold">Общий чат</div>
            <div style="font-size:12px; opacity:0.5">Все пользователи здесь</div>
        </div>
    </div>
    <div id="contacts-list" style="overflow-y:auto; flex:1;"></div>
</div>

<div id="main">
    <div class="main-head">
        <i class="fa-solid fa-chevron-left back-btn" onclick="closeChat()"></i>
        <div class="ava" id="h-ava" style="width:40px; height:40px; font-size:16px; margin-right:12px;">📢</div>
        <b id="h-title" style="font-size:19px;">Выберите чат</b>
    </div>
    <div id="feed"></div>
    <div class="bar" id="input-bar">
        <label class="icon"><i class="fa-solid fa-paperclip"></i><input type="file" id="f-in" hidden onchange="upFile()"></label>
        <input type="text" id="m-in" class="inp" placeholder="Написать..." onkeypress="if(event.key==='Enter')send('text')">
        <i class="fa-solid fa-microphone icon" id="mic" onclick="toggleMic()"></i>
        <i class="fa-solid fa-circle-arrow-up icon" style="font-size:35px" onclick="send('text')"></i>
    </div>
</div>

<audio id="snd_in" src="https://raw.githubusercontent.com/Anonym761/archive/main/msg.mp3" preload="auto"></audio>

<script>
    let myName = localStorage.getItem('tg_v26_u') || "";
    let target = "";
    let lastId = 0;
    let rec;
    let chunks = [];

    // Принудительная регистрация Service Worker для пушей (заглушка для стабильности)
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('data:text/javascript;base64,')
        .catch(() => {});
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
            localStorage.setItem('tg_v26_u', res.user); 
            Notification.requestPermission();
            location.reload(); 
        } else { document.getElementById('auth-err').innerText = res.msg; }
    }

    function startApp() {
        setInterval(sync, 1500);
        setInterval(loadUsers, 5000);
        loadUsers();
        // Разрешаем аудио заранее
        navigator.mediaDevices.getUserMedia({ audio: true }).catch(()=>{});
    }

    function selectChat(t) {
        target = t; lastId = 0;
        document.getElementById('h-title').innerText = t === 'all' ? 'Общий чат' : t;
        document.getElementById('h-ava').innerText = t === 'all' ? '📢' : t[0].toUpperCase();
        document.getElementById('feed').innerHTML = '';
        document.getElementById('input-bar').style.display = 'flex';
        document.body.classList.add('chatting');
        document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
        if(t==='all') document.getElementById('btn-all').classList.add('active');
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
                <div class="ava" style="background:#2b5278">${u[0].toUpperCase()}</div>
                <div style="flex:1">
                    <div style="font-weight:bold">${u}</div>
                    <div style="font-size:12px; opacity:0.5">Личные сообщения</div>
                </div>
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
                    
                    let body = "";
                    if(m.type === 'img') body = `<img src="${m.file}" onclick="window.open(this.src)" style="max-width:100%; border-radius:12px; cursor:pointer;">`;
                    else if(m.type === 'audio') body = `<audio controls src="${m.file}" style="width:100%; min-width:150px;"></audio>`;
                    else body = `<span>${m.content}</span>`;
                    
                    div.innerHTML = `<span class="msg-sender">${m.sender}</span>${body}<div class="time">${m.timestamp}</div>`;
                    f.appendChild(div);
                    f.scrollTop = f.scrollHeight;
                    
                    if(m.sender !== myName) {
                        document.getElementById('snd_in').play().catch(()=>{});
                        if(navigator.vibrate) navigator.vibrate(100);
                        if(document.hidden && Notification.permission === "granted") {
                            new Notification("TegeGrom", { body: m.sender + ": " + m.content });
                        }
                    }
                }
            });
        } catch(e) {}
    }

    function upFile() {
        const file = document.getElementById('f-in').files[0];
        if(!file) return;
        const reader = new FileReader();
        reader.onload = () => send('img', '[Фотография]', reader.result);
        reader.readAsDataURL(file);
    }

    async function toggleMic() {
        const mic = document.getElementById('mic');
        if (!rec || rec.state === "inactive") {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            rec = new MediaRecorder(stream);
            chunks = [];
            rec.ondataavailable = e => chunks.push(e.data);
            rec.onstop = () => {
                const blob = new Blob(chunks, { type: 'audio/webm' });
                const reader = new FileReader();
                reader.onload = () => send('audio', '[Голосовое]', reader.result);
                reader.readAsDataURL(blob);
            };
            rec.start();
            mic.classList.add('mic-rec');
        } else {
            rec.stop();
            mic.classList.remove('mic-rec');
        }
    }

    // Решение бага клавиатуры: скролл при изменении видимой области
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', () => {
            document.getElementById('feed').scrollTop = document.getElementById('feed').scrollHeight;
        });
    }
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
