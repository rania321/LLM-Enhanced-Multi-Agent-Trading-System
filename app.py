from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template
from flask_socketio import SocketIO
from simulation import Simulation

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

sim = Simulation()


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("start_simulation")
def start_simulation():
    # 30 steps automatiques
    for _ in range(30):
        data = sim.step()
        socketio.emit("update", data)
        socketio.sleep(1)  # 1 seconde entre chaque step


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
