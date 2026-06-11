"""
Gateway Web — Chat + Tris Multi-Stanza.

Fa da ponte tra il browser e il server TCP unificato (server.py).
Tutto — chat e tris — passa per lo stesso server sulla porta 5555.

  Browser  <--WebSocket-->  web_gateway.py  <--TCP-->  server.py
"""

import socket
import threading
import time

from flask import Flask, render_template
from flask_socketio import SocketIO

# indirizzo e porta del server TCP unificato (server.py)
TCP_HOST = "127.0.0.1"
TCP_PORT = 5555

# host e porta su cui gira l'interfaccia web
WEB_HOST = "127.0.0.1"
WEB_PORT = 8000

app = Flask(__name__)
app.config["SECRET_KEY"] = "chat-multi-stanza-gateway"
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")


@app.after_request
def add_no_cache_headers(response):
    """Evita che il browser tenga in cache static e template (utile in dev)."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# mappa: session id del browser -> bridge TCP verso server.py
bridges = {}


class Bridge:
    """Rappresenta il ponte TCP tra un singolo browser e server.py."""

    def __init__(self, sid, username, room):
        self.sid = sid
        self.username = username
        self.room = room
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False

    def connect(self):
        """Apre la connessione TCP ed esegue l'handshake (username + stanza)."""
        self.sock.connect((TCP_HOST, TCP_PORT))

        # handshake: prima username, poi stanza
        self.sock.send(self.username.encode("utf-8"))
        time.sleep(0.1)
        self.sock.send(self.room.encode("utf-8"))

        self.running = True
        # thread che ascolta i messaggi dal server e li inoltra al browser
        thread = threading.Thread(target=self._listen, daemon=True)
        thread.start()

    def _listen(self):
        """Riceve i messaggi da server.py e li inoltra al browser via WebSocket."""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                text = data.decode("utf-8")
                # il server puo' inviare piu' righe insieme: le separo
                for line in text.split("\n"):
                    line_clean = line.rstrip('\r\n')
                    if line_clean.strip():
                        socketio.emit("message", {"text": line_clean}, to=self.sid)
            except Exception:
                break

        # la connessione col server e' caduta
        if self.running:
            socketio.emit("server_closed", {}, to=self.sid)
        self.running = False

    def send(self, message):
        """Inoltra un messaggio dal browser a server.py."""
        try:
            self.sock.send(message.encode("utf-8"))
        except Exception:
            pass

    def close(self):
        """Chiude in sicurezza il ponte verso server.py."""
        self.running = False
        try:
            self.sock.send("/quit".encode("utf-8"))
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("join")
def handle_join(data):
    """Il browser chiede di entrare in una stanza: apro il ponte TCP verso server.py."""
    from flask import request

    sid = request.sid
    username = (data.get("username") or "").strip()
    room = (data.get("room") or "").strip()

    if not username or not room:
        socketio.emit("error_msg", {"text": "Username e stanza sono obbligatori."}, to=sid)
        return

    # se esiste gia' un ponte per questa sessione, lo chiudo
    old = bridges.pop(sid, None)
    if old:
        old.close()

    bridge = Bridge(sid, username, room)
    try:
        bridge.connect()
    except Exception:
        socketio.emit(
            "error_msg",
            {"text": "Impossibile connettersi al server. E' avviato (python server.py)?"},
            to=sid,
        )
        return

    bridges[sid] = bridge
    socketio.emit("joined", {"username": username, "room": room}, to=sid)


@socketio.on("send_message")
def handle_send_message(data):
    """Il browser invia un messaggio o un comando: lo inoltro a server.py."""
    from flask import request

    sid = request.sid
    bridge = bridges.get(sid)
    if not bridge:
        return

    message = (data.get("text") or "").strip()
    if not message:
        return

    bridge.send(message)

    # se l'utente esce, chiudo subito il ponte
    if message == "/quit":
        bridge.close()
        bridges.pop(sid, None)


@socketio.on("disconnect")
def handle_disconnect():
    """Il browser si e' disconnesso: chiudo il ponte TCP."""
    from flask import request

    sid = request.sid
    bridge = bridges.pop(sid, None)
    if bridge:
        bridge.close()


if __name__ == "__main__":
    print(f"Interfaccia web disponibile su http://{WEB_HOST}:{WEB_PORT}")
    print(f"(Assicurati che 'python server.py' sia in esecuzione su {TCP_HOST}:{TCP_PORT})")
    socketio.run(app, host=WEB_HOST, port=WEB_PORT, allow_unsafe_werkzeug=True)
