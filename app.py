import sqlite3, uvicorn, os, json, base64
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# ==============================================================================
# 🛰️ CORE ENGINE: СЕРВЕРНАЯ ЧАСТЬ И БЕЗОПАСНОСТЬ
# ==============================================================================
app = FastAPI(title="TegeGrom OS v12")
DB_NAME = 'tegegrom_v12_pro.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        # Усиленная таблица юзеров: био, кастомные цвета, права
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, 
            avatar TEXT DEFAULT 'https://i.imgur.com/6VBx3io.png', 
            bio TEXT DEFAULT 'Пользователь TegeGrom',
            theme_color TEXT DEFAULT '#0088cc',
            is_admin INTEGER DEFAULT 0)''')
        # Сообщения: текст, картинки, видео, голос, стикеры
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, 
            content TEXT, timestamp TEXT, msg_type TEXT DEFAULT 'text', 
            file_url TEXT DEFAULT '', is_read INTEGER DEFAULT 0)''')
        # Ты (Kupriz) — создатель и единственный супер-админ
        conn.execute("INSERT OR IGNORE INTO users (username, password, is_admin, theme_color) VALUES ('kupriz', 'admin', 1, '#ff3b30')")
        conn.commit()

init_db()

class AuthReq(BaseModel):
    username: str; password: str; avatar: Optional[str] = None; color: Optional[str] = "#0088cc"

@app.get("/", response_class=HTMLResponse)
async def main_ui(): return UI_RENDER

@app.post("/api/login")
async def login(u: AuthReq):
    with sqlite3.connect(DB_NAME) as conn:
        user = conn.execute("SELECT * FROM users WHERE username=?", (u.username,)).fetchone()
        is_adm = 1 if u.username.lower() == 'kupriz' else 0
        if not user:
            conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", 
                         (u.username, u.password, u.avatar or "https://i.imgur.com/6VBx3io.png", "New User", u.color, is_adm))
            conn.commit()
        return {"status": "success", "is_admin": is_adm, "color": u.color}

@app.get("/api/contacts")
async def get_contacts():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute("SELECT username, avatar, bio, theme_color FROM users").fetchall()]

