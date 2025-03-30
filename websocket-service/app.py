import os
import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
app.config["SECRET_KEY"] = "some-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

@app.route("/")
def index():
    return "Flask-SocketIO (Production)"

@app.route("/notify_change", methods=["POST"])
def notify_change():
    data = request.get_json() or {}
    message = data.get("message", "No message provided")
    socketio.emit("task_update", {"message": message})
    return {"status": "ok", "broadcasted": message}

@socketio.on("connect")
def on_connect():
    print("A client connected.")

@socketio.on("disconnect")
def on_disconnect():
    print("A client disconnected.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
