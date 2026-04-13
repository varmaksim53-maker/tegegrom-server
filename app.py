import sqlite3, uvicorn, hashlib, base64
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime

app = FastAPI()
DB = 'tegegrom_v24_forever.db'

# --- Инициализация базы данных ---
def init_db():
    with sqlite3.connect(DB) as conn:
        # Таблица пользователей (логин + хэш пароля)
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT)''')
        # Таблица сообщений (с типом контента и файлами)
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            sender TEXT, receiver TEXT, content TEXT, 
            timestamp TEXT, type TEXT DEFAULT 'text', file TEXT DEFAULT '')''')
        conn.commit()

init_db()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

@app.get("/", response_class=HTMLResponse)
async def index(): return UI

# --- API Эндпоинты ---

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

# --- ИНТЕРФЕЙС (HTML/CSS/JS) ---

UI = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>TegeGrom Ultra Pro</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --bg: #0e1621; --side: #17212b; --blue: #0088cc; --txt: #f5f5f5; --in: #182533; --out: #2b5278; --accent: #2481cc; }
        * { box-sizing: border-box; font-family: -apple-system, system-ui, sans-serif; -webkit-tap-highlight-color: transparent; }
        body { margin: 0; background: var(--bg); color: var(--txt); height: 100vh; display: flex; overflow: hidden; }
        
        /* Экран авторизации */
        #auth { position: fixed; inset: 0; z-index: 9999; background: var(--bg); display: flex; align-items: center; justify-content: center; padding: 20px; }
        .auth-box { background: var(--side); padding: 35px; border-radius: 25px; text-align: center; width: 100%; max-width: 380px; box-shadow: 0 20px 60px rgba(0,0,0,0.6); border: 1px solid rgba(255,255,255,0.05); }
        .auth-box h2 { color: var(--blue); margin-top: 0; font-size: 28px; }
        .auth-box input { width: 100%; padding: 15px; margin: 12px 0; border-radius: 12px; border: 1px solid #242f3d; background: #0b1118; color: white; outline: none; font-size: 16px; transition: 0.3s; }
        .auth-box input:focus { border-color: var(--blue); }
        .auth-box button { width: 100%; padding: 16px; background: var(--blue); border: none; color: white; border-radius: 15px; font-weight: bold; cursor: pointer; font-size: 16px; margin-top: 15px; transition: 0.2s; }
        .auth-box button:active { transform: scale(0.98); }

        /* Сайдбар */
        #side { width: 320px; background: var(--side); border-right: 1px solid rgba(0,0,0,0.4); display: flex; flex-direction: column; z-index: 500; transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .side-header { padding: 25px 20px; font-weight: bold; font-size: 24px; color: var(--blue); display: flex; align-items: center; justify-content: space-between; }
        .chat-item { padding: 16px; cursor: pointer; border-bottom: 1px solid rgba(0,0,0,0.05); display: flex; align-items: center; gap: 14px; transition: 0.2s; }
        .chat-item:hover { background: rgba(255,255,255,0.03); }
        .chat-item.active { background: var(--out); }
        .ava { width: 50px; height: 50px; background: var(--blue); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }

        /* Главный экран */
        #main { flex: 1; display: flex; flex-direction: column; background: #0e1117; position: relative; }
        .main-header { padding: 15px 20px; background: var(--side); display: flex; align-items: center; border-bottom: 1px solid rgba(0,0,0,0.3); z-index: 400; }
        
        #feed { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; padding-bottom: 180px; scroll-behavior: smooth; }
        
        /* Сообщения */
        .msg { max-width: 80%; padding: 12px 16px; border-radius: 18px; font-size: 15.5px; line-height: 1.45; position: relative; animation: msgIn 0.3s ease; }
        @keyframes msgIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
        
        .msg.out { align-self: flex-end; background: var(--out); border-bottom-right-radius: 4px; }
        .msg.in { align-self: flex-start; background: var(--in); border-bottom-left-radius: 4px; }
        .msg-info { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 11px; font-weight: bold; color: var(--blue); }
        .time { font-size: 10px; opacity: 0.5; text-align: right; margin-top: 5px; }

        /* ПАНЕЛЬ ВВОДА (Максимально поднята для мобилок) */
        .bar { 
            padding: 15px 20px; 
            background: var(--side); 
            display: flex; 
            align-items: center; 
            gap: 15px; 
            padding-bottom: calc(60px + env(safe-area-inset-bottom)); 
            border-top: 1px solid rgba(255,255,255,0.05);
            position: absolute; bottom: 0; left: 0; right: 0;
            z-index: 1000;
            box-shadow: 0 -10px 25px rgba(0,0,0,0.4);
        }
        .inp { flex: 1; background: #0b1118; border: none; padding: 14px 20px; color: white; border-radius: 25px; font-size: 16px; outline: none; transition: 0.2s; border: 1px solid transparent; }
        .inp:focus { border-color: var(--blue); }
        .icon-btn { color: var(--blue); font-size: 26px; cursor: pointer; transition: 0.2s; display: flex; align-items: center; }
        .icon-btn:active { transform: scale(0.9); }

        /* Мобильная адаптивность */
        @media (max-width: 750px) {
            #side { position: absolute; width: 100%; height: 100%; left: 0; }
            body.chatting #side { transform: translateX(-100%); }
            .back-btn { display: flex !important; }
        }
        .back-btn { display: none; margin-right: 15px; cursor: pointer; font-size: 24px; color: var(--blue); }

        /* Скроллбар */
        #feed::-webkit-scrollbar { width: 5px; }
        #feed::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
    </style>
</head>
<body>

<div id="auth">
    <div class="auth-box">
        <h2>TegeGrom</h2>
        <input type="text" id="a-user" placeholder="Логин" autocomplete="off">
        <input type="password" id="a-pass" placeholder="Пароль">
        <button onclick="doAuth()">ВОЙТИ / СОЗДАТЬ</button>
        <p id="auth-err" style="color:#ff5f5f; margin-top:15px; font-size:14px; font-weight: 500;"></p>
    </div>
</div>

<div id="side">
    <div class="side-header">
        <span>Чаты</span>
        <i class="fa-solid fa-pen-to-square" style="font-size: 18px; opacity: 0.5;"></i>
    </div>
    <div class="chat-item active" id="btn-all" onclick="selectChat('all')">
        <div class="ava" style="background: linear-gradient(45deg, #0088cc, #00c6ff);"><i class="fa-solid fa-users"></i></div>
        <div style="flex:1">
            <div style="font-weight:bold">Общий чат</div>
            <div style="font-size:12px; opacity:0.6">Все пользователи</div>
        </div>
    </div>
    <div id="contacts-list" style="overflow-y:auto; flex:1;"></div>
</div>

<div id="main">
    <div class="main-header">
        <i class="fa-solid fa-chevron-left back-btn" onclick="document.body.classList.remove('chatting')"></i>
        <div class="ava" id="h-ava" style="width:35px; height:35px; font-size:14px; margin-right:12px;">📢</div>
        <b id="h-title" style="font-size:18px;">Общий чат</b>
    </div>
    <div id="feed"></div>
    <div class="bar">
        <label class="icon-btn"><i class="fa-solid fa-paperclip"></i><input type="file" id="f-in" hidden onchange="upFile()"></label>
        <input type="text" id="m-in" class="inp" placeholder="Написать сообщение..." onkeypress="if(event.key==='Enter')send('text')">
        <div class="icon-btn" onclick="send('text')"><i class="fa-solid fa-circle-arrow-up" style="font-size: 32px;"></i></div>
    </div>
</div>

<audio id="snd_in" src="https://raw.githubusercontent.com/Anonym761/archive/main/msg.mp3"></audio>

<script>
    let myName = localStorage.getItem('tg_v24_u') || "";
    let target = "all";
    let lastId = 0;
    let isSyncing = false;

    if(myName) { 
        document.getElementById('auth').style.display='none'; 
        Notification.requestPermission();
        startApp(); 
    }

    async function doAuth() {
        const u = document.getElementById('a-user').value.trim();
        const p = document.getElementById('a-pass').value.trim();
        if(!u || !p) return;
        const r = await fetch('/api/auth', {
            method:'POST', 
            body:JSON.stringify({u, p}), 
            headers:{'Content-Type':'application/json'}
        });
        const res = await r.json();
        if(res.ok) { 
            localStorage.setItem('tg_v24_u', res.user); 
            location.reload(); 
        } else { 
            document.getElementById('auth-err').innerText = res.msg; 
        }
    }

    function startApp() {
        setInterval(sync, 1500);
        setInterval(loadUsers, 5000);
        loadUsers();
    }

    function selectChat(t) {
        target = t; 
        lastId = 0;
        document.getElementById('h-title').innerText = t === 'all' ? 'Общий чат' : t;
        document.getElementById('h-ava').innerText = t === 'all' ? '📢' : t[0].toUpperCase();
        document.getElementById('feed').innerHTML = '';
        document.body.classList.add('chatting');
        document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
        sync();
    }

    async function loadUsers() {
        try {
            const r = await fetch('/api/get_users');
            const users = await r.json();
            const list = document.getElementById('contacts-list');
            list.innerHTML = users.filter(u => u !== myName).map(u => `
                <div class="chat-item ${target===u?'active':''}" onclick="selectChat('${u}')">
                    <div class="ava" style="background:#2b5278">${u[0].toUpperCase()}</div>
                    <div style="flex:1">
                        <div style="font-weight:bold">${u}</div>
                        <div style="font-size:12px; opacity:0.5">личные сообщения</div>
                    </div>
                </div>`).join('');
        } catch(e) {}
    }

    async function send(type, content='', file='') {
        const inp = document.getElementById('m-in');
        const txt = content || inp.value.trim();
        if(!txt && !file) return;
        
        await fetch('/api/send', {
            method:'POST', 
            headers:{'Content-Type':'application/json'}, 
            body:JSON.stringify({s:myName, r:target, c:txt, t:type, f:file})
        });
        inp.value = '';
        sync();
    }

    async function sync() {
        if(isSyncing || !myName) return;
        isSyncing = true;
        try {
            const r = await fetch(`/api/get/${myName}/${target}?last=${lastId}`);
            const data = await r.json();
            const f = document.getElementById('feed');
            
            data.forEach(m => {
                if(m.id > lastId) {
                    lastId = m.id;
                    const div = document.createElement('div');
                    div.className = `msg ${m.sender === myName ? 'out' : 'in'}`;
                    
                    let contentBody = m.type === 'img' ? 
                        `<img src="${m.file}" onclick="window.open(this.src)" style="max-width:100%; border-radius:12px; cursor:pointer; display:block; margin-top:5px;">` : 
                        `<span>${m.content}</span>`;
                    
                    div.innerHTML = `
                        <div class="msg-info"><span>${m.sender}</span></div>
                        ${contentBody}
                        <div class="time">${m.timestamp}</div>
                    `;
                    f.appendChild(div);
                    f.scrollTop = f.scrollHeight;
                    
                    if(m.sender !== myName) {
                        document.getElementById('snd_in').play().catch(()=>{});
                        if(document.hidden) {
                            new Notification("TegeGrom", { body: `${m.sender}: ${m.content.substring(0, 40)}...` });
                        }
                    }
                }
            });
        } catch(e) {
        } finally { isSyncing = false; }
    }

    function upFile() {
        const file = document.getElementById('f-in').files[0];
        if(!file) return;
        const reader = new FileReader();
        reader.onload = () => send('img', '', reader.result);
        reader.readAsDataURL(file);
    }

    // Фикс для клавиатуры на мобилках
    window.visualViewport.addEventListener('resize', () => {
        document.getElementById('feed').scrollTop = document.getElementById('feed').scrollHeight;
    });
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
