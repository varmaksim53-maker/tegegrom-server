import sqlite3
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

# --- СИСТЕМА БАЗЫ ДАННЫХ (НЕ ТРОГАТЬ) ---
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

# --- ВЕСЬ ВИЗУАЛ И СКРИПТЫ (ВЕРНУЛ ВСЁ ДО ПОСЛЕДНЕГО ПИКСЕЛЯ) ---
USER_INTERFACE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
    <title>TG-OS Zenith Pro Max</title>
    <style>
        :root {
            --accent: #00aff0; --bg: #080a0c; --glass: rgba(23, 33, 43, 0.7);
            --msg-in: rgba(36, 55, 78, 0.8); --msg-out: rgba(43, 82, 120, 0.9);
            --text: #f5f5f5; --admin-red: #ff3b30;
        }

        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; outline: none; }
        body, html { 
            margin: 0; padding: 0; height: 100%; width: 100%; 
            background: var(--bg); color: var(--text); 
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            overflow: hidden;
        }

        /* ЖИВОЙ АНИМИРОВАННЫЙ ФОН */
        .bg-anim {
            position: fixed; inset: 0; z-index: -1;
            background: linear-gradient(45deg, #0f172a, #1e1b4b, #312e81, #0f172a);
            background-size: 400% 400%;
            animation: gradientBG 15s ease infinite;
        }
        @keyframes gradientBG { 0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;} }

        .watermark { position: fixed; bottom: 10px; right: 10px; opacity: 0.2; font-size: 10px; pointer-events: none; z-index: 100; }

        /* ОКНО ВХОДА */
        #auth { 
            position: fixed; inset: 0; z-index: 5000; 
            display: flex; align-items: center; justify-content: center;
            backdrop-filter: blur(25px); background: rgba(0,0,0,0.6);
        }
        .auth-card {
            width: 90%; max-width: 400px; padding: 40px;
            background: var(--glass); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 35px; text-align: center; box-shadow: 0 25px 50px rgba(0,0,0,0.5);
        }
        .auth-card input {
            width: 100%; padding: 15px; margin: 10px 0; border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.4);
            color: white; font-size: 16px;
        }
        .login-btn {
            width: 100%; padding: 15px; border-radius: 15px; border: none;
            background: var(--accent); color: white; font-weight: bold; cursor: pointer;
            margin-top: 15px; transition: 0.3s;
        }

        /* ГЛАВНЫЙ ИНТЕРФЕЙС */
        #app { display: none; height: 100%; width: 100%; }
        
        .sidebar {
            width: 380px; background: var(--glass); backdrop-filter: blur(20px);
            border-right: 1px solid rgba(255,255,255,0.05); display: flex; flex-direction: column;
        }
        .sb-header { padding: 25px 20px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .search-input {
            width: 100%; padding: 12px; border-radius: 12px; background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1); color: white; margin-top: 10px;
        }

        .user-list { flex: 1; overflow-y: auto; }
        .u-item {
            padding: 15px 20px; display: flex; align-items: center; gap: 15px;
            cursor: pointer; transition: 0.2s; border-bottom: 1px solid rgba(255,255,255,0.02);
        }
        .u-item:hover { background: rgba(255,255,255,0.05); }
        .u-item.active { background: rgba(0, 175, 240, 0.15); border-right: 3px solid var(--accent); }
        .pfp { width: 50px; height: 50px; border-radius: 50%; object-fit: cover; border: 2px solid rgba(255,255,255,0.1); }

        /* ЧАТ */
        .chat-main { flex: 1; display: flex; flex-direction: column; background: rgba(10, 14, 18, 0.6); position: relative; }
        .chat-head {
            height: 75px; background: var(--glass); backdrop-filter: blur(20px);
            display: flex; align-items: center; padding: 0 25px; justify-content: space-between;
            border-bottom: 1px solid rgba(255,255,255,0.05); z-index: 10;
        }

        #msgs { 
            flex: 1; overflow-y: auto; padding: 25px; display: flex; 
            flex-direction: column; gap: 15px; 
            background: url('https://web.telegram.org/a/chat-bg-pattern-dark.ad383614.png');
            background-size: 500px;
        }

        .m {
            max-width: 75%; padding: 12px 18px; border-radius: 20px;
            font-size: 15px; line-height: 1.5; position: relative;
            animation: messagePop 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        @keyframes messagePop { from {opacity: 0; transform: scale(0.8) translateY(20px);} to {opacity: 1; transform: scale(1) translateY(0);} }
        
        .m.in { align-self: flex-start; background: var(--msg-in); border-bottom-left-radius: 5px; }
        .m.out { align-self: flex-end; background: var(--msg-out); border-bottom-right-radius: 5px; }
        .m-info { font-size: 10px; opacity: 0.6; margin-top: 6px; display: flex; justify-content: flex-end; align-items: center; gap: 5px; }

        /* ПАНЕЛЬ ВВОДА */
        .chat-input-bar {
            padding: 20px; background: var(--glass); backdrop-filter: blur(20px);
            display: flex; align-items: center; gap: 12px; border-top: 1px solid rgba(255,255,255,0.05);
        }
        .input-box { flex: 1; height: 50px; border-radius: 25px; background: #0b0e11; border: 1px solid #242f3d; color: white; padding: 0 20px; font-size: 16px; }
        .action-btn { width: 50px; height: 50px; border-radius: 50%; background: var(--accent); border: none; color: white; font-size: 22px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: 0.2s; }
        .action-btn:active { transform: scale(0.9); }
        .action-btn.sec { background: rgba(255,255,255,0.05); font-size: 18px; }

        @media (max-width: 850px) {
            .sidebar { width: 100%; }
            body.in-chat .sidebar { display: none; }
            body.in-chat .chat-main { display: flex; }
            .chat-main { display: none; }
            .back-node { display: flex !important; }
        }
    </style>
</head>
<body id="body-main">
    <div class="bg-anim"></div>
    <div class="watermark">TG-OS ZENITH PRO MAX v5.1</div>

    <div id="auth">
        <div class="auth-card">
            <h1 style="margin:0; font-size:38px; letter-spacing:-2px; color:var(--accent);">Zenith</h1>
            <p style="opacity:0.5; margin-bottom:30px;">Система управления TegeGrom</p>
            <input type="text" id="au-u" placeholder="Никнейм (Логин)">
            <input type="password" id="au-p" placeholder="Пароль">
            <input type="text" id="au-a" placeholder="URL аватара (Опционально)">
            <button class="login-btn" onclick="login()">ЗАПУСТИТЬ ТЕРМИНАЛ</button>
        </div>
    </div>

    <div id="app">
        <div class="sidebar">
            <div class="sb-header">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="font-size:22px; letter-spacing:1px;">TG-OS</b>
                    <div style="width:10px; height:10px; border-radius:50%; background:#10b981; box-shadow:0 0 10px #10b981;"></div>
                </div>
                <input type="text" id="search-u" class="search-input" placeholder="🔍 Поиск по никнейму..." oninput="renderUsers()">
            </div>
            <div class="user-list" id="u-list"></div>
        </div>

        <div class="chat-main">
            <div class="chat-head">
                <div style="display:flex; align-items:center; gap:15px;">
                    <button class="action-btn sec back-node" onclick="document.body.classList.remove('in-chat')" style="display:none; width:40px; height:40px;">⬅</button>
                    <img id="c-pfp" class="pfp" src="https://cdn-icons-png.flaticon.com/512/149/149071.png">
                    <div>
                        <b id="c-name" style="font-size:18px;">Общий чат</b><br>
                        <span style="font-size:11px; color:var(--accent);">Защищенный канал</span>
                    </div>
                </div>
                <div style="display:flex; gap:10px;">
                    <div class="action-btn sec" style="width:40px; height:40px;" onclick="location.href='/master-control-panel'">⚙️</div>
                </div>
            </div>

            <div id="msgs"></div>

            <div class="chat-input-bar">
                <button class="action-btn sec" onclick="mediaMenu()">➕</button>
                <input type="text" id="m-in" class="input-box" placeholder="Написать сообщение..." onkeypress="if(event.key==='Enter') sendM()">
                <button class="action-btn sec" id="mic" onclick="voiceM()">🎤</button>
                <button class="action-btn" onclick="sendM()">➤</button>
            </div>
        </div>
    </div>

    <script>
        let me = localStorage.getItem('tg_pro_u') || "";
        let target = "all"; let userCache = []; let lastL = -1;
        let isRec = false; let mediaRec; let chunks = [];

        async function login() {
            const u = document.getElementById('au-u').value;
            const p = document.getElementById('au-p').value;
            const a = document.getElementById('au-a').value || "https://cdn-icons-png.flaticon.com/512/149/149071.png";
            if(!u || !p) return;
            await fetch('/auth', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:u, password:p, avatar:a})});
            localStorage.setItem('tg_pro_u', u); location.reload();
        }

        async function init() {
            if(!me) return;
            document.getElementById('auth').style.display = 'none';
            document.getElementById('app').style.display = 'flex';
            await loadUsers(); setInterval(loadUsers, 5000); setInterval(sync, 1000);
        }

        async function loadUsers() {
            const r = await fetch('/users'); userCache = await r.json(); renderUsers();
        }

        function renderUsers() {
            const q = document.getElementById('search-u').value.toLowerCase();
            const list = document.getElementById('u-list');
            let html = `<div class="u-item ${target==='all'?'active':''}" onclick="setT('all','https://cdn-icons-png.flaticon.com/512/149/149071.png','Общий чат')">
                <div class="pfp" style="background:var(--accent); display:flex; align-items:center; justify-content:center; font-size:20px;">📢</div><b>Общий чат</b></div>`;
            
            userCache.filter(u => u.username !== me && u.username.toLowerCase().includes(q)).forEach(u => {
                html += `<div class="u-item ${target===u.username?'active':''}" onclick="setT('${u.username}','${u.avatar}','${u.username}')">
                    <img class="pfp" src="${u.avatar}"><b>${u.username}</b></div>`;
            });
            list.innerHTML = html;
        }

        function setT(t, a, n) { 
            target = t; document.getElementById('c-pfp').src = a; document.getElementById('c-name').innerText = n; 
            document.body.classList.add('in-chat'); lastL = -1; renderUsers(); sync(); 
        }

        async function sendM(type="text", content=null) {
            const val = content || document.getElementById('m-in').value;
            if(!val.trim() && type!=='voice') return;
            await fetch('/send', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({sender:me, receiver:target, text:val, type:type})});
            document.getElementById('m-in').value = ""; sync();
        }

        async function sync() {
            const r = await fetch(`/get_msgs/${me}/${target}`); const data = await r.json();
            if(data.length === lastL) return;
            const box = document.getElementById('msgs');
            box.innerHTML = data.map(m => {
                let body = m.text;
                if(m.type==='photo') body = `<img src="${m.text}" style="max-width:100%; border-radius:15px; margin-top:5px;">`;
                if(m.type==='video') body = `<video controls style="width:100%; border-radius:15px; margin-top:5px;"><source src="${m.text}"></video>`;
                if(m.type==='voice') body = `<audio controls src="${m.text}" style="width:100%; margin-top:5px;"></audio>`;
                
                const isAdmin = (me.toLowerCase() === 'kupriz');
                const delBtn = (m.sender === me || isAdmin) ? `<span onclick="dropM(${m.id})" style="cursor:pointer; color:var(--admin-red); font-weight:bold; margin-left:10px;">[УДАЛИТЬ]</span>` : '';
                
                return `<div class="m ${m.sender===me?'out':'in'}">
                    <b style="font-size:11px; color:var(--accent);">${m.sender}</b><br>${body}
                    <div class="m-info">${m.time} ${delBtn}</div>
                </div>`;
            }).join('');
            box.scrollTop = box.scrollHeight; lastL = data.length;
        }

        function mediaMenu() {
            const t = prompt("1 - Фото, 2 - Видео (вставь прямую ссылку)");
            const u = prompt("Вставь URL:");
            if(u) sendM(t==="1"?'photo':'video', u);
        }

        async function dropM(id) { await fetch(`/del_m/${id}`, {method:'DELETE'}); lastL=-1; sync(); }

        async function voiceM() {
            const btn = document.getElementById('mic');
            if(!isRec) {
                const s = await navigator.mediaDevices.getUserMedia({audio:true});
                mediaRec = new MediaRecorder(s); chunks = [];
                mediaRec.ondataavailable = e => chunks.push(e.data);
                mediaRec.onstop = async () => {
                    const blob = new Blob(chunks, {type:'audio/ogg'});
                    const reader = new FileReader(); reader.readAsDataURL(blob);
                    reader.onloadend = () => sendM('voice', reader.result);
                };
                mediaRec.start(); btn.style.background = '#ff3b30'; isRec = true;
            } else { mediaRec.stop(); btn.style.background = 'rgba(255,255,255,0.05)'; isRec = false; }
        }
        init();
    </script>
