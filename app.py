import sqlite3
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

# --- СИСТЕМА ДАННЫХ ---
def get_db():
    conn = sqlite3.connect('zenith_pro.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, avatar TEXT DEFAULT "https://cdn-icons-png.flaticon.com/512/149/149071.png")')
    db.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT, receiver TEXT, text TEXT, time TEXT, type TEXT DEFAULT "text")''')
    db.commit()
    db.close()

init_db()

class AuthData(BaseModel):
    username: str
    password: str
    avatar: str = ""

# --- ИНТЕРФЕЙС (ZENITH PRO MAX) ---
HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
    <title>TG-OS Zenith Pro</title>
    <style>
        :root {
            --accent: #00aff0; --bg: #0b0e11; --glass: rgba(23, 33, 43, 0.8);
            --msg-in: #182533; --msg-out: #2b5278; --text: #f5f5f5;
        }

        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; outline: none; }
        body, html { 
            margin: 0; padding: 0; height: 100%; width: 100%; 
            background: var(--bg); color: var(--text); 
            font-family: 'Segoe UI', system-ui, sans-serif; overflow: hidden;
        }

        /* Логотипы и Брендинг */
        .os-badge { font-size: 10px; font-weight: bold; color: var(--accent); letter-spacing: 1px; text-transform: uppercase; }
        .watermark { position: fixed; bottom: 10px; right: 10px; opacity: 0.2; pointer-events: none; font-size: 12px; z-index: 100; }

        /* Вход */
        #auth { 
            position: fixed; inset: 0; z-index: 5000; 
            background: radial-gradient(circle at center, #1e293b, #0b0e11);
            display: flex; align-items: center; justify-content: center;
        }
        .auth-card {
            width: 90%; max-width: 400px; padding: 35px;
            background: var(--glass); backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.1); border-radius: 35px;
            text-align: center; box-shadow: 0 25px 50px rgba(0,0,0,0.5);
        }

        /* Контейнер приложения */
        #app { display: none; height: 100%; width: 100%; }
        
        /* Боковая панель (Поиск + Юзеры) */
        .sidebar {
            width: 380px; background: var(--glass); backdrop-filter: blur(15px);
            border-right: 1px solid rgba(255,255,255,0.05); display: flex; flex-direction: column;
        }
        .sb-head { padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .search-box {
            width: 100%; padding: 12px 15px; border-radius: 12px;
            background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);
            color: white; font-size: 14px; margin-top: 10px;
        }

        .user-list { flex: 1; overflow-y: auto; }
        .u-item {
            padding: 15px 20px; display: flex; align-items: center; gap: 15px;
            cursor: pointer; transition: 0.2s; border-bottom: 1px solid rgba(255,255,255,0.02);
        }
        .u-item:hover { background: rgba(255,255,255,0.05); }
        .u-item.active { background: rgba(0, 175, 240, 0.15); border-right: 3px solid var(--accent); }
        .pfp { width: 50px; height: 50px; border-radius: 50%; object-fit: cover; background: #334155; border: 2px solid rgba(255,255,255,0.1); }

        /* Окно чата */
        .chat-main { flex: 1; display: flex; flex-direction: column; position: relative; background: #0e1114; }
        .chat-header {
            height: 70px; background: var(--glass); backdrop-filter: blur(15px);
            display: flex; align-items: center; padding: 0 20px; justify-content: space-between;
            border-bottom: 1px solid rgba(255,255,255,0.05); z-index: 10;
        }
        
        #msgs { 
            flex: 1; overflow-y: auto; padding: 20px; display: flex; 
            flex-direction: column; gap: 12px; background: url('https://web.telegram.org/a/chat-bg-pattern-dark.ad383614.png');
            background-size: 450px;
        }

        .m {
            max-width: 70%; padding: 10px 15px; border-radius: 18px;
            font-size: 15px; position: relative; animation: mShow 0.2s ease-out;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        @keyframes mShow { from{opacity:0; transform:scale(0.9);} to{opacity:1; transform:scale(1);} }
        .m.in { align-self: flex-start; background: var(--msg-in); border-bottom-left-radius: 4px; }
        .m.out { align-self: flex-end; background: var(--msg-out); border-bottom-right-radius: 4px; }

        /* Подвал */
        .chat-input-area {
            padding: 15px 20px; background: var(--glass); backdrop-filter: blur(20px);
            display: flex; align-items: center; gap: 10px; border-top: 1px solid rgba(255,255,255,0.05);
        }
        .input-wrap { flex: 1; position: relative; }
        #m-in { width: 100%; height: 48px; border-radius: 24px; padding: 0 20px; background: #0b0e11; border: 1px solid #242f3d; color: white; font-size: 16px; }
        .icon-btn { width: 48px; height: 48px; border-radius: 50%; background: var(--accent); border: none; color: white; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .icon-btn.secondary { background: rgba(255,255,255,0.05); font-size: 18px; }

        /* Адаптив */
        @media (max-width: 850px) {
            .sidebar { width: 100%; }
            body.chat-active .sidebar { display: none; }
            body.chat-active .chat-main { display: flex; }
            .chat-main { display: none; }
            .back-btn { display: flex !important; }
        }
    </style>
</head>
<body>
    <div class="watermark">POWERED BY TG-OS ZENITH 2026</div>

    <div id="auth">
        <div class="auth-card">
            <div class="os-badge">TegeGrom System v4.0</div>
            <h1 style="margin:10px 0 30px 0; font-size:36px; letter-spacing:-1px;">Zenith Pro</h1>
            <input type="text" id="au-u" placeholder="Никнейм">
            <input type="password" id="au-p" placeholder="Пароль">
            <input type="text" id="au-a" placeholder="URL аватара (необязательно)">
            <button class="btn" onclick="login()">ЗАПУСТИТЬ СИСТЕМУ</button>
        </div>
    </div>

    <div id="app">
        <div class="sidebar">
            <div class="sb-head">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="font-size:20px;">TG-OS</b>
                    <span class="os-badge">Online</span>
                </div>
                <input type="text" id="search-u" class="search-box" placeholder="🔍 Поиск по никнейму..." oninput="renderUsers()">
            </div>
            <div class="user-list" id="u-list"></div>
        </div>

        <div class="chat-main">
            <div class="chat-header">
                <div style="display:flex; align-items:center; gap:12px;">
                    <button class="icon-btn secondary back-btn" onclick="document.body.classList.remove('chat-active')" style="display:none; width:40px; height:40px;">⬅</button>
                    <img id="c-pfp" class="pfp" src="https://cdn-icons-png.flaticon.com/512/149/149071.png">
                    <div>
                        <b id="c-name" style="font-size:18px;">Общий чат</b><br>
                        <span style="font-size:11px; color:var(--accent);">Zenith Secure Line</span>
                    </div>
                </div>
                <div style="display:flex; gap:10px;">
                    <div class="icon-btn secondary" onclick="alert('Вызов...')">📞</div>
                    <div class="icon-btn secondary" id="god-btn" style="display:none;" onclick="adminPanel()">⚙️</div>
                </div>
            </div>

            <div id="msgs"></div>

            <div class="chat-input-area">
                <button class="icon-btn secondary" onclick="attachMedia()">➕</button>
                <div class="input-wrap">
                    <input type="text" id="m-in" placeholder="Сообщение..." onkeypress="if(event.key==='Enter') sendM()">
                </div>
                <button class="icon-btn secondary" id="mic" onclick="voiceM()">🎤</button>
                <button class="icon-btn" onclick="sendM()">➤</button>
            </div>
        </div>
    </div>

    <script>
        let me = localStorage.getItem('tg_pro_u') || "";
        let target = "all";
        let userCache = [];
        let lastMsgLen = -1;
        let isRec = false;
        let mediaRec;
        let chunks = [];

        async function login() {
            const u = document.getElementById('au-u').value;
            const p = document.getElementById('au-p').value;
            const a = document.getElementById('au-a').value || "https://cdn-icons-png.flaticon.com/512/149/149071.png";
            if(!u || !p) return;
            await fetch('/auth', {method:'POST', headers:{'Content-Type':'application/json'}, 
                body:JSON.stringify({username:u, password:p, avatar:a})});
            localStorage.setItem('tg_pro_u', u);
            location.reload();
        }

        async function init() {
            if(!me) return;
            document.getElementById('auth').style.display = 'none';
            document.getElementById('app').style.display = 'flex';
            if(me === 'kupriz') document.getElementById('god-btn').style.display = 'flex';
            
            await loadUsers();
            setInterval(loadUsers, 5000);
            setInterval(sync, 1000);
        }

        async function loadUsers() {
            const r = await fetch('/users');
            userCache = await r.json();
            renderUsers();
        }

        function renderUsers() {
            const q = document.getElementById('search-u').value.toLowerCase();
            const list = document.getElementById('u-list');
            let html = `<div class="u-item ${target==='all'?'active':''}" onclick="setT('all','https://cdn-icons-png.flaticon.com/512/149/149071.png','Общий чат')">
                <div class="ava" style="background:var(--accent)">📢</div><b>Общий чат</b></div>`;
            
            userCache.filter(u => u.username !== me && u.username.toLowerCase().includes(q)).forEach(u => {
                html += `<div class="u-item ${target===u.username?'active':''}" onclick="setT('${u.username}','${u.avatar}','${u.username}')">
                    <img class="pfp" src="${u.avatar}"><b>${u.username}</b></div>`;
            });
            list.innerHTML = html;
        }

        function setT(t, a, name) {
            target = t;
            document.getElementById('c-pfp').src = a;
            document.getElementById('c-name').innerText = name;
            document.body.classList.add('chat-active');
            lastMsgLen = -1;
            renderUsers();
            sync();
        }

        async function sendM(type="text", content=null) {
            const inp = document.getElementById('m-in');
            const val = content || inp.value;
            if(!val.trim() && type!=='voice') return;
            await fetch('/send', {method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({sender:me, receiver:target, text:val, type:type})});
            inp.value = "";
            sync();
        }

        async function sync() {
            const r = await fetch(`/get_msgs/${me}/${target}`);
            const data = await r.json();
            if(data.length === lastMsgLen) return;
            const box = document.getElementById('msgs');
            box.innerHTML = data.map(m => {
                let body = m.text;
                if(m.type==='photo') body = `<img src="${m.text}" style="max-width:100%; border-radius:15px; border:1px solid rgba(255,255,255,0.1)">`;
                if(m.type==='video') body = `<video controls style="width:100%; border-radius:15px;"><source src="${m.text}"></video>`;
                if(m.type==='voice') body = `<audio controls src="${m.text}" style="width:100%; min-width:220px;"></audio>`;
                
                const del = (m.sender===me || me==='kupriz') ? `<span onclick="dropM(${m.id})" style="cursor:pointer;opacity:0.3;margin-left:8px;">🗑️</span>` : '';
                
                return `<div class="m ${m.sender===me?'out':'in'}">
                    ${target==='all'&&m.sender!==me?`<div style="font-size:11px;color:var(--accent);font-weight:bold;margin-bottom:4px;">${m.sender}</div>`:''}
                    ${body}
                    <div style="font-size:10px; opacity:0.5; text-align:right; margin-top:5px;">${m.time} ${del}</div>
                </div>`;
            }).join('');
            box.scrollTop = box.scrollHeight;
            lastMsgLen = data.length;
        }

        function attachMedia() {
            const m = prompt("1 - Фото, 2 - Видео (вставь URL)");
            const url = prompt("Вставь прямую ссылку:");
            if(!url) return;
            if(m === "1") sendM('photo', url);
            if(m === "2") sendM('video', url);
        }

        async function voiceM() {
            const mic = document.getElementById('mic');
            if(!isRec) {
                const s = await navigator.mediaDevices.getUserMedia({audio:true});
                mediaRec = new MediaRecorder(s);
                chunks = [];
                mediaRec.ondataavailable = e => chunks.push(e.data);
                mediaRec.onstop = async () => {
                    const blob = new Blob(chunks, {type:'audio/ogg'});
                    const reader = new FileReader();
                    reader.readAsDataURL(blob);
                    reader.onloadend = () => sendM('voice', reader.result);
                };
                mediaRec.start();
                mic.style.background = '#ff3b30';
                isRec = true;
            } else {
                mediaRec.stop();
                mic.style.background = 'rgba(255,255,255,0.05)';
                isRec = false;
            }
        }

        async function dropM(id) { await fetch(`/del_m/${id}`, {method:'DELETE'}); lastMsgLen=-1; sync(); }
        
        function adminPanel() {
            const a = prompt("ADMIN: 1-Снести базу, 2-Удалить юзера");
            if(a==="1") fetch('/admin/wipe', {method:'POST'}).then(()=>location.reload());
            if(a==="2") { const u = prompt("Ник:"); fetch('/admin/ban/'+u, {method:'DELETE'}).then(()=>location.reload()); }
        }

        init();
    </script>
</body>
</html>
"""

# --- БЭКЕНД (FASTAPI + SQLITE) ---
@app.get("/", response_class=HTMLResponse)
async def home(): return HTML

@app.post("/auth")
async def auth(d: AuthData):
    db = get_db()
    db.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)", (d.username, d.password, d.avatar))
    db.execute("UPDATE users SET avatar=? WHERE username=? AND password=?", (d.avatar, d.username, d.password))
    db.commit(); db.close()
    return {"ok":True}

@app.get("/users")
async def get_users():
    db = get_db(); res = [dict(r) for r in db.execute("SELECT username, avatar FROM users").fetchall()]; db.close()
    return res

@app.post("/send")
async def send(m: dict):
    db = get_db()
    db.execute("INSERT INTO messages (sender, receiver, text, time, type) VALUES (?,?,?,?,?)",
               (m['sender'], m['receiver'], m['text'], datetime.now().strftime("%H:%M"), m.get('type','text')))
    db.commit(); db.close()
    return {"ok":True}

@app.get("/get_msgs/{u1}/{u2}")
async def get_msgs(u1: str, u2: str):
    db = get_db()
    if u2 == "all": res = db.execute("SELECT * FROM messages WHERE receiver='all' ORDER BY id ASC").fetchall()
    else: res = db.execute("SELECT * FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC", (u1, u2, u2, u1)).fetchall()
    db.close()
    return [dict(r) for r in res]

@app.delete("/del_m/{id}")
async def del_m(id: int):
    db = get_db(); db.execute("DELETE FROM messages WHERE id=?", (id,)); db.commit(); db.close()
    return {"ok":True}

@app.post("/admin/wipe")
async def wipe():
    db = get_db(); db.execute("DELETE FROM messages"); db.commit(); db.close()
    return {"ok":True}

@app.delete("/admin/ban/{u}")
async def ban(u: str):
    db = get_db()
    db.execute("DELETE FROM users WHERE username=?", (u,))
    db.execute("DELETE FROM messages WHERE sender=? OR receiver=?", (u,u))
    db.commit(); db.close()
    return {"ok":True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
