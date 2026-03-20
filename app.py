import os
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
messages = []

# Дизайн твоего чата
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>TegeGrom Cloud</title>
    <style>
        body { background: #0e1621; color: white; font-family: sans-serif; text-align: center; padding: 20px; }
        #chat { border: 1px solid #2b5278; height: 350px; overflow-y: auto; background: #17212b; padding: 15px; border-radius: 10px; text-align: left; margin-bottom: 10px; }
        input { padding: 12px; width: 70%; border-radius: 10px; border: none; margin: 5px; background: #242f3d; color: white; }
        button { padding: 12px 25px; background: #2b5278; color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: bold; }
        .msg { margin-bottom: 8px; border-bottom: 1px solid #242f3d; padding-bottom: 5px; }
    </style>
</head>
<body>
    <h2>TegeGrom Cloud ☁️</h2>
    <div id="chat"></div>
    <input id="u" placeholder="Твой ник">
    <input id="m" placeholder="Сообщение...">
    <button onclick="send()">ОТПРАВИТЬ</button>

    <script>
        function send() {
            const u = document.getElementById('u').value || "Аноним";
            const m = document.getElementById('m').value;
            if(!m) return;
            fetch('/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({u, m})
            });
            document.getElementById('m').value = "";
        }
        // Обновление сообщений каждые 2 секунды
        setInterval(() => {
            fetch('/get').then(r => r.json()).then(data => {
                document.getElementById('chat').innerHTML = data.map(msg => `
                    <div class="msg"><b>${msg.u}:</b> ${msg.m}</div>
                `).join('');
            });
        }, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/send', methods=['POST'])
def send():
    messages.append(request.json)
    if len(messages) > 50: messages.pop(0) # Храним только последние 50 сообщений
    return jsonify({'ok': True})

@app.route('/get')
def get():
    return jsonify(messages)

if __name__ == "__main__":
    # Render сам скажет, какой порт использовать
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