</body>
</html>
"""

# --- ИНТЕРФЕЙС АДМИНКИ (Mission Control) ---
ADMIN_INTERFACE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>TG-OS | MISSION CONTROL</title>
    <style>
        :root { --danger: #ff3b30; --accent: #00aff0; --bg: #05070a; }
        body { background: var(--bg); color: #e5e7eb; font-family: sans-serif; margin: 0; display: flex; height: 100vh; }
        .nav { width: 280px; background: #0f172a; padding: 30px; border-right: 1px solid #1e293b; }
        .content { flex: 1; padding: 40px; overflow-y: auto; }
        .card { background: #111827; border: 1px solid #1f2937; border-radius: 20px; padding: 25px; margin-bottom: 25px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #1f2937; }
        .btn-red { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer; }
        textarea { width: 100%; background: #000; color: white; border: 1px solid var(--accent); padding: 15px; border-radius: 12px; font-size: 16px; }
        .stat { font-size: 30px; font-weight: bold; color: var(--accent); }
    </style>
</head>
<body>
    <div class="nav">
        <h1 style="color:var(--accent)">TG-OS MOD</h1>
        <p>Zenith Pro Master Panel</p>
        <hr style="opacity:0.1; margin:20px 0;">
        <button onclick="location.href='/'" style="width:100%; padding:12px; background:var(--accent); color:white; border:none; border-radius:10px; cursor:pointer;">ВЕРНУТЬСЯ В ЧАТ</button>
    </div>
    <div class="content">
        <div class="card">
            <h2 style="margin-top:0">🛰️ Глобальный Мегафон</h2>
            <textarea id="alert-text" rows="3" placeholder="Ваше сообщение для всех пользователей..."></textarea>
            <button onclick="broadcast()" style="width:100%; padding:15px; background:var(--accent); color:white; border:none; border-radius:10px; margin-top:15px; cursor:pointer; font-weight:bold;">ОТПРАВИТЬ ОБЪЯВЛЕНИЕ</button>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1.5fr; gap:25px;">
            <div class="card">
                <h3>👥 Пользователи</h3>
                <div id="u-count" class="stat">0</div>
                <table id="u-table" style="margin-top:20px;">
                    <thead><tr><th>Ник</th><th>Действие</th></tr></thead>
                    <tbody></tbody>
                </table>
            </div>
            <div class="card">
                <h3>📡 Лог трафика (Живой)</h3>
                <div id="m-count" class="stat">0</div>
                <table id="m-table" style="margin-top:20px;">
                    <thead><tr><th>От</th><th>Текст / Тип</th><th>X</th></tr></thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    </div>
    <script>
        async function update() {
            const s = await (await fetch('/stats')).json();
            document.getElementById('u-count').innerText = s.u;
            document.getElementById('m-count').innerText = s.m;

            const u = await (await fetch('/users')).json();
            document.querySelector('#u-table tbody').innerHTML = u.map(user => `<tr><td><b>${user.username}</b></td><td><button class="btn-red" onclick="ban('${user.username}')">BAN</button></td></tr>`).join('');
            
            const m = await (await fetch('/get_msgs/all/all')).json();
            document.querySelector('#m-table tbody').innerHTML = m.reverse().slice(0,30).map(msg => `<tr><td>${msg.sender}</td><td style="opacity:0.8">${msg.text.substring(0,40)}... [${msg.type}]</td><td><button class="btn-red" onclick="drop(${msg.id})">❌</button></td></tr>`).join('');
        }
        async function ban(u) { if(confirm('Стереть аккаунт '+u+'?')) await fetch('/admin/ban/'+u, {method:'DELETE'}); update(); }
        async function drop(id) { await fetch('/del_m/'+id, {method:'DELETE'}); update(); }
        async function broadcast() {
            const t = document.getElementById('alert-text').value; if(!t) return;
            await fetch('/send', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({sender:'🛰️ SYSTEM', receiver:'all', text: '📢 ' + t, type:'text'})});
            document.getElementById('alert-text').value=''; alert('Разослано!'); update();
        }
        setInterval(update, 3000); update();
    </script>
</body>
</html>
"""

# --- BACKEND (API РУЧКИ) ---

@app.get("/", response_class=HTMLResponse)
async def home(): return USER_INTERFACE

@app.get("/master-control-panel", response_class=HTMLResponse)
async def admin_page(): return ADMIN_INTERFACE

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
    elif u1 == "all" and u2 == "all": res = db.execute("SELECT * FROM messages ORDER BY id ASC").fetchall()
    else: res = db.execute("SELECT * FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC", (u1, u2, u2, u1)).fetchall()
    db.close()
    return [dict(r) for r in res]

@app.delete("/del_m/{id}")
async def del_m(id: int):
    db = get_db(); db.execute("DELETE FROM messages WHERE id=?", (id,)); db.commit(); db.close()
    return {"ok":True}

@app.get("/stats")
async def stats():
    db = get_db()
    u = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    m = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    db.close()
    return {"u": u, "m": m}

@app.delete("/admin/ban/{u}")
async def ban(u: str):
    db = get_db()
    db.execute("DELETE FROM users WHERE username=?", (u,))
    db.execute("DELETE FROM messages WHERE sender=? OR receiver=?", (u,u))
    db.commit(); db.close()
    return {"ok":True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
