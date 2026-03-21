import sqlite3, uvicorn, os, json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# ==============================================================================
# 🛰️ BACKEND: СЕРВЕРНАЯ ЛОГИКА И БАЗА ДАННЫХ
# ==============================================================================
app = FastAPI(title="TegeGrom Ultimate v11")
DB_FILE = 'tegegrom_v11_pro.db'

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        # Юзеры: пароли, аватарки, статусы, права админа
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, 
            avatar TEXT DEFAULT 'https://cdn-icons-png.flaticon.com/512/149/149071.png', 
            status TEXT DEFAULT 'online', is_admin INTEGER DEFAULT 0)''')
        # Сообщения: текст, фото, видео, голосовые, реакции
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, 
            content TEXT, timestamp TEXT, msg_type TEXT DEFAULT 'text', 
            file_url TEXT DEFAULT '', reactions TEXT DEFAULT '')''')
        # Ты — главный админ (Kupriz)
        conn.execute("INSERT OR IGNORE INTO users (username, password, is_admin) VALUES ('kupriz', 'admin', 1)")
        conn.commit()

init_db()

class AuthModel(BaseModel):
    username: str
    password: str
    avatar: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def home(): return UI_CODE

@app.post("/api/auth")
async def auth(u: AuthModel):
    with sqlite3.connect(DB_FILE) as conn:
        res = conn.execute("SELECT * FROM users WHERE username=?", (u.username,)).fetchone()
        is_adm = 1 if u.username.lower() == 'kupriz' else 0
        if not res:
            conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", 
                         (u.username, u.password, u.avatar or "https://cdn-icons-png.flaticon.com/512/149/149071.png", "online", is_adm))
            conn.commit()
        return {"status": "ok", "is_admin": is_adm}

@app.get("/api/users")
async def get_users():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute("SELECT username, avatar, status FROM users").fetchall()]

@app.get("/api/messages/{me}/{to}")
async def get_messages(me: str, to: str):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        q = "SELECT * FROM messages WHERE receiver='all'" if to=="all" else "SELECT * FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)"
        p = () if to=="all" else (me, to, to, me)
        return [dict(r) for r in conn.execute(q, p).fetchall()]

@app.post("/api/send")
async def send_msg(m: dict):
    with sqlite3.connect(DB_FILE) as conn:
        now = datetime.now().strftime("%H:%M")
        conn.execute("INSERT INTO messages (sender, receiver, content, timestamp, msg_type, file_url) VALUES (?,?,?,?,?,?)",
                     (m['sender'], m['receiver'], m['content'], now, m.get('type','text'), m.get('url','')))
        conn.commit()
    return {"ok": True}

@app.delete("/api/msg/{id}/{user}")
async def delete_msg(id: int, user: str):
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute("SELECT sender FROM messages WHERE id=?", (id,)).fetchone()
        if row and (row[0] == user or user.lower() == 'kupriz'):
            conn.execute("DELETE FROM messages WHERE id=?", (id,))
            conn.commit()
            return {"ok": True}
        raise HTTPException(status_code=403, detail="Forbidden")

