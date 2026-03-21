import sqlite3, uvicorn, os, json, base64
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# ==============================================================================
# 🛠️ СЕРВЕРНЫЙ ДВИЖОК: TEGEGROM ULTIMATE ENGINE
# ==============================================================================
app = FastAPI(title="TegeGrom Ultimate v16")
DB_PATH = 'tegegrom_v16_pro.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Таблица пользователей с расширенными настройками
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            password TEXT, 
            avatar TEXT DEFAULT 'https://i.imgur.com/6VBx3io.png',
            status TEXT DEFAULT 'online',
            theme_color TEXT DEFAULT '#0088cc',
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # Таблица сообщений (Текст, Медиа, Голос)
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            sender TEXT, 
            receiver TEXT, 
            content TEXT, 
            timestamp TEXT, 
            msg_type TEXT DEFAULT 'text', 
            file_blob TEXT,
            is_read INTEGER DEFAULT 0
        )''')
        # Создаем тебя как владельца
        conn.execute("INSERT OR IGNORE INTO users (username, password, theme_color) VALUES ('kupriz', 'admin', '#ff3b30')")
        conn.commit()

init_db()

# --- Модели данных ---
class MessageSend(BaseModel):
    sender: str
    receiver: str
    content: Optional[str] = ""
    msg_type: str = "text"
    file_blob: Optional[str] = None

class AuthModel(BaseModel):
    username: str
    password: str

# ==============================================================================
# 🛰️ API КАНАЛЫ (БЭКЕНД ЛОГИКА)
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    return UI_V16

@app.post("/api/login")
async def login(user: AuthModel):
    with get_db() as conn:
        res = conn.execute("SELECT * FROM users WHERE username=?", (user.username,)).fetchone()
        if not res:
            conn.execute("INSERT INTO users (username, password) VALUES (?,?)", (user.username, user.password))
            conn.commit()
        return {"status": "ok", "is_admin": (user.username.lower() == 'kupriz')}

@app.get("/api/users")
async def fetch_users():
    with get_db() as conn:
        return [dict(row) for row in conn.execute("SELECT username, avatar, status FROM users").fetchall()]

@app.get("/api/chat/{me}/{to}")
async def get_messages(me: str, to: str, last_id: int = 0):
    with get_db() as conn:
        if to == "all":
            query = "SELECT * FROM messages WHERE receiver='all' AND id > ? ORDER BY id ASC"
            params = (last_id,)
        else:
            query = "SELECT * FROM messages WHERE ((sender=? AND receiver=?) OR (sender=? AND receiver=?)) AND id > ? ORDER BY id ASC"
            params = (me, to, to, me, last_id)
        return [dict(row) for row in conn.execute(query, params).fetchall()]

@app.post("/api/send")
async def send_message(msg: MessageSend):
    with get_db() as conn:
        now = datetime.now().strftime("%H:%M")
        conn.execute("INSERT INTO messages (sender, receiver, content, timestamp, msg_type, file_blob) VALUES (?,?,?,?,?,?)",
                     (msg.sender, msg.receiver, msg.content, now, msg.msg_type, msg.file_blob))
        conn.commit()
    return {"status": "sent"}

@app.delete("/api/delete/{mid}/{user}")
async def delete_msg(mid: int, user: str):
    with get_db() as conn:
        row = conn.execute("SELECT sender FROM messages WHERE id=?", (mid,)).fetchone()
        if row and (row['sender'] == user or user.lower() == 'kupriz'):
            conn.execute("DELETE FROM messages WHERE id=?", (mid,))
            conn.commit()
            return {"ok": True}
        raise HTTPException(status_code=403)

# ==============================================================================
# 🎨 UI ENGINE: МОНУМЕНТАЛЬНЫЙ ИНТЕРФЕЙС (HTML/CSS/JS)
# ==============================================================================
UI_V16 = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>TegeGrom Premium v16</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg: #0e1621; --side: #17212b; --blue: #0088cc; --text: #f5f5f5;
            --msg-in: #182533; --msg-out: #2b5278; --hint: #708499; --accent: #2481cc;
        }
        * { box-sizing: border-box; outline: none; -webkit-tap-highlight-color: transparent; }
        body, html { 
            margin: 0; padding: 0; height: 100vh; width: 100vw; 
            background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            overflow: hidden;
        }

        /* --- AUTH LAYER --- */
        #auth-screen {
            position: fixed; inset: 0; z-index: 9999; background: radial-gradient(circle at top, #1e2a3a, #0e1621);
            display: flex; align-items: center; justify-content: center; transition: 0.5s;
        }
        .auth-card {
            background: rgba(23, 33, 43, 0.8); backdrop-filter: blur(20px);
            padding: 40px; border-radius: 30px; width: 90%; max-width: 400px;
            text-align: center; box-shadow: 0 25px 50px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.05);
        }
        .auth-card h1 { font-size: 32px; margin-bottom: 10px; color: var(--blue); letter-spacing: -1px; }
        .auth-input {
            width: 100%; padding: 15px; margin: 10px 0; border-radius: 15px; border: 1px solid #242f3d;
            background: #0b1118; color: white; font-size: 16px; transition: 0.3s;
        }
        .auth-input:focus { border-color: var(--blue); box-shadow: 0 0 10px rgba(0,136,204,0.3); }
        .auth-btn {
            width: 100%; padding: 16px; background: var(--blue); color: white; border: none;
            border-radius: 15px; font-weight: bold; cursor: pointer; font-size: 18px; margin-top: 20px;
        }

        /* --- MAIN LAYOUT --- */
        #app { display: none; height: 100%; width: 100%; flex-direction: row; }
        
        #sidebar {
            width: 380px; background: var(--side); border-right: 1px solid rgba(0,0,0,0.4);
            display: flex; flex-direction: column; z-index: 100; transition: 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        #chat-area { flex: 1; display: flex; flex-direction: column; background: #0e1117; position: relative; }

        /* --- CONTACTS --- */
        .search-bar { padding: 15px; background: var(--side); border-bottom: 1px solid rgba(0,0,0,0.2); }
        .search-input { width: 100%; padding: 10px 15px; border-radius: 10px; border: none; background: #242f3d; color: white; }
        
        #user-list { flex: 1; overflow-y: auto; }
        .user-item {
            padding: 12px 20px; display: flex; align-items: center; gap: 15px; cursor: pointer;
            transition: 0.2s; border-bottom: 1px solid rgba(255,255,255,0.02);
        }
        .user-item:hover { background: rgba(255,255,255,0.05); }
        .user-item.active { background: #2b5278; }
        .avatar { width: 54px; height: 54px; border-radius: 50%; object-fit: cover; background: #242f3d; }
        .user-info b { font-size: 16px; display: block; margin-bottom: 4px; }
        .user-info small { color: var(--hint); font-size: 13px; }

        /* --- CHAT HEADER --- */
        .chat-header {
            height: 64px; background: var(--side); padding: 0 20px; display: flex;
            align-items: center; justify-content: space-between; z-index: 50; box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .active-user { display: flex; align-items: center; gap: 12px; }
        .header-btn { font-size: 20px; color: var(--blue); cursor: pointer; padding: 10px; transition: 0.2s; }
        .header-btn:hover { transform: scale(1.1); }

        /* --- MESSAGES FEED --- */
        #feed {
            flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 8px;
            background: url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png');
            background-color: rgba(14, 22, 33, 0.95); background-blend-mode: overlay;
            scroll-behavior: smooth;
        }
        .msg-wrap { display: flex; flex-direction: column; max-width: 80%; animation: msgIn 0.2s ease-out; }
        @keyframes msgIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .msg-wrap.mine { align-self: flex-end; }
        .msg-wrap.their { align-self: flex-start; }

        .bubble {
            padding: 10px 14px; border-radius: 18px; font-size: 15px; position: relative;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); line-height: 1.4; word-wrap: break-word;
        }
        .mine .bubble { background: var(--msg-out); border-bottom-right-radius: 4px; }
        .their .bubble { background: var(--msg-in); border-bottom-left-radius: 4px; }
        
        .bubble img, .bubble video { 
            max-width: 100%; border-radius: 12px; margin: 5px 0; display: block;
            cursor: pointer; transition: 0.3s;
        }
        .bubble audio { width: 100%; margin-top: 5px; filter: invert(1); }

        .msg-meta { display: flex; justify-content: flex-end; gap: 5px; font-size: 11px; margin-top: 4px; opacity: 0.6; }
        .del-btn { color: #ff3b30; cursor: pointer; display: none; }
        .msg-wrap:hover .del-btn { display: inline; }

        /* --- INPUT BAR --- */
        .input-bar {
            padding: 10px 20px; background: var(--side); display: flex; align-items: center; gap: 12px;
            border-top: 1px solid rgba(0,0,0,0.3); padding-bottom: calc(10px + env(safe-area-inset-bottom));
        }
        .attach-label { font-size: 22px; color: var(--hint); cursor: pointer; transition: 0.2s; }
        .attach-label:hover { color: var(--blue); }
        .main-input {
            flex: 1; background: #0b1118; border: 1px solid #242f3d; padding: 12px 18px;
            border-radius: 25px; color: white; font-size: 16px; outline: none;
        }
        .send-btn {
            width: 44px; height: 44px; background: var(--blue); color: white; border: none;
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            font-size: 18px; cursor: pointer; box-shadow: 0 4px 10px rgba(0,136,204,0.3);
        }

        /* --- CALL UI --- */
        #call-overlay {
            position: absolute; inset: 0; background: rgba(14,22,33,0.98); z-index: 500;
            display: none; flex-direction: column; align-items: center; justify-content: center;
        }
        .call-ava { width: 150px; height: 150px; border-radius: 50%; border: 4px solid var(--blue); animation: pulse 2s infinite; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(0,136,204,0.4); } 70% { box-shadow: 0 0 0 40px rgba(0,136,204,0); } 100% { box-shadow: 0 0 0 0 rgba(0,136,204,0); } }

        /* --- MOBILE --- */
        @media (max-width: 800px) {
            #sidebar { position: fixed; width: 100%; height: 100%; left: 0; transform: translateX(0); }
            body.is-chatting #sidebar { transform: translateX(-100%); }
            .back-btn { display: block !important; }
        }
        .back-btn { display: none; font-size: 24px; color: var(--blue); cursor: pointer; margin-right: 15px; }

        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
    </style>
</head>
<body>

<div id="auth-screen">
    <div class="auth-card">
        <h1>TegeGrom 16</h1>
        <p style="color:var(--hint); margin-bottom:20px;">Введите данные для входа</p>
        <input type="text" id="auth-u" class="auth-input" placeholder="Ваше имя">
        <input type="password" id="auth-p" class="auth-input" placeholder="Пароль">
        <button class="auth-btn" onclick="tryLogin()">ВОЙТИ В СИСТЕМУ</button>
    </div>
</div>

<div id="app">
    <div id="sidebar">
        <div class="search-bar">
            <input type="text" class="search-input" placeholder="Поиск контактов...">
        </div>
        <div id="user-list"></div>
    </div>

    <div id="chat-area">
        <div id="call-overlay">
            <img id="call-img" class="call-ava" src="">
            <h2 id="call-name" style="margin:20px 0 50px;">Вызов...</h2>
            <button class="auth-btn" style="background:#ff3b30; width:180px;" onclick="closeCall()">СБРОСИТЬ</button>
        </div>

        <div class="chat-header">
            <div class="active-user">
                <i class="fa-solid fa-chevron-left back-btn" onclick="document.body.classList.remove('is-chatting')"></i>
                <img id="h-ava" class="avatar" src="https://i.imgur.com/6VBx3io.png" style="width:40px; height:40px;">
                <div>
                    <b id="h-name">Выберите чат</b><br>
                    <small id="h-status" style="color:#4ade80">в сети</small>
                </div>
            </div>
            <div style="display:flex; gap:10px;">
                <i class="fa-solid fa-phone header-btn" onclick="startCall()"></i>
                <i class="fa-solid fa-video header-btn" onclick="startCall()"></i>
                <i class="fa-solid fa-ellipsis-vertical header-btn"></i>
            </div>
        </div>

        <div id="feed"></div>

        <div class="input-bar">
            <label class="attach-label">
                <i class="fa-solid fa-paperclip"></i>
                <input type="file" id="file-input" hidden onchange="handleFile()">
            </label>
            <input type="text" id="msg-input" class="main-input" placeholder="Напишите сообщение..." onkeypress="if(event.key==='Enter')sendNow()">
            <i class="fa-solid fa-microphone attach-label" id="mic-btn" onclick="toggleVoice()"></i>
            <button class="send-btn" onclick="sendNow()"><i class="fa-solid fa-paper-plane"></i></button>
        </div>
    </div>
</div>

<script>
    let myUser = localStorage.getItem('tg16_user') || "";
    let chatWith = "all";
    let lastId = 0;
    let isRecording = false;
    let recorder;
    let chunks = [];

    async function tryLogin() {
        const u = document.getElementById('auth-u').value.trim();
        const p = document.getElementById('auth-p').value.trim();
        if(!u || !p) return alert("Заполните все поля!");

        const res = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: u, password: p})
        });
        localStorage.setItem('tg16_user', u);
        location.reload();
    }

    if(myUser) {
        document.getElementById('auth-screen').style.opacity = '0';
        setTimeout(() => {
            document.getElementById('auth-screen').style.display = 'none';
            document.getElementById('app').style.display = 'flex';
        }, 500);
        initChat();
    }

    function initChat() {
        loadUsers();
        setInterval(loadUsers, 10000);
        setInterval(syncMessages, 1500);
    }

    async function loadUsers() {
        const r = await fetch('/api/users');
        const users = await r.json();
        const box = document.getElementById('user-list');
        let html = `<div class="user-item ${chatWith==='all'?'active':''}" onclick="selectChat('all','📢 Глобальный чат','https://i.imgur.com/6VBx3io.png')">
            <img src="https://i.imgur.com/6VBx3io.png" class="avatar">
            <div class="user-info"><b>Глобальный чат</b><small>Общий поток сообщений</small></div>
        </div>`;
        users.forEach(u => {
            if(u.username !== myUser) {
                html += `<div class="user-item ${chatWith===u.username?'active':''}" onclick="selectChat('${u.username}','${u.username}','${u.avatar}')">
                    <img src="${u.avatar}" class="avatar">
                    <div class="user-info"><b>${u.username}</b><small>${u.status}</small></div>
                </div>`;
            }
        });
        box.innerHTML = html;
    }

    function selectChat(u, name, ava) {
        chatWith = u;
        lastId = 0;
        document.getElementById('h-name').innerText = name;
        document.getElementById('h-ava').src = ava;
        document.getElementById('feed').innerHTML = '';
        if(window.innerWidth < 800) document.body.classList.add('is-chatting');
        syncMessages();
    }

    async function sendNow(type='text', blob=null) {
        const inp = document.getElementById('msg-input');
        if(!inp.value && type==='text' && !blob) return;

        await fetch('/api/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                sender: myUser,
                receiver: chatWith,
                content: inp.value,
                msg_type: type,
                file_blob: blob
            })
        });
        inp.value = '';
        syncMessages();
    }

    async function syncMessages() {
        const r = await fetch(`/api/chat/${myUser}/${chatWith}?last_id=${lastId}`);
        const data = await r.json();
        const box = document.getElementById('feed');
        
        data.forEach(m => {
            lastId = Math.max(lastId, m.id);
            const isMe = m.sender === myUser;
            const wrap = document.createElement('div');
            wrap.className = `msg-wrap ${isMe ? 'mine' : 'their'}`;
            
            let content = `<span>${m.content}</span>`;
            if(m.msg_type === 'img') content = `<img src="${m.file_blob}" onclick="window.open(this.src)">`;
            if(m.msg_type === 'vid') content = `<video controls src="${m.file_blob}"></video>`;
            if(m.msg_type === 'voice') content = `<audio controls src="${m.file_blob}"></audio>`;

            wrap.innerHTML = `
                <div class="bubble">
                    <b style="font-size:12px; color:var(--blue);">${m.sender}</b><br>
                    ${content}
                    <div class="msg-meta">
                        <span>${m.timestamp}</span>
                        ${(isMe || myUser.toLowerCase()==='kupriz') ? `<i class="fa-solid fa-trash del-btn" onclick="deleteMsg(${m.id})"></i>` : ''}
                    </div>
                </div>
            `;
            box.appendChild(wrap);
            box.scrollTop = box.scrollHeight;
        });
    }

    async function deleteMsg(id) {
        if(confirm("Удалить?")) {
            await fetch(`/api/delete/${id}/${myUser}`, {method: 'DELETE'});
            location.reload();
        }
    }

    async function handleFile() {
        const file = document.getElementById('file-input').files[0];
        if(!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            const type = file.type.startsWith('image') ? 'img' : 'vid';
            sendNow(type, reader.result);
        };
        reader.readAsDataURL(file);
    }

    async function toggleVoice() {
        const btn = document.getElementById('mic-btn');
        if(!isRecording) {
            const stream = await navigator.mediaDevices.getUserMedia({audio:true});
            recorder = new MediaRecorder(stream);
            recorder.ondataavailable = e => chunks.push(e.data);
            recorder.onstop = () => {
                const blob = new Blob(chunks, {type: 'audio/ogg'});
                const reader = new FileReader();
                reader.onload = () => sendNow('voice', reader.result);
                reader.readAsDataURL(blob);
                chunks = [];
            };
            recorder.start();
            isRecording = true;
            btn.style.color = '#ff3b30';
        } else {
            recorder.stop();
            isRecording = false;
            btn.style.color = 'var(--hint)';
        }
    }

    function startCall() {
        document.getElementById('call-img').src = document.getElementById('h-ava').src;
        document.getElementById('call-name').innerText = "Вызов: " + chatWith;
        document.getElementById('call-overlay').style.display = 'flex';
    }
    function closeCall() { document.getElementById('call-overlay').style.display = 'none'; }
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