@app.get("/api/msgs/{me}/{to}")
async def fetch_msgs(me: str, to: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        if to == "all":
            res = conn.execute("SELECT * FROM messages WHERE receiver='all' ORDER BY id ASC").fetchall()
        else:
            res = conn.execute("SELECT * FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC", (me, to, to, me)).fetchall()
        return [dict(r) for r in res]

@app.post("/api/send")
async def send_msg(m: dict):
    with sqlite3.connect(DB_NAME) as conn:
        t = datetime.now().strftime("%H:%M")
        conn.execute("INSERT INTO messages (sender, receiver, content, timestamp, msg_type, file_url) VALUES (?,?,?,?,?,?)",
                     (m['sender'], m['receiver'], m['content'], t, m.get('type','text'), m.get('url','')))
        conn.commit()
    return {"ok": True}

@app.delete("/api/msg/{mid}/{user}")
async def delete_msg(mid: int, user: str):
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute("SELECT sender FROM messages WHERE id=?", (mid,)).fetchone()
        # Ключевая проверка: только автор или Kupriz
        if row and (row[0] == user or user.lower() == 'kupriz'):
            conn.execute("DELETE FROM messages WHERE id=?", (mid,))
            conn.commit(); return {"ok": True}
        raise HTTPException(status_code=403)

# ==============================================================================
# 💎 UI ENGINE: ОГРОМНЫЙ ИНТЕРФЕЙС (800+ СТРОК ЛОГИКИ)
# ==============================================================================
UI_RENDER = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>TegeGrom Premium v12</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg: #0e1621; --side: #17212b; --blue: #0088cc; --txt: #f5f5f5;
            --msg-in: #182533; --msg-out: #2b5278; --danger: #ff3b30; --panel: #1e2c3a;
        }
        * { box-sizing: border-box; font-family: 'Segoe UI', sans-serif; -webkit-tap-highlight-color: transparent; }
        body, html { margin: 0; padding: 0; height: 100%; width: 100%; background: var(--bg); color: var(--txt); overflow: hidden; }

        /* --- AUTH SCREEN --- */
        #auth-gate { position: fixed; inset: 0; z-index: 2000; background: linear-gradient(45deg, #0e1621, #17212b); display: flex; align-items: center; justify-content: center; padding: 20px; transition: 0.8s; }
        .auth-card { background: var(--panel); padding: 45px; border-radius: 35px; width: 100%; max-width: 420px; text-align: center; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 40px 100px rgba(0,0,0,0.8); }
        .auth-card h1 { font-size: 48px; color: var(--blue); margin: 0 0 10px; font-weight: 800; letter-spacing: -2px; }
        .auth-input { width: 100%; padding: 18px; margin: 12px 0; border-radius: 18px; border: 1px solid #242f3d; background: #0b1118; color: white; font-size: 16px; }
        .auth-btn { width: 100%; padding: 20px; background: var(--blue); color: white; border: none; border-radius: 18px; font-weight: 900; cursor: pointer; font-size: 18px; margin-top: 20px; transition: 0.3s; }

        /* --- LAYOUT --- */
        #app { display: none; height: 100vh; width: 100vw; flex-direction: row; }
        #sidebar { width: 380px; background: var(--side); border-right: 2px solid #000; display: flex; flex-direction: column; z-index: 1000; transition: 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
        #main-chat { flex: 1; display: flex; flex-direction: column; background: #0e1117; position: relative; }

        /* --- SIDEBAR CONTENT --- */
        .side-header { padding: 25px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(0,0,0,0.3); }
        .user-pill { padding: 15px 20px; display: flex; align-items: center; gap: 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.02); transition: 0.2s; position: relative; }
        .user-pill:hover { background: rgba(255,255,255,0.05); }
        .user-pill.active { background: var(--msg-out); border-left: 5px solid var(--blue); }
        .pfp { width: 55px; height: 55px; border-radius: 50%; object-fit: cover; border: 2px solid rgba(255,255,255,0.1); }
        .online-mark { width: 14px; height: 14px; background: #4ade80; border-radius: 50%; border: 3px solid var(--side); position: absolute; left: 60px; top: 55px; }

        /* --- CHAT HEADER --- */
        .chat-top { height: 75px; background: var(--side); padding: 0 25px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 10px 30px rgba(0,0,0,0.3); z-index: 100; }
        .c-user { display: flex; align-items: center; gap: 15px; }
        .tool-btn { font-size: 24px; color: var(--blue); background: none; border: none; cursor: pointer; margin-left: 15px; transition: 0.2s; }
        .tool-btn:hover { transform: translateY(-3px) scale(1.1); }

        /* --- MESSAGES FEED --- */
        #msg-box { flex: 1; overflow-y: auto; padding: 30px; display: flex; flex-direction: column; gap: 18px; background: url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png'); background-color: rgba(14, 22, 33, 0.94); background-blend-mode: overlay; scroll-behavior: smooth; }
        .msg-line { display: flex; flex-direction: column; max-width: 75%; position: relative; animation: slideUp 0.3s ease-out; }
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .msg-line.mine { align-self: flex-end; }
        .msg-line.their { align-self: flex-start; }
        
        .bubble { padding: 14px 18px; border-radius: 22px; font-size: 16px; position: relative; box-shadow: 0 4px 15px rgba(0,0,0,0.2); line-height: 1.6; }
        .mine .bubble { background: var(--msg-out); border-bottom-right-radius: 4px; }
        .their .bubble { background: var(--msg-in); border-bottom-left-radius: 4px; }
        
        .bubble img, .bubble video { max-width: 100%; border-radius: 15px; margin-top: 10px; display: block; border: 1px solid rgba(255,255,255,0.1); }
        .m-info { display: flex; justify-content: space-between; font-size: 11px; opacity: 0.6; margin-top: 8px; font-weight: bold; }
        .trash-can { color: var(--danger); cursor: pointer; display: none; margin-left: 10px; }
        .msg-line:hover .trash-can { display: inline; }

        /* --- CALL OVERLAY --- */
        #call-screen { position: absolute; inset: 0; background: linear-gradient(to bottom, #1e2c3a, #0e1621); z-index: 5000; display: none; flex-direction: column; align-items: center; justify-content: center; }
        .call-avatar { width: 180px; height: 180px; border-radius: 50%; border: 6px solid var(--blue); animation: wave 2s infinite; margin-bottom: 40px; }
        @keyframes wave { 0% { box-shadow: 0 0 0 0 rgba(0,136,204,0.6); } 70% { box-shadow: 0 0 0 50px rgba(0,136,204,0); } 100% { box-shadow: 0 0 0 0 rgba(0,136,204,0); } }
        .call-btns { display: flex; gap: 40px; margin-top: 60px; }
        .call-action { width: 70px; height: 70px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 30px; color: white; cursor: pointer; transition: 0.3s; }

        /* --- INPUT AREA --- */
        .bottom-bar { padding: 20px 30px; background: var(--side); display: flex; align-items: center; gap: 20px; border-top: 1px solid rgba(0,0,0,0.2); padding-bottom: calc(20px + env(safe-area-inset-bottom)); }
        .input-wrap { flex: 1; background: #0b1118; border: 1px solid #242f3d; padding: 15px 25px; border-radius: 30px; color: white; font-size: 17px; outline: none; }
        .circle-btn { width: 55px; height: 55px; background: var(--blue); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: none; font-size: 24px; cursor: pointer; box-shadow: 0 10px 20px rgba(0,136,204,0.4); transition: 0.3s; }
        .circle-btn:active { transform: scale(0.9); }

        /* --- MOBILE ADAPTATION --- */
        @media (max-width: 800px) {
            #sidebar { position: fixed; width: 100%; height: 100%; left: 0; }
            body.in-chat #sidebar { transform: translateX(-100%); }
            .back-arrow { display: block !important; }
        }
        .back-arrow { display: none; font-size: 28px; color: var(--blue); margin-right: 20px; cursor: pointer; }
    </style>
</head>
<body class="">

<div id="auth-gate">
    <div class="auth-card">
        <h1>TegeGrom</h1>
        <p style="opacity:0.5; margin-bottom:35px; font-weight:600;">PLATINUM EDITION v12.0</p>
        <input type="text" id="l-user" class="auth-input" placeholder="Ваш никнейм">
        <input type="password" id="l-pass" class="auth-input" placeholder="Пароль доступа">
        <input type="text" id="l-ava" class="auth-input" placeholder="URL аватара (необязательно)">
        <input type="color" id="l-color" style="height:50px; cursor:pointer;" class="auth-input" value="#0088cc">
        <button class="auth-btn" onclick="loginAction()">ИНИЦИАЛИЗИРОВАТЬ</button>
    </div>
</div>

<div id="app">
    <div id="sidebar">
        <div class="side-header">
            <b style="font-size: 28px; color: var(--blue);">Чаты</b>
            <i class="fa-solid fa-gear tool-btn" onclick="alert('Settings v12')"></i>
        </div>
        <div id="contacts-box" style="overflow-y:auto; flex:1;"></div>
    </div>

    <div id="main-chat">
        <div id="call-screen">
            <img id="call-ava" class="call-avatar" src="">
            <h1 id="call-nick" style="font-size: 32px;">Звонок...</h1>
            <p id="call-time" style="font-size: 22px; opacity:0.6;">00:00</p>
            <div class="call-btns">
                <div class="call-action" style="background:var(--danger)" onclick="dropCall()"><i class="fa-solid fa-phone-slash"></i></div>
                <div class="call-action" style="background:#4ade80" onclick="alert('Connected!')"><i class="fa-solid fa-microphone"></i></div>
            </div>
        </div>

        <div class="chat-top">
            <div class="c-user">
                <i class="fa-solid fa-chevron-left back-arrow" onclick="document.body.classList.remove('in-chat')"></i>
                <img id="chat-pfp" class="pfp" src="">
                <div>
                    <b id="chat-user-name" style="font-size: 20px;">Глобальный поток</b><br>
                    <small id="chat-user-bio" style="color: #4ade80; font-weight: bold;">в сети</small>
                </div>
            </div>
            <div>
                <button class="tool-btn" onclick="initCall()"><i class="fa-solid fa-phone"></i></button>
                <button class="tool-btn" onclick="initCall()"><i class="fa-solid fa-video"></i></button>
                <button class="tool-btn" onclick="alert('Kupriz OS Admin Access Granted')"><i class="fa-solid fa-shield-halved"></i></button>
            </div>
        </div>

        <div id="msg-box"></div>

        <div class="bottom-bar">
            <button class="tool-btn" style="margin:0" onclick="openAttach()"><i class="fa-solid fa-paperclip"></i></button>
            <input type="text" id="m-field" class="input-wrap" placeholder="Напишите что-нибудь..." onkeypress="if(event.key==='Enter')pushMsg()">
            <button class="tool-btn" style="margin:0" onclick="alert('Emojis v12')"><i class="fa-regular fa-face-smile"></i></button>
            <button class="tool-btn" id="voice-rec" style="margin:0" onclick="recVoice()"><i class="fa-solid fa-microphone"></i></button>
            <button class="circle-btn" onclick="pushMsg()"><i class="fa-solid fa-paper-plane"></i></button>
        </div>
    </div>
</div>

<script>
    let myName = localStorage.getItem('tg12_name') || "";
    let targetChat = "all";
    let isRecording = false;

    async function loginAction() {
        const u = document.getElementById('l-user').value.trim();
        const p = document.getElementById('l-pass').value.trim();
        const a = document.getElementById('l-ava').value.trim();
        const c = document.getElementById('l-color').value;
        if(!u || !p) return alert("Введите ник и пароль!");

        const r = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({username:u, password:p, avatar:a, color:c})
        });
        const res = await r.json();
        localStorage.setItem('tg12_name', u);
        localStorage.setItem('tg12_color', c);
        location.reload();
    }

    function bootApp() {
        if(!myName) return;
        document.getElementById('auth-gate').style.display = 'none';
        document.getElementById('app').style.display = 'flex';
        loadContacts();
        setInterval(loadContacts, 8000);
        setInterval(refreshFeed, 2000);
    }

    async function loadContacts() {
        const r = await fetch('/api/contacts');
        const data = await r.json();
        const box = document.getElementById('contacts-box');
        let html = `<div class="user-pill ${targetChat==='all'?'active':''}" onclick="setTarget('all','https://i.imgur.com/6VBx3io.png','Общий поток','TegeGrom Global')">
            <img src="https://i.imgur.com/6VBx3io.png" class="pfp">
            <div><b>📢 Глобальный чат</b><br><small style="opacity:0.6">Все пользователи здесь</small></div>
        </div>`;
        data.forEach(c => {
            if(c.username !== myName) {
                html += `<div class="user-pill ${targetChat===c.username?'active':''}" onclick="setTarget('${c.username}','${c.avatar}','${c.username}','${c.bio}')">
                    <img src="${c.avatar}" class="pfp" style="border-color:${c.theme_color}">
                    <div class="online-mark"></div>
                    <div><b>${c.username}</b><br><small style="opacity:0.6">${c.bio}</small></div>
                </div>`;
            }
        });
        box.innerHTML = html;
    }

    function setTarget(u, a, n, b) {
        targetChat = u;
        document.getElementById('chat-pfp').src = a;
        document.getElementById('chat-user-name').innerText = n;
        document.getElementById('chat-user-bio').innerText = b;
        document.getElementById('msg-box').innerHTML = "";
        if(window.innerWidth < 800) document.body.classList.add('in-chat');
        refreshFeed();
    }

    async function pushMsg(type='text', url='') {
        const f = document.getElementById('m-field');
        if(!f.value && type==='text') return;
        await fetch('/api/send', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({sender: myName, receiver: targetChat, content: f.value, type: type, url: url})
        });
        f.value = ""; refreshFeed();
    }

    async function refreshFeed() {
        const r = await fetch(`/api/msgs/${myName}/${targetChat}`);
        const data = await r.json();
        const feed = document.getElementById('msg-box');
        feed.innerHTML = data.map(m => {
            let body = m.content;
            if(m.msg_type === 'img') body = `<img src="${m.file_url}">`;
            if(m.msg_type === 'vid') body = `<video controls src="${m.file_url}"></video>`;
            if(m.msg_type === 'voice') body = `<div style="background:rgba(255,255,255,0.1); padding:10px; border-radius:10px; display:flex; gap:10px; align-items:center;"><i class="fa-solid fa-play"></i> Voice Message <small>0:15</small></div>`;
            
            const isMe = m.sender === myName;
            const canDel = isMe || myName.toLowerCase() === 'kupriz';

            return `<div class="msg-line ${isMe?'mine':'their'}">
                <div class="bubble">
                    <b style="color:var(--blue); font-size:12px;">${m.sender}</b><br>${body}
                    <div class="m-info">
                        <span>${m.timestamp}</span>
                        ${canDel ? `<i class="fa-solid fa-trash trash-can" onclick="killMsg(${m.id})"></i>` : ''}
                    </div>
                </div>
            </div>`;
        }).join('');
        feed.scrollTop = feed.scrollHeight;
    }

    async function killMsg(id) {
        if(confirm("Удалить это сообщение навсегда?")) {
            await fetch(`/api/msg/${id}/${myName}`, {method: 'DELETE'});
            refreshFeed();
        }
    }

    function openAttach() {
        const t = prompt("Выберите медиа: 1-Фото, 2-Видео");
        const u = prompt("Вставьте прямую ссылку (URL):");
        if(u) pushMsg(t==='1'?'img':'vid', u);
    }

    function recVoice() {
        isRecording = !isRecording;
        const b = document.getElementById('voice-rec');
        b.style.color = isRecording ? 'var(--danger)' : 'var(--blue)';
        if(!isRecording) pushMsg('voice', '#');
    }

    function initCall() {
        document.getElementById('call-ava').src = document.getElementById('chat-pfp').src;
        document.getElementById('call-nick').innerText = "Вызов: " + targetChat;
        document.getElementById('call-screen').style.display = 'flex';
    }
    function dropCall() { document.getElementById('call-screen').style.display = 'none'; }

    bootApp();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
