import sqlite3, uvicorn, os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

app = FastAPI()
DB = 'tegegrom_v17.db'

# --- Инициализация БД ---
def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            sender TEXT, receiver TEXT, content TEXT, 
            timestamp TEXT, type TEXT DEFAULT 'text', file TEXT DEFAULT '')''')
        conn.commit()

init_db()

@app.get("/", response_class=HTMLResponse)
async def index(): return UI

@app.get("/api/get/{me}/{to}")
async def get_msgs(me: str, to: str, last: int = 0):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        if to == "all":
            res = conn.execute("SELECT * FROM messages WHERE receiver='all' AND id > ? ORDER BY id ASC", (last,)).fetchall()
        else:
            res = conn.execute("SELECT * FROM messages WHERE ((sender=? AND receiver=?) OR (sender=? AND receiver=?)) AND id > ? ORDER BY id ASC", 
                               (me, to, to, me, last)).fetchall()
        return [dict(r) for r in res]

@app.post("/api/send")
async def send_msg(d: dict):
    with sqlite3.connect(DB) as conn:
        t = datetime.now().strftime("%H:%M")
        conn.execute("INSERT INTO messages (sender, receiver, content, timestamp, type, file) VALUES (?,?,?,?,?,?)",
                     (d['s'], d['r'], d['c'], t, d['t'], d.get('f', '')))
        conn.commit()
    return {"ok": True}

# --- ИНТЕРФЕЙС ---
UI = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>TegeGrom v17 Stable</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --bg: #0e1621; --side: #17212b; --blue: #0088cc; --txt: #f5f5f5; --in: #182533; --out: #2b5278; }
        * { box-sizing: border-box; font-family: sans-serif; }
        body { margin: 0; background: var(--bg); color: var(--txt); height: 100vh; display: flex; overflow: hidden; }
        
        /* Авторизация */
        #auth { position: fixed; inset: 0; z-index: 1000; background: var(--bg); display: flex; align-items: center; justify-content: center; }
        .auth-box { background: var(--side); padding: 30px; border-radius: 20px; text-align: center; width: 90%; max-width: 350px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border-radius: 10px; border: 1px solid #242f3d; background: #0b1118; color: white; }

        /* Боковая панель */
        #side { width: 300px; background: var(--side); border-right: 1px solid #000; display: flex; flex-direction: column; transition: 0.3s; }
        .chat-item { padding: 15px; cursor: pointer; border-bottom: 1px solid rgba(0,0,0,0.2); display: flex; align-items: center; gap: 10px; }
        .chat-item:hover { background: rgba(255,255,255,0.05); }
        .chat-item.active { background: var(--out); }
        .ava { width: 40px; height: 40px; border-radius: 50%; background: var(--blue); display: flex; align-items:center; justify-content:center; }

        /* Окно чата */
        #main { flex: 1; display: flex; flex-direction: column; background: #0e1117; position: relative; }
        #feed { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 8px; }
        
        .msg { max-width: 85%; padding: 8px 12px; border-radius: 12px; line-height: 1.4; position: relative; font-size: 15px; }
        .msg.out { align-self: flex-end; background: var(--out); border-bottom-right-radius: 2px; }
        .msg.in { align-self: flex-start; background: var(--in); border-bottom-left-radius: 2px; }
        .msg img { max-width: 100%; border-radius: 8px; margin-top: 5px; cursor: pointer; }
        .time { font-size: 10px; opacity: 0.5; text-align: right; margin-top: 4px; }

        /* Поле ввода */
        .input-area { padding: 10px; background: var(--side); display: flex; align-items: center; gap: 10px; }
        .btn-icon { color: var(--blue); font-size: 20px; cursor: pointer; }

        /* Мобильная адаптация */
        @media (max-width: 700px) {
            #side { position: absolute; width: 100%; height: 100%; z-index: 100; }
            body.in-chat #side { transform: translateX(-100%); }
            .back { display: block !important; }
        }
        .back { display: none; margin-right: 10px; cursor: pointer; font-size: 20px; }
    </style>
</head>
<body>

<div id="auth">
    <div class="auth-box">
        <h2 style="color:var(--blue)">TegeGrom</h2>
        <input type="text" id="my-name" placeholder="Введите ваш ник">
        <button onclick="saveName()" style="width:100%; padding:12px; background:var(--blue); border:none; color:white; border-radius:10px; cursor:pointer;">Войти</button>
    </div>
</div>

<div id="side">
    <div style="padding:15px; border-bottom:1px solid #000;"><b>Чаты</b></div>
    <div class="chat-item" onclick="selectChat('all')"><div class="ava">📢</div><b>Общий чат</b></div>
    <div id="contacts"></div>
</div>

<div id="main">
    <div style="padding:15px; background:var(--side); display:flex; align-items:center;">
        <i class="fa-solid fa-arrow-left back" onclick="document.body.classList.remove('in-chat')"></i>
        <b id="chat-title">Выберите чат</b>
    </div>
    <div id="feed"></div>
    <div class="input-area">
        <label class="btn-icon"><i class="fa-solid fa-image"></i><input type="file" id="f-in" hidden onchange="upFile()"></label>
        <input type="text" id="m-in" class="input" style="flex:1; background:#0b1118; border:none; padding:10px; color:white; border-radius:15px;" placeholder="Сообщение..." onkeypress="if(event.key==='Enter')send('text')">
        <i class="fa-solid fa-paper-plane btn-icon" onclick="send('text')"></i>
    </div>
</div>

<script>
    let me = localStorage.getItem('tg_name') || "";
    let target = "all";
    let lastId = 0;
    let syncing = false;

    if(me) { document.getElementById('auth').style.display='none'; startSync(); }

    function saveName() {
        const n = document.getElementById('my-name').value.trim();
        if(n) { localStorage.setItem('tg_name', n); location.reload(); }
    }

    function selectChat(t) {
        target = t; lastId = 0;
        document.getElementById('chat-title').innerText = t === 'all' ? 'Общий чат' : t;
        document.getElementById('feed').innerHTML = '';
        document.body.classList.add('in-chat');
        sync();
    }

    async function send(type, content='', file='') {
        const inp = document.getElementById('m-in');
        const txt = content || inp.value.trim();
        if(!txt && !file) return;
        
        await fetch('/api/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({s:me, r:target, c:txt, t:type, f:file})
        });
        inp.value = '';
        sync();
    }

    async function sync() {
        if(syncing || !me) return;
        syncing = true;
        try {
            const r = await fetch(`/api/get/${me}/${target}?last=${lastId}`);
            const data = await r.json();
            const f = document.getElementById('feed');
            
            data.forEach(m => {
                if(m.id > lastId) {
                    lastId = m.id;
                    const div = document.createElement('div');
                    div.className = `msg ${m.sender === me ? 'out' : 'in'}`;
                    
                    let body = m.type === 'img' ? `<img src="${m.file}" onclick="window.open(this.src)">` : `<span>${m.content}</span>`;
                    div.innerHTML = `<b style="font-size:12px; color:var(--blue)">${m.sender}</b><br>${body}<div class="time">${m.timestamp}</div>`;
                    f.appendChild(div);
                    f.scrollTop = f.scrollHeight;
                }
            });
        } finally { syncing = false; }
    }

    function upFile() {
        const file = document.getElementById('f-in').files[0];
        const reader = new FileReader();
        reader.onload = () => send('img', '', reader.result);
        reader.readAsDataURL(file);
    }

    function startSync() { setInterval(sync, 1500); }
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