# ==============================================================================
# 🎨 FRONTEND: ОГРОМНЫЙ И КРАСИВЫЙ ИНТЕРФЕЙС
# ==============================================================================
UI_CODE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>TegeGrom Pro v11</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg: #0e1621; --side: #17212b; --blue: #0088cc; --text: #f5f5f5;
            --msg-in: #182533; --msg-out: #2b5278; --hint: #708499; --danger: #ff3b30;
            --grad: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; font-family: 'Segoe UI', Roboto, sans-serif; }
        body, html { margin: 0; padding: 0; height: 100%; width: 100%; background: var(--bg); color: var(--text); overflow: hidden; }

        /* --- ЭКРАН ВХОДА --- */
        #auth-overlay { position: fixed; inset: 0; z-index: 1000; background: var(--grad); display: flex; align-items: center; justify-content: center; padding: 20px; transition: 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
        .auth-card { background: var(--side); padding: 40px; border-radius: 30px; width: 100%; max-width: 400px; text-align: center; box-shadow: 0 30px 60px rgba(0,0,0,0.7); border: 1px solid rgba(255,255,255,0.05); }
        .auth-card h1 { font-size: 42px; margin: 0; color: var(--blue); text-shadow: 0 0 20px rgba(0,136,204,0.3); }
        .auth-input { width: 100%; padding: 16px; margin: 12px 0; border-radius: 15px; border: 1px solid #242f3d; background: #0b1118; color: white; font-size: 16px; }
        .auth-btn { width: 100%; padding: 18px; background: var(--blue); color: white; border: none; border-radius: 15px; font-weight: bold; cursor: pointer; font-size: 18px; margin-top: 15px; box-shadow: 0 5px 15px rgba(0,136,204,0.4); }

        /* --- МАКЕТ ПРИЛОЖЕНИЯ --- */
        #app { display: none; height: 100vh; width: 100vw; flex-direction: row; }
        #sidebar { width: 350px; background: var(--side); border-right: 2px solid #000; display: flex; flex-direction: column; z-index: 100; transition: 0.3s ease; }
        #chat-window { flex: 1; display: flex; flex-direction: column; background: #0e1117; position: relative; }

        /* --- СПИСОК ЮЗЕРОВ --- */
        .side-head { padding: 20px; background: var(--side); display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(0,0,0,0.2); }
        .u-item { padding: 15px 20px; display: flex; align-items: center; gap: 15px; cursor: pointer; border-bottom: 1px solid rgba(0,0,0,0.05); transition: 0.2s; }
        .u-item:hover { background: rgba(255,255,255,0.03); }
        .u-item.active { background: #2b5278; border-left: 4px solid var(--blue); }
        .pfp { width: 52px; height: 52px; border-radius: 50%; object-fit: cover; border: 1px solid rgba(255,255,255,0.1); }
        .online-dot { width: 12px; height: 12px; background: #4ade80; border-radius: 50%; border: 2px solid var(--side); position: relative; left: -25px; top: 15px; }

        /* --- ХЕДЕР ЧАТА --- */
        .chat-header { height: 70px; background: var(--side); padding: 0 20px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 5px 15px rgba(0,0,0,0.2); z-index: 50; }
        .c-info { display: flex; align-items: center; gap: 15px; }
        .nav-btn { font-size: 22px; color: var(--blue); cursor: pointer; background: none; border: none; padding: 10px; transition: 0.2s; }
        .nav-btn:hover { transform: scale(1.1); }

        /* --- СООБЩЕНИЯ --- */
        #feed { flex: 1; overflow-y: auto; padding: 25px; display: flex; flex-direction: column; gap: 15px; background: url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png'); background-color: rgba(14, 22, 33, 0.9); background-blend-mode: overlay; scroll-behavior: smooth; }
        .m-wrap { display: flex; flex-direction: column; max-width: 80%; position: relative; animation: pop 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28); }
        @keyframes pop { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        .m-wrap.out { align-self: flex-end; }
        .m-wrap.in { align-self: flex-start; }
        .bubble { padding: 12px 16px; border-radius: 20px; font-size: 15.5px; position: relative; line-height: 1.5; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .out .bubble { background: var(--msg-out); border-bottom-right-radius: 4px; }
        .in .bubble { background: var(--msg-in); border-bottom-left-radius: 4px; }
        .bubble img, .bubble video { max-width: 100%; border-radius: 12px; margin-top: 8px; border: 1px solid rgba(255,255,255,0.05); }
        .m-meta { display: flex; justify-content: space-between; align-items: center; margin-top: 6px; font-size: 11px; opacity: 0.6; }
        .del-i { color: var(--danger); cursor: pointer; margin-left: 10px; visibility: hidden; }
        .m-wrap:hover .del-i { visibility: visible; }

        /* --- ПАНЕЛЬ ВВОДА --- */
        .bar { padding: 15px 25px; background: var(--side); display: flex; align-items: center; gap: 15px; border-top: 1px solid rgba(0,0,0,0.2); }
        .field { flex: 1; background: #0b1118; border: 1px solid #242f3d; padding: 14px 20px; border-radius: 25px; color: white; font-size: 16px; }
        .action { font-size: 24px; color: var(--blue); cursor: pointer; border: none; background: none; }
        .send-pill { width: 50px; height: 50px; background: var(--blue); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: none; cursor: pointer; box-shadow: 0 4px 10px rgba(0,136,204,0.3); }

        /* --- ЗВОНОК --- */
        #call-ui { position: absolute; inset: 0; background: var(--grad); z-index: 200; display: none; flex-direction: column; align-items: center; justify-content: center; }
        .call-ava { width: 160px; height: 160px; border-radius: 50%; border: 5px solid var(--blue); margin-bottom: 30px; animation: glow 2s infinite; }
        @keyframes glow { 0% { box-shadow: 0 0 0 0 rgba(0,136,204,0.6); } 70% { box-shadow: 0 0 0 40px rgba(0,136,204,0); } 100% { box-shadow: 0 0 0 0 rgba(0,136,204,0); } }

        /* --- МОБИЛКА --- */
        @media (max-width: 768px) {
            #sidebar { position: fixed; left: 0; width: 100%; height: 100%; transform: translateX(0); z-index: 150; }
            body.is-chat #sidebar { transform: translateX(-100%); }
            .back-m { display: block !important; }
        }
        .back-m { display: none; font-size: 26px; margin-right: 15px; cursor: pointer; }
    </style>
</head>
<body>

<div id="auth-overlay">
    <div class="auth-card">
        <h1>TegeGrom</h1>
        <p style="opacity:0.6; margin: 10px 0 30px;">Premium OS v11.0</p>
        <input type="text" id="u-name" class="auth-input" placeholder="Никнейм">
        <input type="password" id="u-pass" class="auth-input" placeholder="Пароль">
        <input type="text" id="u-ava" class="auth-input" placeholder="Аватар URL (прямая ссылка)">
        <button class="auth-btn" onclick="startSession()">ВОЙТИ В СИСТЕМУ</button>
    </div>
</div>

<div id="app">
    <div id="sidebar">
        <div class="side-head">
            <b style="font-size: 24px; color: var(--blue);">Чаты</b>
            <i class="fa-solid fa-pen-to-square nav-btn"></i>
        </div>
        <div id="u-list" style="overflow-y:auto; flex:1;"></div>
    </div>

    <div id="chat-window">
        <div id="call-ui">
            <img id="call-pfp" class="call-ava" src="">
            <h2 id="call-target">Звонок...</h2>
            <p id="timer" style="font-size: 20px; letter-spacing: 2px;">00:00</p>
            <button onclick="endCall()" style="background:var(--danger); width: 200px; padding:15px; border-radius:15px; color:white; border:none; font-weight:bold; margin-top:50px;">ЗАВЕРШИТЬ</button>
        </div>

        <div class="chat-header">
            <div class="c-info">
                <i class="fa-solid fa-arrow-left back-m" onclick="document.body.classList.remove('is-chat')"></i>
                <img id="h-ava" class="pfp" src="https://cdn-icons-png.flaticon.com/512/149/149071.png">
                <div>
                    <b id="h-name" style="font-size:18px;">Глобальный чат</b><br>
                    <small id="h-stat" style="color:#4ade80;">в сети</small>
                </div>
            </div>
            <div style="display:flex; gap:10px;">
                <button class="nav-btn" onclick="makeCall()"><i class="fa-solid fa-phone"></i></button>
                <button class="nav-btn" onclick="makeCall()"><i class="fa-solid fa-video"></i></button>
                <button class="nav-btn" onclick="alert('Admin: '+me)"><i class="fa-solid fa-ellipsis-vertical"></i></button>
            </div>
        </div>

        <div id="feed"></div>

        <div class="bar">
            <button class="action" onclick="media()"><i class="fa-solid fa-paperclip"></i></button>
            <input type="text" id="msg-field" class="field" placeholder="Написать сообщение..." onkeypress="if(event.key==='Enter')send()">
            <button class="action" onclick="emoji()"><i class="fa-regular fa-face-smile"></i></button>
            <button class="action" id="rec-btn" onclick="voice()"><i class="fa-solid fa-microphone"></i></button>
            <button class="send-pill" onclick="send()"><i class="fa-solid fa-paper-plane"></i></button>
        </div>
    </div>
</div>

<script>
    let me = localStorage.getItem('tg11_u') || "";
    let tg = "all";
    let isRec = false;

    async function startSession() {
        const u = document.getElementById('u-name').value.trim();
        const p = document.getElementById('u-pass').value.trim();
        const a = document.getElementById('u-ava').value.trim();
        if(!u || !p) return alert("Введите данные!");
        await fetch('/api/auth', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p,avatar:a})});
        localStorage.setItem('tg11_u', u);
        location.reload();
    }

    function init() {
        if(!me) return;
        document.getElementById('auth-overlay').style.display = 'none';
        document.getElementById('app').style.display = 'flex';
        loadUsers();
        setInterval(loadUsers, 10000);
        setInterval(sync, 2000);
    }

    async function loadUsers() {
        const r = await fetch('/api/users');
        const data = await r.json();
        const list = document.getElementById('u-list');
        let html = `<div class="u-item ${tg==='all'?'active':''}" onclick="setT('all','https://cdn-icons-png.flaticon.com/512/149/149071.png','Глобальный чат')">
            <img src="https://cdn-icons-png.flaticon.com/512/149/149071.png" class="pfp">
            <div><b>📢 Глобальный чат</b><br><small style="color:var(--hint)">Общий поток</small></div>
        </div>`;
        data.forEach(u => {
            if(u.username !== me) {
                html += `<div class="u-item ${tg===u.username?'active':''}" onclick="setT('${u.username}','${u.avatar}','${u.username}')">
                    <img src="${u.avatar}" class="pfp">
                    <div><b>${u.username}</b><br><small style="color:var(--hint)">${u.status}</small></div>
                </div>`;
            }
        });
        list.innerHTML = html;
    }

    function setT(u, a, n) {
        tg = u;
        document.getElementById('h-ava').src = a;
        document.getElementById('h-name').innerText = n;
        document.getElementById('feed').innerHTML = "";
        if(window.innerWidth < 768) document.body.classList.add('is-chat');
        sync();
    }

    async function send(type='text', url='') {
        const f = document.getElementById('msg-field');
        if(!f.value && type==='text') return;
        await fetch('/api/send', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sender:me,receiver:tg,content:f.value,type:type,url:url})});
        f.value = ""; sync();
    }

    async function sync() {
        const r = await fetch(`/api/messages/${me}/${tg}`);
        const data = await r.json();
        const box = document.getElementById('feed');
        box.innerHTML = data.map(m => {
            let body = m.content;
            if(m.msg_type === 'img') body = `<img src="${m.url}">`;
            if(m.msg_type === 'vid') body = `<video controls src="${m.url}"></video>`;
            if(m.msg_type === 'voice') body = `<div style="display:flex;align-items:center;gap:10px;"><i class="fa-solid fa-play"></i><div style="height:4px;width:100px;background:#fff;border-radius:2px;"></div></div>`;
            
            const isMe = m.sender === me;
            const canD = isMe || me.toLowerCase() === 'kupriz';

            return `<div class="m-wrap ${isMe?'out':'in'}">
                <div class="bubble">
                    <b style="color:var(--blue); font-size:12px;">${m.sender}</b><br>${body}
                    <div class="m-meta">
                        <span>${m.timestamp}</span>
                        ${canD ? `<i class="fa-solid fa-trash del-i" onclick="del(${m.id})"></i>` : ''}
                    </div>
                </div>
            </div>`;
        }).join('');
        box.scrollTop = box.scrollHeight;
    }

    async function del(id) { if(confirm("Удалить?")) await fetch(`/api/msg/${id}/${me}`, {method:'DELETE'}); sync(); }

    function media() {
        const t = prompt("1-Фото, 2-Видео");
        const u = prompt("URL ссылки:");
        if(u) send(t==='1'?'img':'vid', u);
    }

    function emoji() { 
        const e = ["😀","😂","😍","👍","🔥","🚀","💎"];
        const rand = e[Math.floor(Math.random() * e.length)];
        document.getElementById('msg-field').value += rand;
    }

    function voice() {
        isRec = !isRec;
        const b = document.getElementById('rec-btn');
        b.style.color = isRec ? 'var(--danger)' : 'var(--blue)';
        if(!isRec) send('voice', '#');
    }

    function makeCall() {
        document.getElementById('call-pfp').src = document.getElementById('h-ava').src;
        document.getElementById('call-target').innerText = "Вызов: " + tg;
        document.getElementById('call-ui').style.display = 'flex';
    }
    function endCall() { document.getElementById('call-ui').style.display = 'none'; }

    init();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
