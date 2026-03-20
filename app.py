import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List

app = FastAPI()
messages = []

class Msg(BaseModel):
    u: str
    m: str
    to: str = "all"

HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>TegeGrom Legacy</title>
    <style>
        body { margin: 0; font-family: 'Segoe UI', Tahoma, sans-serif; display: flex; height: 100vh; background: #f0f2f5; overflow: hidden; }
        
        /* Боковая панель (Список чатов) */
        .sidebar { width: 320px; background: #ffffff; border-right: 1px solid #ddd; display: flex; flex-direction: column; }
        .sidebar-header { padding: 15px; background: #0088cc; color: white; font-weight: bold; font-size: 18px; }
        .search-box { padding: 10px; background: #f4f4f4; border-bottom: 1px solid #eee; }
        .search-box input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; outline: none; background: #fff; }
        
        .chats-list { flex: 1; overflow-y: auto; }
        .chat-item { padding: 15px; border-bottom: 1px solid #f9f9f9; cursor: pointer; display: flex; align-items: center; transition: 0.2s; }
        .chat-item:hover { background: #f1f1f1; }
        .chat-item.active { background: #e7f3ff; border-left: 4px solid #0088cc; }
        
        .avatar { width: 45px; height: 45px; background: #0088cc; border-radius: 50%; margin-right: 12px; 
                  display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; flex-shrink: 0; }

        /* Основная зона чата */
        .main-chat { flex: 1; display: flex; flex-direction: column; background: #e5ddd5; background-image: url('https://web.telegram.org/a/chat-bg-pattern-light.693798b1.png'); }
        .chat-header { padding: 10px 20px; background: #ffffff; border-bottom: 1px solid #ddd; display: flex; align-items: center; z-index: 10; }
        #chat-window { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 8px; }
        
        /* Сообщения (Бабблы) */
        .msg { max-width: 75%; padding: 8px 14px; border-radius: 12px; font-size: 15px; position: relative; box-shadow: 0 1px 2px rgba(0,0,0,0.1); line-height: 1.4; }
        .msg.in { align-self: flex-start; background: #ffffff; border-top-left-radius: 2px; }
        .msg.out { align-self: flex-end; background: #efffde; border-top-right-radius: 2px; }
        .msg b { color: #0088cc; font-size: 13px; display: block; margin-bottom: 2px; }
        .msg .time { font-size: 10px; color: #999; text-align: right; margin-top: 4px; }

        /* Панель ввода */
        .input-area { padding: 10px 20px; background: #ffffff; display: flex; gap: 12px; align-items: center; border-top: 1px solid #ddd; }
        .input-area input { flex: 1; padding: 12px 18px; border-radius: 25px; border: 1px solid #ddd; outline: none; font-size: 15px; }
        .send-btn { background: #0088cc; color: white; border: none; width: 45px; height: 45px; border-radius: 50%; cursor: pointer; font-size: 20px; transition: 0.3s; }
        .send-btn:hover { background: #0077b3; transform: scale(1.05); }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">TegeGrom Legacy</div>
        <div class="search-box">
            <input id="search-user" placeholder="Поиск по нику (кому писать ЛС)..." oninput="changeChat(this.value)">
        </div>
        <div class="chats-list">
            <div class="chat-item active" id="chat-all" onclick="changeChat('all')">
                <div class="avatar" style="background: #2196F3;">📢</div>
                <div><b>Общий чат</b><br><small>Все пользователи здесь</small></div>
            </div>
            <div id="private-chats-list"></div>
        </div>
    </div>

    <div class="main-chat">
        <div class="chat-header">
            <div class="avatar" id="header-avatar" style="background: #2196F3;">📢</div>
            <div><b id="chat-title">Общий чат</b><br><small style="color: #4CAF50;">в сети</small></div>
        </div>
        <div id="chat-window"></div>
        <div class="input-area">
            <input id="my-nick" placeholder="Твой ник" style="width: 100px; flex: none; border-right: 1px solid #eee;">
            <input id="message-text" placeholder="Напишите сообщение..." onkeypress="if(event.key==='Enter') sendMsg()">
            <button class="send-btn" onclick="sendMsg()">➤</button>
        </div>
    </div>

    <script>
        let currentTarget = "all";
        let myNick = localStorage.getItem('tg-nick') || "";
        let allMsgs = [];

        if(myNick) document.getElementById('my-nick').value = myNick;

        function changeChat(target) {
            currentTarget = target || "all";
            document.getElementById('chat-title').innerText = currentTarget === "all" ? "Общий чат" : "ЛС: " + currentTarget;
            document.getElementById('header-avatar').innerText = currentTarget === "all" ? "📢" : currentTarget[0].toUpperCase();
            
            // Подсветка активного чата
            document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
            if(currentTarget === 'all') document.getElementById('chat-all').classList.add('active');
            
            renderMessages();
        }

        async function sendMsg() {
            const nick = document.getElementById('my-nick').value.trim() || "Аноним";
            const text = document.getElementById('message-text').value.trim();
            if(!text) return;
            
            myNick = nick;
            localStorage.setItem('tg-nick', myNick);
            
            await fetch('/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({u: nick, m: text, to: currentTarget})
            });
            document.getElementById('message-text').value = "";
        }

        function renderMessages() {
            const win = document.getElementById('chat-window');
            const filtered = allMsgs.filter(m => {
                if(currentTarget === "all") return m.to === "all";
                return (m.u === currentTarget && m.to === myNick) || (m.u === myNick && m.to === currentTarget);
            });

            win.innerHTML = filtered.map(m => `
                <div class="msg ${m.u === myNick ? 'out' : 'in'}">
                    <b>${m.u}</b>
                    ${m.m}
                    <div class="time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                </div>
            `).join('');
            win.scrollTop = win.scrollHeight;
        }

        // Авто-обновление каждые 2 секунды
        setInterval(async () => {
            try {
                const r = await fetch('/get');
                allMsgs = await r.json();
                renderMessages();
            } catch(e) { console.log("Ошибка связи с сервером"); }
        }, 2000);
    </script>
</body>
</html>
