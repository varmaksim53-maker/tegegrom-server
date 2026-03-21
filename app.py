import sqlite3
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

# --- СЕРВЕРНАЯ БАЗА ДАННЫХ ---
def get_db():
    conn = sqlite3.connect('zenith_pro.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            password TEXT, 
            avatar TEXT DEFAULT "https://cdn-icons-png.flaticon.com/512/149/149071.png"
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT, 
            receiver TEXT, 
            text TEXT, 
            time TEXT, 
            type TEXT DEFAULT "text"
        )
    ''')
    db.commit()
    db.close()

init_db()

class AuthData(BaseModel):
    username: str
    password: str
    avatar: str = ""

# --- ВЕСЬ ВИЗУАЛЬНЫЙ ИНТЕРФЕЙС (HTML + CSS + JS) ---
USER_INTERFACE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>TG-OS Zenith Pro Max</title>
    <style>
        :root {
            --accent: #00aff0;
            --bg: #080a0c;
            --glass: rgba(23, 33, 43, 0.75);
            --msg-in: rgba(36, 55, 78, 0.85);
            --msg-out: rgba(43, 82, 120, 0.95);
            --text: #ffffff;
            --admin-red: #ff3b30;
        }

        * { 
            box-sizing: border-box; 
            -webkit-tap-highlight-color: transparent; 
            outline: none; 
        }

        body, html { 
            margin: 0; 
            padding: 0; 
            height: 100%; 
            width: 100%; 
            background: var(--bg); 
            color: var(--text); 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; 
            overflow: hidden; 
        }

        /* АНИМИРОВАННЫЙ ФОН */
        .bg-layer {
            position: fixed;
            inset: 0;
            z-index: -1;
            background: linear-gradient(125deg, #0f172a, #1e1b4b, #312e81, #020617);
            background-size: 400% 400%;
            animation: moveGradient 15s ease infinite;
        }
        @keyframes moveGradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* АВТОРИЗАЦИЯ */
        #auth-screen {
            position: fixed;
            inset: 0;
            z-index: 9999;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(30px);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .auth-container {
            width: 90%;
            max-width: 420px;
            padding: 40px;
            background: var(--glass);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 40px;
            text-align: center;
            box-shadow: 0 30px 60px rgba(0,0,0,0.6);
        }
        .auth-container h1 { font-size: 42px; margin-bottom: 10px; color: var(--accent); letter-spacing: -1px; }
        .auth-container input {
            width: 100%;
            padding: 16px;
            margin: 12px 0;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.5);
            color: white;
            font-size: 16px;
        }
        .btn-login {
            width: 100%;
            padding: 18px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 18px;
            font-weight: bold;
            font-size: 18px;
            cursor: pointer;
            margin-top: 20px;
            transition: 0.3s;
        }
        .btn-login:hover { filter: brightness(1.2); transform: translateY(-2px); }

        /* ОСНОВНОЙ ПОРТ */
        #main-viewport {
            display: none;
            height: 100vh;
            width: 100vw;
        }

        .side-panel {
            width: 380px;
            background: var(--glass);
            backdrop-filter: blur(25px);
            border-right: 1px solid rgba(255,255,255,0.05);
            display: flex;
            flex-direction: column;
        }

        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: rgba(10, 14, 18, 0.4);
            position: relative;
        }

        .header {
            height: 80px;
            padding: 0 25px;
            background: var(--glass);
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }

        /* СПИСОК ЮЗЕРОВ */
        .u-list { flex: 1; overflow-y: auto; }
        .u-card {
            padding: 18px 25px;
            display: flex;
            align-items: center;
            gap: 15px;
            cursor: pointer;
            transition: 0.3s;
            border-bottom: 1px solid rgba(255,255,255,0.03);
        }
        .u-card:hover { background: rgba(255,255,255,0.05); }
        .u-card.active { background: rgba(0, 175, 240, 0.15); border-right: 4px solid var(--accent); }
        .avatar { width: 55px; height: 55px; border-radius: 50%; object-fit: cover; border: 2px solid rgba(255,255,255,0.1); }

        /* СООБЩЕНИЯ */
        #messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
            display: flex;
            flex-direction: column;
            gap: 18px;
            background: url('https://web.telegram.org/a/chat-bg-pattern-dark.ad383614.png');
            background-size: 500px;
        }

        .msg-bubble {
            max-width: 70%;
            padding: 14px 20px;
            border-radius: 22px;
            font-size: 15px;
            line-height: 1.4;
            position: relative;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            animation: slideUp 0.3s ease-out;
        }
        @keyframes slideUp { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }

        .msg-bubble.in { align-self: flex-start; background: var(--msg-in); border-bottom-left-radius: 5px; }
        .msg-bubble.out { align-self: flex-end; background: var(--msg-out); border-bottom-right-radius: 5px; }

        .msg-meta {
            font-size: 10px;
            opacity: 0.6;
            margin-top: 8px;
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 8px;
        }

        /* ПАНЕЛЬ ВВОДА */
        .input-bar {
            padding: 20px 30px;
            background: var(--glass);
            display: flex;
            align-items: center;
            gap: 15px;
            border-top: 1px solid rgba(255,255,255,0.05);
        }
        .main-input {
            flex: 1;
            height: 55px;
            border-radius: 28px;
            background: #0b0e11;
            border: 1px solid #242f3d;
            color: white;
            padding: 0 25px;
            font-size: 16px;
        }
        .btn-circle {
            width: 55px;
            height: 55px;
            border-radius: 50%;
            background: var(--accent);
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: 0.2s;
        }
        .btn-circle.secondary { background: rgba(255,255,255,0.05); font-size: 20px; }
        .btn-circle:active { transform: scale(0.9); }

        @media (max-width: 900px) {
            .side-panel { width: 100%; }
            body.chat-open .side-panel { display: none; }
            body.chat-open .chat-area { display: flex; }
            .chat-area { display: none; }
        }
    </style>
</head>
<body id="root-body">
    <div class="bg-layer"></div>

    <div id="auth-screen">
        <div class="auth-container">
            <h1>Zenith OS</h1>
            <p style="opacity:0.5; margin-bottom:25px;">Войдите в систему TegeGrom</p>
            <input type="text" id="auth-user" placeholder="Ваш никнейм">
            <input type="password" id="auth-pass" placeholder="Пароль">
            <input type="text" id="auth-ava" placeholder="Ссылка на аватар (не обязательно)">
            <button class="btn-login" onclick="handleLogin()">АВТОРИЗАЦИЯ</button>
        </div>
    </div>

    <div id="main-viewport">
        <div class="side-panel">
            <div style="padding:25px;">
                <b style="font-size:24px; color:var(--accent);">TG-OS PRO</b>
                <input type="text" id="user-search" class="main-input" style="width:100%; margin-top:15px; height:45px;" placeholder="Поиск юзеров..." oninput="drawUsers()">
            </div>
            <div class="u-list" id="users-box"></div>
        </div>

        <div class="chat-area">
            <div class="header">
                <div style="display:flex; align-items:center; gap:15px;">
                    <button class="btn-circle secondary" style="width:40px; height:40px; display:none;" id="back-btn" onclick="document.body.classList.remove('chat-open')">⬅</button>
                    <img id="chat-with-avatar" class="avatar" src="https://cdn-icons-png.flaticon.com/512/149/149071.png">
                    <div>
                        <b id="chat-with-name" style="font-size:20px;">Глобальный чат</b><br>
                        <span style="font-size:11px; color:#10b981;">● Online</span>
                    </div>
                </div>
                <button class="btn-circle secondary" style="width:45px; height:45px;" onclick="location.href='/master-control-panel'">🛰️</button>
            </div>

            <div id="messages-container"></div>

            <div class="input-bar">
                <button class="btn-circle secondary" onclick="openMedia()">📎</button>
                <input type="text" id="message-input" class="main-input" placeholder="Введите сообщение..." onkeypress="if(event.key==='Enter') performSend()">
                <button class="btn-circle secondary" id="voice-btn" onclick="toggleVoice()">🎤</button>
                <button class="btn-circle" onclick="performSend()">➤</button>
            </div>
        </div>
    </div>

    <script>
        let myNick = localStorage.getItem('tg_pro_u') || "";
        let chatTarget = "all"; 
        let cachedUsers = []; 
        let msgCount = -1;
        let recording = false; 
        let recorder; 
        let audioChunks = [];

        async function handleLogin() {
            const u = document.getElementById('auth-user').value;
            const p = document.getElementById('auth-pass').value;
            const a = document.getElementById('auth-ava').value || "https://cdn-icons-png.flaticon.com/512/149/149071.png";
            if(!u || !p) return alert("Заполните поля!");
            
            await fetch('/auth', {
                method:'POST', 
                headers:{'Content-Type':'application/json'}, 
                body:JSON.stringify({username:u, password:p, avatar:a})
            });
            
            localStorage.setItem('tg_pro_u', u);
            location.reload();
        }

        async function startup() {
            if(!myNick) return;
            document.getElementById('auth-screen').style.display = 'none';
            document.getElementById('main-viewport').style.display = 'flex';
            
            await syncUsers();
            setInterval(syncUsers, 5000);
            setInterval(syncMessages, 1000);
        }

        async function syncUsers() {
            const r = await fetch('/users');
            cachedUsers = await r.json();
            drawUsers();
        }

        function drawUsers() {
            const query = document.getElementById('user-search').value.toLowerCase();
            const container = document.getElementById('users-box');
            
            let html = `<div class="u-card ${chatTarget==='all'?'active':''}" onclick="switchTo('all','https://cdn-icons-png.flaticon.com/512/149/149071.png','Глобальный чат')">
                <div class="avatar" style="background:var(--accent); display:flex; align-items:center; justify-content:center; font-size:24px;">📢</div>
                <b>Глобальный чат</b>
            </div>`;

            cachedUsers.filter(u => u.username !== myNick && u.username.toLowerCase().includes(query)).forEach(u => {
                html += `<div class="u-card ${chatTarget===u.username?'active':''}" onclick="switchTo('${u.username}','${u.avatar}','${u.username}')">
                    <img class="avatar" src="${u.avatar}">
                    <b>${u.username}</b>
                </div>`;
            });
            container.innerHTML = html;
        }

        function switchTo(t, a, n) {
            chatTarget = t;
            document.getElementById('chat-with-avatar').src = a;
            document.getElementById('chat-with-name').innerText = n;
            document.body.classList.add('chat-open');
            msgCount = -1;
            drawUsers();
            syncMessages();
        }

        async function performSend(type="text", content=null) {
            const text = content || document.getElementById('message-input').value;
            if(!text.trim() && type === 'text') return;
            
            await fetch('/send', {
                method:'POST', 
                headers:{'Content-Type':'application/json'}, 
                body: JSON.stringify({sender:myNick, receiver:chatTarget, text:text, type:type})
            });
            
            document.getElementById('message-input').value = "";
            syncMessages();
        }

        async function syncMessages() {
            const r = await fetch(`/get_msgs/${myNick}/${chatTarget}`);
            const data = await r.json();
            if(data.length === msgCount) return;
            
            const box = document.getElementById('messages-container');
            box.innerHTML = data.map(m => {
                let content = m.text;
                if(m.type==='photo') content = `<img src="${m.text}" style="max-width:100%; border-radius:15px; margin-top:8px; box-shadow:0 5px 15px rgba(0,0,0,0.3);">`;
                if(m.type==='video') content = `<video controls style="width:100%; border-radius:15px; margin-top:8px;"><source src="${m.text}"></video>`;
                if(m.type==='voice') content = `<audio controls src="${m.text}" style="width:100%; margin-top:8px;"></audio>`;
                
                const isAdmin = (myNick.toLowerCase() === 'kupriz');
                const deleteAction = (m.sender === myNick || isAdmin) 
                    ? `<span onclick="deleteMsg(${m.id})" style="cursor:pointer; color:var(--admin-red); font-weight:bold; margin-left:12px;">УДАЛИТЬ</span>` 
                    : '';
                
                return `<div class="msg-bubble ${m.sender===myNick?'out':'in'}">
                    <b style="font-size:12px; color:var(--accent);">${m.sender}</b><br>
                    ${content}
                    <div class="msg-meta">${m.time} ${deleteAction}</div>
                </div>`;
            }).join('');
            
            box.scrollTop = box.scrollHeight;
            msgCount = data.length;
        }

        function openMedia() {
            const choice = prompt("Что отправить?\\n1 - Фото (URL)\\n2 - Видео (URL)");
            const link = prompt("Вставьте прямую ссылку:");
            if(link) performSend(choice === "1" ? 'photo' : 'video', link);
        }

        async function deleteMsg(id) {
            if(confirm("Удалить сообщение навсегда?")) {
                await fetch(`/del_m/${id}`, {method:'DELETE'});
                msgCount = -1;
                syncMessages();
            }
        }

        async function toggleVoice() {
            const btn = document.getElementById('voice-btn');
            if(!recording) {
                const stream = await navigator.mediaDevices.getUserMedia({audio:true});
                recorder = new MediaRecorder(stream);
                audioChunks = [];
                recorder.ondataavailable = e => audioChunks.push(e.data);
                recorder.onstop = async () => {
                    const blob = new Blob(audioChunks, {type:'audio/ogg'});
                    const reader = new FileReader();
                    reader.readAsDataURL(blob);
                    reader.onloadend = () => performSend('voice', reader.result);
                };
                recorder.start();
                btn.style.background = '#ff3b30';
                recording = true;
            } else {
                recorder.stop();
                btn.style.background = 'rgba(255,255,255,0.05)';
                recording = false;
            }
        }
        startup();
    </script>
</body>
</html>
"""

# --- ПАНЕЛЬ УПРАВЛЕНИЯ (ADMIN) ---
ADMIN_INTERFACE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>TG-OS | ПАНЕЛЬ УПРАВЛЕНИЯ</title>
    <script>
        // ЖЕСТКАЯ ПРОВЕРКА ПРАВ
        if (localStorage.getItem('tg_pro_u') !== 'kupriz') {
            alert('ДОСТУП ЗАПРЕЩЕН ДЛЯ ВСЕХ, КРОМЕ KUPRIZ!');
            window.location.href = "/";
        }
    </script>
    <style>
        :root { --danger: #ff3b30; --accent: #00aff0; --bg: #05070a; }
        body { background: var(--bg); color: #ffffff; font-family: sans-serif; margin: 0; padding: 40px; }
        .admin-card { background: #111827; border: 1px solid #1f2937; border-radius: 25px; padding: 30px; margin-bottom: 30px; }
        .back-link { color: var(--accent); text-decoration: none; font-weight: bold; margin-bottom: 20px; display: inline-block; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #1f2937; }
        .btn-ban { background: rgba(255, 59, 48, 0.2); color: var(--danger); border: 1px solid var(--danger); padding: 8px 16px; border-radius: 10px; cursor: pointer; }
        textarea { width: 100%; height: 100px; background: #000; color: #fff; border: 1px solid var(--accent); border-radius: 15px; padding: 15px; font-size: 16px; }
    </style>
</head>
<body>
    <a href="/" class="back-link">⬅ Вернуться в чат</a>
    <div class="admin-card">
        <h1 style="margin:0; color:var(--accent);">🛰️ Mission Control Panel</h1>
        <p style="opacity:0.5;">Добро пожаловать, Макс (Kupriz). Все системы онлайн.</p>
    </div>

    <div class="admin-card">
        <h3>📢 Рассылка Оповещения</h3>
        <textarea id="broadcast-msg" placeholder="Введите текст, который увидят все..."></textarea>
        <button onclick="sendAlert()" style="width:100%; padding:15px; background:var(--accent); color:white; border:none; border-radius:15px; margin-top:15px; font-weight:bold; cursor:pointer;">ОТПРАВИТЬ ВСЕМ</button>
    </div>

    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:30px;">
        <div class="admin-card">
            <h3>👥 Список Юзеров</h3>
            <table id="user-tbl">
                <thead><tr><th>Никнейм</th><th>Действие</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>
        <div class="admin-card">
            <h3>📡 Живой Трафик</h3>
            <table id="msg-tbl">
                <thead><tr><th>От</th><th>Текст</th><th>X</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>
    </div>

    <script>
        async function refresh() {
            const u = await (await fetch('/users')).json();
            document.querySelector('#user-tbl tbody').innerHTML = u.map(user => `
                <tr>
                    <td><b>${user.username}</b></td>
                    <td><button class="btn-ban" onclick="banUser('${user.username}')">БАН / УДАЛИТЬ</button></td>
                </tr>
            `).join('');

            const m = await (await fetch('/get_msgs/all/all')).json();
            document.querySelector('#msg-tbl tbody').innerHTML = m.reverse().slice(0,25).map(msg => `
                <tr>
                    <td>${msg.sender}</td>
                    <td style="opacity:0.7">${msg.text.substring(0,40)}...</td>
                    <td><button class="btn-ban" onclick="dropMsg(${msg.id})">❌</button></td>
                </tr>
            `).join('');
        }

        async function banUser(n) { if(confirm('Стереть юзера '+n+'?')) { await fetch('/admin/ban/'+n, {method:'DELETE'}); refresh(); } }
        async function dropMsg(id) { await fetch('/del_m/'+id, {method:'DELETE'}); refresh(); }
        async function sendAlert() {
            const t = document.getElementById('broadcast-msg').value; if(!t) return;
            await fetch('/send', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({sender:'🛰️ SYSTEM', receiver:'all', text: '📢 ВНИМАНИЕ: ' + t, type:'text'})});
            document.getElementById('broadcast-msg').value = ''; alert('Разослано!'); refresh();
        }
        setInterval(refresh, 3000); refresh();
    </script>
</body>
</html>
"""

# --- СЕРВЕРНАЯ ЧАСТЬ (FASTAPI) ---

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    return USER_INTERFACE

@app.get("/master-control-panel", response_class=HTMLResponse)
async def serve_admin():
    return ADMIN_INTERFACE

@app.post("/auth")
async def process_auth(data: AuthData):
    db = get_db()
    db.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)", (data.username, data.password, data.avatar))
    db.execute("UPDATE users SET avatar=? WHERE username=? AND password=?", (data.avatar, data.username, data.password))
    db.commit()
    db.close()
    return {"status":"success"}

@app.get("/users")
async def list_users():
    db = get_db()
    results = [dict(r) for r in db.execute("SELECT username, avatar FROM users").fetchall()]
    db.close()
    return results

@app.post("/send")
async def handle_send(msg: dict):
    db = get_db()
    db.execute(
        "INSERT INTO messages (sender, receiver, text, time, type) VALUES (?,?,?,?,?)",
        (msg['sender'], msg['receiver'], msg['text'], datetime.now().strftime("%H:%M"), msg.get('type','text'))
    )
    db.commit()
    db.close()
    return {"status":"sent"}

@app.get("/get_msgs/{u1}/{u2}")
async def fetch_messages(u1: str, u2: str):
    db = get_db()
    if u2 == "all":
        q = db.execute("SELECT * FROM messages WHERE receiver='all' ORDER BY id ASC").fetchall()
    elif u1 == "all" and u2 == "all":
        q = db.execute("SELECT * FROM messages ORDER BY id ASC").fetchall()
    else:
        q = db.execute(
            "SELECT * FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC", 
            (u1, u2, u2, u1)
        ).fetchall()
    db.close()
    return [dict(r) for r in q]

@app.delete("/del_m/{id}")
async def delete_message(id: int):
    db = get_db()
    db.execute("DELETE FROM messages WHERE id=?", (id,))
    db.commit()
    db.close()
    return {"status":"deleted"}

@app.get("/stats")
async def get_server_stats():
    db = get_db()
    u_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    m_count = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    db.close()
    return {"u": u_count, "m": m_count}

@app.delete("/admin/ban/{user}")
async def admin_ban_user(user: str):
    db = get_db()
    db.execute("DELETE FROM users WHERE username=?", (user,))
    db.execute("DELETE FROM messages WHERE sender=? OR receiver=?", (user, user))
    db.commit()
    db.close()
    return {"status":"banned"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
