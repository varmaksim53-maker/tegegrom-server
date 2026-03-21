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
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <title>TegeGrom GOD MODE</title>
    <style>
        :root { --blue: #0088cc; --bg: #0e1621; --white: #17212b; --text: #f5f5f5; --out: #2b5278; }
        * { box-sizing: border-box; font-family: -apple-system, system-ui, sans-serif; }
        body { margin: 0; background: var(--bg); height: 100vh; display: flex; overflow: hidden; color: var(--text); }

        /* Вход */
        #login-page { position: fixed; inset: 0; background: var(--bg); z-index: 9999; display: flex; align-items: center; justify-content: center; }
        .auth-card { width: 90%; max-width: 350px; text-align: center; background: var(--white); padding: 30px; border-radius: 20px; border: 1px solid #242f3d; }
        input { width: 100%; padding: 15px; margin: 10px 0; border: 1px solid #242f3d; background: #0e1621; color: white; border-radius: 12px; outline: none; }
        .btn { width: 100%; padding: 15px; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; transition: 0.3s; }
        .btn-blue { background: var(--blue); color: white; }
        .btn-link { background: none; color: #6ab3f3; margin-top: 10px; }

        /* Интерфейс */
        #main-app { display: none; width: 100%; height: 100%; }
        .side { width: 300px; background: var(--white); border-right: 1px solid #0e1621; display: flex; flex-direction: column; }
        .chat-area { flex: 1; display: flex; flex-direction: column; background: #0e1621; }

        /* Список */
        .u-item { padding: 12px; display: flex; align-items: center; gap: 12px; cursor: pointer; transition: 0.2s; border-bottom: 1px solid #0e1621; }
        .u-item:hover { background: #242f3d; }
        .u-item.active { background: #2b5278; }
        .ava { width: 45px; height: 45px; border-radius: 50%; background: #242f3d; display: flex; align-items: center; justify-content: center; font-size: 20px; }

        /* Сообщения */
        #msgs { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
        .msg { max-width: 80%; padding: 10px 15px; border-radius: 15px; font-size: 15px; line-height: 1.4; position: relative; }
        .msg.in { align-self: flex-start; background: var(--white); border-bottom-left-radius: 4px; }
        .msg.out { align-self: flex-end; background: var(--out); border-bottom-right-radius: 4px; }

        /* Имба-Админка */
        #god-panel { position: fixed; top: 0; left: 0; right: 0; background: #ff3b30; color: white; font-size: 12px; padding: 5px 15px; z-index: 10000; font-family: monospace; display: none; cursor: pointer; }
        #admin-menu { position: fixed; top: 30px; left: 10px; background: #1c1c1c; border: 2px solid #ff3b30; border-radius: 10px; padding: 15px; z-index: 10001; display: none; width: 250px; }
        .admin-btn { background: #ff3b30; color: white; border: none; padding: 8px; width: 100%; border-radius: 5px; margin-top: 10px; cursor: pointer; font-weight: bold; }
        
        /* Стили чата */
        .head { height: 60px; background: var(--white); display: flex; align-items: center; padding: 0 15px; justify-content: space-between; border-bottom: 1px solid #0e1621; }
        .footer { padding: 10px; background: var(--white); display: flex; align-items: center; gap: 10px; }
        .footer input { margin: 0; }
        .act { font-size: 24px; cursor: pointer; color: #6ab3f3; }
        .admin-only { color: #ff3b30 !important; font-weight: bold; }
    </style>
</head>
<body>
    <div id="god-panel" onclick="toggleAdminMenu()">
        🔥 GOD MODE: <span id="st-u">0</span> USERS | <span id="st-m">0</span> MSGS | CLICK TO OPEN MENU
    </div>

    <div id="admin-menu">
        <h3 style="margin-top:0">GOD CONSOLE</h3>
        <p style="font-size:11px; opacity:0.7">Управление базой данных</p>
        <button class="admin-btn" onclick="clearAllMsgs()">ОЧИСТИТЬ ВЕСЬ ЧАТ</button>
        <button class="admin-btn" onclick="deleteTarget()" id="del-u-btn">УДАЛИТЬ ТЕКУЩЕГО ЮЗЕРА</button>
        <button class="admin-btn" style="background:#444" onclick="toggleAdminMenu()">ЗАКРЫТЬ</button>
    </div>

    <div id="login-page">
        <div class="auth-card">
            <h2>TegeGrom</h2>
            <input type="text" id="log" placeholder="Username">
            <input type="password" id="pas" placeholder="Password">
            <button class="btn btn-blue" onclick="auth('login')">ВХОД</button>
            <button class="btn btn-link" onclick="auth('register')">РЕГИСТРАЦИЯ</button>
        </div>
    </div>

    <div id="main-app">
        <div class="side">
            <div style="padding:10px;"><input type="text" id="find" placeholder="Поиск..." oninput="draw()"></div>
            <div id="u-list" style="overflow-y:auto; flex:1;"></div>
        </div>
        <div class="chat-area">
            <div class="head">
                <div style="display:flex; align-items:center; gap:10px">
                    <div class="ava" id="h-ava">📢</div>
                    <b id="h-nick">Общий чат</b>
                </div>
            </div>
            <div id="msgs"></div>
            <div class="footer">
                <input type="text" id="m-inp" placeholder="Message..." onkeypress="if(event.key==='Enter') send()">
                <div class="act" onclick="send()">➤</div>
            </div>
        </div>
    </div>

    <script>
        let me = localStorage.getItem('tg_me') || "";
        let target = "all";
        let users = [];
        let lastC = -1;

        async function auth(m) {
            const u = document.getElementById('log').value;
            const p = document.getElementById('pas').value;
            const r = await fetch('/'+m, {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({username: u, password: p, avatar: "👤"})
            });
            const d = await r.json();
            if(d.error) return alert(d.error);
            localStorage.setItem('tg_me', u);
            location.reload();
        }

        async function start() {
            if(!me) return;
            document.getElementById('login-page').style.display='none';
            document.getElementById('main-app').style.display='flex';
            
            if(me === 'kupriz') {
                document.getElementById('god-panel').style.display='block';
                setInterval(async () => {
                    const r = await fetch('/stats');
                    const d = await r.json();
                    document.getElementById('st-u').innerText = d.u;
                    document.getElementById('st-m').innerText = d.m;
                }, 1000);
            }

            const r = await fetch('/users');
            users = await r.json();
            draw();
            setInterval(sync, 1000);
        }

        function draw() {
            const q = document.getElementById('find').value.toLowerCase();
            let h = `<div class="u-item ${target==='all'?'active':''}" onclick="setT('all','📢')"><div class="ava">📢</div><b>Общий чат</b></div>`;
            users.filter(u => u.username !== me && u.username.toLowerCase().includes(q)).forEach(u => {
                h += `<div class="u-item ${target===u.username?'active':''}" onclick="setT('${u.username}','${u.avatar}')">
                    <div class="ava">${u.avatar}</div><b>${u.username}</b>
                </div>`;
            });
            document.getElementById('u-list').innerHTML = h;
        }

        function setT(t, a) {
            target = t;
            document.getElementById('h-nick').innerText = t;
            document.getElementById('h-ava').innerText = a;
            document.getElementById('del-u-btn').innerText = t === 'all' ? "НЕЛЬЗЯ УДАЛИТЬ ОБЩИЙ ЧАТ" : "УДАЛИТЬ " + t;
            lastC = -1;
            draw();
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
            if(data.length === lastC) return;
            const box = document.getElementById('msgs');
            box.innerHTML = data.map(m => {
                const del = (m.sender===me || me==='kupriz') ? `<span onclick="drop(${m.id})" style="cursor:pointer;opacity:0.3"> 🗑️</span>` : '';
                return `<div class="msg ${m.sender===me?'out':'in'}">
                    ${target==='all'&&m.sender!==me?`<div style="font-size:11px;color:#6ab3f3">${m.sender}</div>`:''}
                    ${m.text} <span style="font-size:10px;opacity:0.5">${m.time}${del}</span>
                </div>`;
            }).join('');
            box.scrollTop = box.scrollHeight;
            lastC = data.length;
        }

        function toggleAdminMenu() {
            const m = document.getElementById('admin-menu');
            m.style.display = m.style.display === 'block' ? 'none' : 'block';
        }

        async function drop(id) { await fetch(`/delete/${id}/${me}`, {method:'DELETE'}); sync(); }

        // --- ИМБА ФУНКЦИИ ---
        async function clearAllMsgs() {
            if(confirm("ТЫ УВЕРЕН? ВСЕ СООБЩЕНИЯ ИСЧЕЗНУТ!")) {
                await fetch('/admin/clear_msgs', {method:'POST'});
                location.reload();
            }
        }

        async function deleteTarget() {
            if(target === 'all') return;
            if(confirm("УДАЛИТЬ ПОЛЬЗОВАТЕЛЯ " + target + "?")) {
                await fetch(`/admin/delete_user/${target}`, {method:'DELETE'});
                location.reload();
            }
        }

        start();
    </script>
</body>
</html>
"""

# --- ЭНДПОИНТЫ ---
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
    return {"error": "Wrong pass"}

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
    db.execute("INSERT INTO messages (sender, receiver, text, time) VALUES (?,?,?,?)", (m['sender'], m['receiver'], m['text'], now))
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

# --- ЭКСКЛЮЗИВНЫЕ АДМИН-МЕТОДЫ ---
@app.post("/admin/clear_msgs")
async def clear_msgs():
    db = get_db()
    db.execute("DELETE FROM messages")
    db.commit()
    db.close()
    return {"status":"cleaned"}

@app.delete("/admin/delete_user/{username}")
async def delete_user(username: str):
    db = get_db()
    db.execute("DELETE FROM users WHERE username=?", (username,))
    db.execute("DELETE FROM messages WHERE sender=? OR receiver=?", (username, username))
    db.commit()
    db.close()
    return {"status":"user_deleted"}

@app.get("/stats")
async def stats():
    db = get_db()
    u = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    m = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    db.close()
    return {"u": u, "m": m}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
