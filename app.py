from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template
from flask_socketio import SocketIO
from simulation import Simulation

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

sim = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@socketio.on("start_simulation")
def start_simulation():
    global sim
    sim = Simulation()
    
    # Run 30 simulation steps
    for step in range(30):
        data = sim.step()
        data['step'] = step + 1
        data['total_steps'] = 30
        socketio.emit("update", data)
        socketio.sleep(1)
    
    # Emit simulation finished
    socketio.emit("simulation_finished", {
        "message": "Simulation completed successfully",
        "total_steps": 30
    })


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
