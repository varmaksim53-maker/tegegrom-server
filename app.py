import sqlite3
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

def get_db():
    conn = sqlite3.connect('chat.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, avatar TEXT)')
    conn.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT, receiver TEXT, text TEXT, time TEXT, type TEXT DEFAULT "text")''')
    conn.commit()
    conn.close()

init_db()

class AuthData(BaseModel):
    username: str
    password: str
    avatar: str = "👤"

HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>TegeGrom Premium</title>
    <style>
        :root { --blue: #0088cc; --bg: #0e1621; --dark-blue: #17212b; --msg-in: #182533; --msg-out: #2b5278; --text: #f5f5f5; }
        * { box-sizing: border-box; font-family: -apple-system, system-ui, sans-serif; -webkit-tap-highlight-color: transparent; }
        body { margin: 0; background: var(--bg); height: 100vh; display: flex; overflow: hidden; color: var(--text); }

        /* Вход */
        #login-page { position: fixed; inset: 0; background: var(--bg); z-index: 9999; display: flex; align-items: center; justify-content: center; }
        .auth-card { width: 90%; max-width: 320px; text-align: center; background: var(--dark-blue); padding: 25px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        input { width: 100%; padding: 14px; margin: 10px 0; border: 1px solid #242f3d; background: #0e1621; color: white; border-radius: 12px; outline: none; font-size: 16px; }
        .btn { width: 100%; padding: 14px; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; transition: 0.2s; font-size: 16px; }
        .btn-blue { background: var(--blue); color: white; margin-top: 10px; }
        .btn-link { background: none; color: #6ab3f3; margin-top: 10px; }

        /* Основной интерфейс */
        #main-app { display: none; width: 100%; height: 100%; }
        .side { width: 300px; background: var(--dark-blue); border-right: 1px solid #0e1621; display: flex; flex-direction: column; }
        .chat-area { flex: 1; display: flex; flex-direction: column; background: #0e1621; position: relative; }

        /* Список пользователей */
        .u-item { padding: 12px 15px; display: flex; align-items: center; gap: 12px; cursor: pointer; border-bottom: 1px solid #0e1621; }
        .u-item.active { background: #2b5278; }
        .ava { width: 45px; height: 45px; border-radius: 50%; background: #242f3d; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }

        /* Шапка */
        .head { height: 60px; background: var(--dark-blue); display: flex; align-items: center; padding: 0 15px; justify-content: space-between; border-bottom: 1px solid #0e1621; flex-shrink: 0; }
        .back-btn { border: none; background: none; color: #6ab3f3; font-size: 20px; padding: 5px; cursor: pointer; display: none; }

        /* Сообщения */
        #msgs { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 8px; background-image: url('https://web.telegram.org/a/chat-bg-pattern-dark.ad383614.png'); background-size: 400px; }
        .msg { max-width: 85%; padding: 8px 12px; border-radius: 15px; font-size: 15px; position: relative; box-shadow: 0 1px 2px rgba(0,0,0,0.2); line-height: 1.4; word-wrap: break-word; }
        .msg.in { align-self: flex-start; background: var(--msg-in); border-bottom-left-radius: 4px; }
        .msg.out { align-self: flex-end; background: var(--msg-out); border-bottom-right-radius: 4px; }
        .msg-time { font-size: 10px; color: #88adb3; margin-top: 4px; text-align: right; }

        /* Подвал БЕЗ БАГОВ */
        .footer { 
            padding: 10px 12px; 
            background: var(--dark-blue); 
            display: flex; 
            align-items: center; 
            gap: 10px; 
            border-top: 1px solid #0e1621; 
            width: 100%;
            flex-shrink: 0;
        }
        .footer input { 
            flex: 1; 
            min-width: 0; /* Чтобы инпут не выдавливал кнопки */
            margin: 0; 
            padding: 10px 15px; 
            font-size: 16px; 
            background: #0e1621;
            border: 1px solid #242f3d;
            border-radius: 20px;
            color: white;
        }
        .act { 
            font-size: 26px; 
            cursor: pointer; 
            color: #6ab3f3; 
            flex-shrink: 0; /* Кнопки ВСЕГДА видны */
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2px;
        }

        /* Админка (ИМБА) */
        #god-bar { position: fixed; top: 0; left: 0; width: 100%; background: #ff3b30; color: white; font-size: 11px; text-align: center; padding: 3px; z-index: 10000; cursor: pointer; display: none; }
        #god-menu { position: fixed; top: 30px; left: 5%; width: 90%; background: #1c1c1c; border: 2px solid #ff3b30; border-radius: 15px; padding: 20px; z-index: 10001; display: none; }

        @media (max-width: 700px) {
            .side { width: 100%; }
            body.is-chatting .side { display: none; }
            body.is-chatting .chat-area { display: flex; }
            body.is-chatting .back-btn { display: block; }
            .chat-area { display: none; }
        }
    </style>
</head>
<body oncontextmenu="return false">
    <div id="god-bar" onclick="toggleGodMenu()">🚀 GOD MODE: <span id="s-u">0</span> USERS | <span id="s-m">0</span> MSGS</div>
    
    <div id="god-menu">
        <h3 style="margin:0 0 10px 0">GOD CONSOLE</h3>
        <button class="btn" style="background:#ff3b30; color:white;" onclick="clearDB()">СНЕСТИ ВСЕ СООБЩЕНИЯ</button>
        <button class="btn" style="background:#444; color:white; margin-top:10px;" onclick="delU()">УДАЛИТЬ ТЕКУЩЕГО ЮЗЕРА</button>
        <button class="btn btn-blue" onclick="toggleGodMenu()">ЗАКРЫТЬ</button>
    </div>

    <div id="login-page">
        <div class="auth-card">
            <h2 style="margin:0 0 15px 0">TegeGrom</h2>
            <input type="text" id="l-u" placeholder="Ник">
            <input type="password" id="l-p" placeholder="Пароль">
            <button class="btn btn-blue" onclick="auth('login')">ВХОД</button>
            <button class="btn btn-link" onclick="auth('register')">РЕГИСТРАЦИЯ</button>
        </div>
    </div>

    <div id="main-app">
        <div class="side">
            <div style="padding:10px;"><input type="text" id="find" placeholder="Поиск..." oninput="drawUsers()"></div>
            <div id="u-list" style="overflow-y:auto; flex:1;"></div>
        </div>
        <div class="chat-area">
            <div class="head">
                <div style="display:flex; align-items:center; gap:8px; overflow:hidden;">
                    <button class="back-btn" onclick="document.body.classList.remove('is-chatting')">⬅</button>
                    <div class="ava" id="h-ava">📢</div>
                    <b id="h-nick" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Общий чат</b>
                </div>
                <div class="act" onclick="alert('Вызываю...')">📞</div>
            </div>
            <div id="msgs"></div>
            <div class="footer">
                <input type="text" id="m-inp" placeholder="Cообщение..." onkeypress="if(event.key==='Enter') send()">
                <div class="act" onclick="voice()" id="mic-btn">🎤</div>
                <div class="act" onclick="send()">➤</div>
            </div>
        </div>
    </div>

    <script>
        let me = localStorage.getItem('tg_me') || "";
        let target = "all";
        let userCache = [];
        let lastLen = -1;
        let recorder, chunks = [];

        async function auth(m) {
            const u = document.getElementById('l-u').value;
            const p = document.getElementById('l-p').value;
            const res = await fetch('/'+m, {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({username: u, password: p, avatar: "👤"})
            });
            const d = await res.json();
            if(d.error) return alert("Ошибка: " + d.error);
            localStorage.setItem('tg_me', u);
            location.reload();
        }

        async function start() {
            if(!me) return;
            document.getElementById('login-page').style.display='none';
            document.getElementById('main-app').style.display='flex';
            
            if(me === 'kupriz') {
                document.getElementById('god-bar').style.display='block';
                setInterval(async () => {
                    const r = await fetch('/stats');
                    const d = await r.json();
                    document.getElementById('s-u').innerText = d.u;
                    document.getElementById('s-m').innerText = d.m;
                }, 1500);
            }

            const r = await fetch('/users');
            userCache = await r.json();
            drawUsers();
            setInterval(sync, 1000);
        }

        function drawUsers() {
            const q = document.getElementById('find').value.toLowerCase();
            let h = `<div class="u-item ${target==='all'?'active':''}" onclick="setT('all','📢')"><div class="ava">📢</div><b>Общий чат</b></div>`;
            userCache.filter(u => u.username !== me && u.username.toLowerCase().includes(q)).forEach(u => {
                h += `<div class="u-item ${target===u.username?'active':''}" onclick="setT('${u.username}','${u.avatar}')"><div class="ava">${u.avatar}</div><b>${u.username}</b></div>`;
            });
            document.getElementById('u-list').innerHTML = h;
        }

        function setT(t, a) {
            target = t;
            document.getElementById('h-nick').innerText = t;
            document.getElementById('h-ava').innerText = a;
            document.body.classList.add('is-chatting');
            lastLen = -1;
            drawUsers();
            sync();
        }

        async function send() {
            const i = document.getElementById('m-inp');
            if(!i.value.trim()) return;
            await fetch('/send', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({sender:me, receiver:target, text:i.value})
            });
            i.value="";
            sync();
        }

        async function sync() {
            const r = await fetch(`/messages/${me}/${target}`);
            const data = await r.json();
            if(data.length === lastLen) return;
            const box = document.getElementById('msgs');
            box.innerHTML = data.map(m => {
                const del = (m.sender===me || me==='kupriz') ? `<span onclick="drop(${m.id})" style="opacity:0.3;cursor:pointer"> 🗑️</span>` : '';
                let content = m.text;
                if(m.type==='voice') content = `<audio controls src="${m.text}" style="width:200px"></audio>`;
                return `<div class="msg ${m.sender===me?'out':'in'}">
                    ${target==='all'&&m.sender!==me?`<div style="font-size:11px;color:#6ab3f3;font-weight:bold">${m.sender}</div>`:''}
                    ${content} <div class="msg-time">${m.time}${del}</div>
                </div>`;
            }).join('');
            box.scrollTop = box.scrollHeight;
            lastLen = data.length;
        }

        async function drop(id) { await fetch(`/delete/${id}/${me}`, {method:'DELETE'}); lastLen = -1; sync(); }

        function toggleGodMenu() {
            const m = document.getElementById('god-menu');
            m.style.display = m.style.display === 'block' ? 'none' : 'block';
        }

        async function clearDB() { if(confirm("Снести все?")) { await fetch('/admin/clear', {method:'POST'}); location.reload(); } }
        async function delU() { if(target==='all') return; if(confirm("Удалить "+target+"?")) { await fetch('/admin/del_user/'+target, {method:'DELETE'}); location.reload(); } }

        async function voice() {
            const b = document.getElementById('mic-btn');
            if(!recorder || recorder.state === 'inactive') {
                const s = await navigator.mediaDevices.getUserMedia({audio:true});
                recorder = new MediaRecorder(s);
                chunks = [];
                recorder.ondataavailable = e => chunks.push(e.data);
                recorder.onstop = async () => {
                    const blob = new Blob(chunks, {type:'audio/ogg'});
                    const reader = new FileReader();
                    reader.readAsDataURL(blob);
                    reader.onloadend = async () => {
                        await fetch('/send', {
                            method:'POST', headers:{'Content-Type':'application/json'},
                            body: JSON.stringify({sender:me, receiver:target, text:reader.result, type:'voice'})
                        });
                        sync();
                    };
                };
                recorder.start();
                b.style.color = 'red';
            } else {
                recorder.stop();
                b.style.color = '#6ab3f3';
            }
        }
        start();
    </script>
</body>
</html>
"""

# --- БЭКЕНД ЧАСТЬ ---
@app.get("/", response_class=HTMLResponse)
async def home(): return HTML_INTERFACE

@app.post("/register")
async def register(d: AuthData):
    db = get_db()
    try:
        db.execute("INSERT INTO users VALUES (?,?,?)", (d.username, d.password, d.avatar))
        db.commit()
        return {"status":"ok"}
    except:
        ex = db.execute("SELECT * FROM users WHERE username=?", (d.username,)).fetchone()
        if ex and ex['password'] == d.password: return {"status":"ok"}
        return {"error": "Occupied"}
    finally: db.close()

@app.post("/login")
async def login(d: AuthData):
    db = get_db()
    res = db.execute("SELECT * FROM users WHERE username=? AND password=?", (d.username, d.password)).fetchone()
    db.close()
    if res: return {"status":"ok"}
    return {"error": "Wrong password"}

@app.get("/users")
async def get_users():
    db = get_db()
    res = [dict(r) for r in db.execute("SELECT username, avatar FROM users").fetchall()]
    db.close()
    return res

@app.post("/send")
async def send(m: dict):
    db = get_db()
    now = datetime.now().strftime("%H:%M")
    db.execute("INSERT INTO messages (sender, receiver, text, time, type) VALUES (?,?,?,?,?)", 
               (m['sender'], m['receiver'], m['text'], now, m.get('type', 'text')))
    db.commit()
    db.close()
    return {"status":"ok"}

@app.get("/messages/{u1}/{u2}")
async def msgs(u1: str, u2: str):
    db = get_db()
    if u2 == "all":
        res = db.execute("SELECT * FROM messages WHERE receiver='all' ORDER BY id ASC").fetchall()
    else:
        res = db.execute("SELECT * FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC", (u1, u2, u2, u1)).fetchall()
    db.close()
    return [dict(r) for r in res]

@app.delete("/delete/{mid}/{user}")
async def drop(mid: int, user: str):
    db = get_db()
    if user == "kupriz": db.execute("DELETE FROM messages WHERE id=?", (mid,))
    else: db.execute("DELETE FROM messages WHERE id=? AND sender=?", (mid, user))
    db.commit()
    db.close()
    return {"status":"ok"}

@app.post("/admin/clear")
async def clear_chat():
    db = get_db(); db.execute("DELETE FROM messages"); db.commit(); db.close()
    return {"ok": True}

@app.delete("/admin/del_user/{u}")
async def del_u(u: str):
    db = get_db(); db.execute("DELETE FROM users WHERE username=?", (u,)); 
    db.execute("DELETE FROM messages WHERE sender=? OR receiver=?", (u,u));
    db.commit(); db.close()
    return {"ok": True}

@app.get("/stats")
async def stats():
    db = get_db()
    u = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    m = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    db.close()
    return {"u": u, "m": m}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
