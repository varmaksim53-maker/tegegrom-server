import sqlite3, uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from datetime import datetime

app = FastAPI()
DB = 'tegegrom_v21_final.db'

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

@app.get("/api/get_users")
async def get_users():
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        res = conn.execute("SELECT DISTINCT sender FROM messages WHERE sender != 'all'").fetchall()
        return [r['sender'] for r in res]

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

UI = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>TegeGrom Premium</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --bg: #0e1621; --side: #17212b; --blue: #0088cc; --txt: #f5f5f5; --in: #182533; --out: #2b5278; }
        * { box-sizing: border-box; font-family: -apple-system, sans-serif; }
        body { margin: 0; background: var(--bg); color: var(--txt); height: 100vh; display: flex; overflow: hidden; }
        
        #auth { position: fixed; inset: 0; z-index: 2000; background: var(--bg); display: flex; align-items: center; justify-content: center; }
        .auth-box { background: var(--side); padding: 30px; border-radius: 20px; text-align: center; width: 90%; max-width: 350px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border-radius: 10px; border: 1px solid #242f3d; background: #0b1118; color: white; outline: none; }

        #side { width: 300px; background: var(--side); border-right: 1px solid #000; display: flex; flex-direction: column; transition: 0.3s; z-index: 100; }
        .chat-item { padding: 15px; cursor: pointer; border-bottom: 1px solid rgba(0,0,0,0.1); display: flex; align-items: center; gap: 12px; }
        .chat-item:hover, .chat-item.active { background: var(--out); }
        .ava-circle { width: 42px; height: 42px; background: var(--blue); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; }

        #main { flex: 1; display: flex; flex-direction: column; background: #0e1117; position: relative; }
        #feed { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 8px; padding-bottom: 160px; scroll-behavior: smooth; }
        
        .msg { max-width: 80%; padding: 10px 14px; border-radius: 16px; font-size: 15px; line-height: 1.4; position: relative; }
        .msg.out { align-self: flex-end; background: var(--out); border-bottom-right-radius: 4px; }
        .msg.in { align-self: flex-start; background: var(--in); border-bottom-left-radius: 4px; }
        .msg img { max-width: 100%; border-radius: 8px; margin-top: 6px; }
        .time { font-size: 10px; opacity: 0.5; text-align: right; margin-top: 4px; }

        /* ЕЩЕ ВЫШЕ И КРУЧЕ ДЛЯ ТЕЛЕФОНОВ */
        .bar { 
            padding: 15px 20px; 
            background: var(--side); 
            display: flex; 
            align-items: center; 
            gap: 15px; 
            padding-bottom: calc(50px + env(safe-area-inset-bottom)); /* Подняли еще на 15px */
            border-top: 1px solid rgba(255,255,255,0.05);
            position: absolute; bottom: 0; left: 0; right: 0;
            box-shadow: 0 -10px 20px rgba(0,0,0,0.3);
        }
        .inp { flex: 1; background: #0b1118; border: none; padding: 12px 18px; color: white; border-radius: 25px; font-size: 16px; outline: none; }
        .icon { color: var(--blue); font-size: 26px; cursor: pointer; }

        @media (max-width: 700px) {
            #side { position: absolute; width: 100%; height: 100%; left: 0; }
            body.chatting #side { transform: translateX(-100%); }
            .back { display: block !important; }
        }
        .back { display: none; margin-right: 15px; cursor: pointer; font-size: 24px; color: var(--blue); }
    </style>
</head>
<body>

<div id="auth">
    <div class="auth-box">
        <h2 style="color:var(--blue)">TegeGrom</h2>
        <input type="text" id="my-name" placeholder="Никнейм">
        <button onclick="login()" style="width:100%; padding:14px; background:var(--blue); border:none; color:white; border-radius:12px; font-weight:bold;">Войти</button>
    </div>
</div>

<div id="side">
    <div style="padding:20px; border-bottom:1px solid rgba(0,0,0,0.3); font-weight:bold; font-size:20px;">Чаты</div>
    <div class="chat-item active" id="btn-all" onclick="selectChat('all')">
        <div class="ava-circle">📢</div> <b>Общий чат</b>
    </div>
    <div id="contacts-list" style="overflow-y:auto; flex:1;"></div>
</div>

<div id="main">
    <div style="padding:12px 20px; background:var(--side); display:flex; align-items:center; border-bottom:1px solid rgba(0,0,0,0.3);">
        <i class="fa-solid fa-arrow-left back" onclick="document.body.classList.remove('chatting')"></i>
        <b id="header-title" style="font-size: 18px;">Общий чат</b>
    </div>
    <div id="feed"></div>
    <div class="bar">
        <label class="icon"><i class="fa-solid fa-paperclip"></i><input type="file" id="f-in" hidden onchange="upFile()"></label>
        <input type="text" id="m-in" class="inp" placeholder="Сообщение..." onkeypress="if(event.key==='Enter')send('text')">
        <i class="fa-solid fa-circle-arrow-up icon" onclick="send('text')"></i>
    </div>
</div>

<script>
    let myName = localStorage.getItem('tg_v21_user') || "";
    let target = "all";
    let lastId = 0;
    let isSyncing = false;

    if(myName) { document.getElementById('auth').style.display='none'; startApp(); }

    function login() {
        const n = document.getElementById('my-name').value.trim();
        if(n) { localStorage.setItem('tg_v21_user', n); location.reload(); }
    }

    function startApp() {
        setInterval(sync, 1500);
        setInterval(loadUsers, 5000);
        loadUsers();
    }

    function selectChat(t) {
        target = t; lastId = 0;
        document.getElementById('header-title').innerText = t === 'all' ? 'Общий чат' : t;
        document.getElementById('feed').innerHTML = '';
        document.body.classList.add('chatting');
        document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
        if(t === 'all') document.getElementById('btn-all').classList.add('active');
        sync();
    }

    async function loadUsers() {
        const r = await fetch('/api/get_users');
        const users = await r.json();
        const list = document.getElementById('contacts-list');
        let html = '';
        users.forEach(u => {
            if(u !== myName) {
                html += `<div class="chat-item ${target===u?'active':''}" onclick="selectChat('${u}')">
                    <div class="ava-circle" style="background:#2b5278">${u[0].toUpperCase()}</div> <b>${u}</b>
                </div>`;
            }
        });
        list.innerHTML = html;
    }

    async function send(type, content='', file='') {
        const inp = document.getElementById('m-in');
        const txt = content || inp.value.trim();
        if(!txt && !file) return;
        await fetch('/api/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({s:myName, r:target, c:txt, t:type, f:file})
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
                    let body = m.type === 'img' ? `<img src="${m.file}" onclick="window.open(this.src)">` : `<span>${m.content}</span>`;
                    div.innerHTML = `<b style="font-size:11px; color:var(--blue)">${m.sender}</b><br>${body}<div class="time">${m.timestamp}</div>`;
                    f.appendChild(div);
                    f.scrollTop = f.scrollHeight;
                }
            });
        } finally { isSyncing = false; }
    }

    function upFile() {
        const file = document.getElementById('f-in').files[0];
        if(!file) return;
        const reader = new FileReader();
        reader.onload = () => send('img', '', reader.result);
        reader.readAsDataURL(file);
    }
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
