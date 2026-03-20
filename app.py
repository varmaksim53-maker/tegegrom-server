import socketio, uvicorn, sqlite3, hashlib
from fastapi import FastAPI
from starlette.responses import HTMLResponse

# --- 1. НАСТРОЙКА БАЗЫ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    # Таблица пользователей
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    # Таблица сообщений с фиксацией времени
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (sender TEXT, receiver TEXT, text TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. НАСТРОЙКА СЕРВЕРА ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
socket_app = socketio.ASGIApp(sio, app)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Messenger v2.0</title>
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; height: 100vh; background: #e6ebee; }
        #auth { position: fixed; width: 100%; height: 100%; background: white; z-index: 100; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; }
        #sidebar { width: 280px; background: white; border-right: 1px solid #ddd; display: flex; flex-direction: column; }
        #chat-area { flex: 1; display: flex; flex-direction: column; background: #f5f5f5; }
        .header { padding: 15px; background: #0088cc; color: white; font-weight: bold; display: flex; justify-content: space-between; align-items: center; }
        .search-box { padding: 10px; border-bottom: 1px solid #eee; }
        .search-box input { width: 100%; padding: 8px; border-radius: 20px; border: 1px solid #ddd; outline: none; }
        #chat-list { flex: 1; overflow-y: auto; }
        .chat-item { padding: 15px; cursor: pointer; border-bottom: 1px solid #f9f9f9; }
        .chat-item:hover { background: #f0f0f0; }
        .chat-item.active { background: #e3f2fd; border-left: 4px solid #0088cc; }
        #messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .msg { max-width: 80%; padding: 10px; border-radius: 10px; font-size: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .msg.my { align-self: flex-end; background: #effdde; border: 1px solid #c8e6c9; }
        .msg.other { align-self: flex-start; background: white; border: 1px solid #ddd; }
        .input-area { padding: 15px; background: white; display: flex; gap: 10px; border-top: 1px solid #ddd; }
        .input-area input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 8px; outline: none; }
        button { padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; background: #0088cc; color: white; font-weight: bold; }
    </style>
</head>
<body>

<div id="auth">
    <h2>🚪 Вход в сеть</h2>
    <input type="text" id="userIn" placeholder="Никнейм">
    <input type="password" id="passIn" placeholder="Пароль">
    <button onclick="login()">Войти / Регистрация</button>
</div>

<div id="sidebar">
    <div class="header">Чаты <span id="my-nick" style="font-size: 12px; opacity: 0.8;"></span></div>
    <div class="search-box"><input type="text" id="search-input" placeholder="Поиск ника (Enter)..." onkeyup="searchUser(event)"></div>
    <div id="chat-list">
        <div class="chat-item active" id="item-global" onclick="switchChat('global')"><b>🌍 Общий чат</b></div>
    </div>
</div>

<div id="chat-area">
    <div class="header" id="chat-title">🌍 Общий чат</div>
    <div id="messages"></div>
    <div class="input-area">
        <input type="text" id="msg-input" placeholder="Напишите сообщение..." onkeypress="if(event.key==='Enter') send()">
        <button onclick="send()">➤</button>
    </div>
</div>

<script>
    const socket = io();
    let myName = "", currentChat = "global", activeChats = new Set();

    function login() {
        myName = document.getElementById('userIn').value;
        const pass = document.getElementById('passIn').value;
        if(myName && pass) socket.emit('login', { user: myName, pass: pass });
    }

    socket.on('login_res', (data) => {
        if(data.success) {
            document.getElementById('auth').style.display = 'none';
            document.getElementById('my-nick').innerText = "@" + myName;
            switchChat('global');
        } else alert(data.msg);
    });

    function switchChat(target) {
        currentChat = target;
        document.getElementById('chat-title').innerText = target === 'global' ? '🌍 Общий чат' : '👤 ' + target;
        document.getElementById('messages').innerHTML = ""; 
        
        document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
        const activeEl = document.getElementById('item-' + target);
        if(activeEl) activeEl.classList.add('active');

        // Запрашиваем историю
        socket.emit('get_history', { chat: target });
    }

    socket.on('chat_history', (data) => {
        data.messages.forEach(m => addMsg(m.sender, m.text, m.sender === myName));
    });

    function searchUser(e) {
        if(e.key === 'Enter') {
            const nick = document.getElementById('search-input').value;
            if(nick && nick !== myName) addChatItem(nick);
            document.getElementById('search-input').value = "";
        }
    }

    function addChatItem(nick) {
        if(activeChats.has(nick)) return;
        activeChats.add(nick);
        const div = document.createElement('div');
        div.className = 'chat-item';
        div.id = 'item-' + nick;
        div.onclick = () => switchChat(nick);
        div.innerHTML = `<b>👤 ${nick}</b>`;
        document.getElementById('chat-list').appendChild(div);
    }

    function send() {
        const text = document.getElementById('msg-input').value;
        if(!text) return;
        if(currentChat === 'global') {
            socket.emit('global_msg', { text: text });
        } else {
            socket.emit('private_msg', { to: currentChat, text: text });
            addMsg(myName, text, true);
        }
        document.getElementById('msg-input').value = "";
    }

    function addMsg(sender, text, isMy) {
        const div = document.createElement('div');
        div.className = `msg ${isMy ? 'my' : 'other'}`;
        div.innerHTML = `<b>${sender}:</b> ${text}`;
        const container = document.getElementById('messages');
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    socket.on('new_global', (data) => {
        if(currentChat === 'global') addMsg(data.from, data.text, data.from === myName);
    });

    socket.on('new_private', (data) => {
        addChatItem(data.from);
        if(currentChat === data.from) addMsg(data.from, data.text, false);
    });
</script>
</body>
</html>
"""

# --- 3. ОБРАБОТЧИКИ СОБЫТИЙ ---

@app.get("/")
async def get():
    return HTMLResponse(content=HTML_TEMPLATE)

@sio.event
async def login(sid, data):
    user, p_hash = data['user'], hashlib.sha256(data['pass'].encode()).hexdigest()
    conn = sqlite3.connect('chat.db'); c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username=?', (user,))
    row = c.fetchone()
    if row:
        if row[0] == p_hash:
            await sio.save_session(sid, {'user': user})
            await sio.enter_room(sid, user)
            await sio.emit('login_res', {'success': True}, room=sid)
        else: await sio.emit('login_res', {'success': False, 'msg': 'Неверный пароль'}, room=sid)
    else:
        c.execute('INSERT INTO users VALUES (?, ?)', (user, p_hash))
        conn.commit(); await sio.save_session(sid, {'user': user})
        await sio.enter_room(sid, user); await sio.emit('login_res', {'success': True}, room=sid)
    conn.close()

@sio.event
async def get_history(sid, data):
    session = await sio.get_session(sid)
    if not session: return
    user, target = session['user'], data['chat']
    conn = sqlite3.connect('chat.db'); c = conn.cursor()
    if target == 'global':
        c.execute('SELECT sender, text FROM messages WHERE receiver="global" ORDER BY ts ASC LIMIT 50')
    else:
        c.execute('''SELECT sender, text FROM messages 
                     WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) 
                     ORDER BY ts ASC LIMIT 50''', (user, target, target, user))
    history = [{"sender": r[0], "text": r[1]} for r in c.fetchall()]
    await sio.emit('chat_history', {'messages': history}, room=sid)
    conn.close()

@sio.event
async def global_msg(sid, data):
    session = await sio.get_session(sid)
    user = session['user']
    conn = sqlite3.connect('chat.db'); c = conn.cursor()
    c.execute('INSERT INTO messages (sender, receiver, text) VALUES (?, ?, ?)', (user, "global", data['text']))
    conn.commit(); conn.close()
    await sio.emit('new_global', {'from': user, 'text': data['text']})

@sio.event
async def private_msg(sid, data):
    session = await sio.get_session(sid)
    user, target = session['user'], data['to']
    conn = sqlite3.connect('chat.db'); c = conn.cursor()
    c.execute('INSERT INTO messages (sender, receiver, text) VALUES (?, ?, ?)', (user, target, data['text']))
    conn.commit(); conn.close()
    await sio.emit('new_private', {'from': user, 'text': data['text']}, room=target)

if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=5555)
