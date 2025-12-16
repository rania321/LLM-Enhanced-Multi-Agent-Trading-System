# 📈 LLM-Enhanced Multi-Agent Trading System

A **real-time trading simulation** combining **Multi-Agent Systems (MAS)** with **LLM-based reasoning**, featuring an **interactive dashboard** and **live decision visualization**.

---

## ✨ Highlights

- 🧠 **LLM-driven trading agent** with risk-aware position sizing  
- 🤖 **Multiple interacting trader agents** (rule-based + LLM)  
- ⚖️ **Governance layer** with risk agents and manager approval  
- 📊 **Live dashboard** with charts, news, and agent activity  
- 🔄 **Real-time updates** via Socket.IO  
- 🎓 Designed for **academic demos & presentations**

---

## 🧠 How It Works (High Level)

Market Environment
        ↓
Classic Traders (Rule-Based)
        ↓
Research Layer
 ├─ Bullish Agent
 ├─ Bearish Agent
 └─ General Research Agent (LLM)
        ↓
LLM Trader (Action + Size)
        ↓
Risk Agents
        ↓
Manager Agent
        ↓
Execution


---

## 🤖 Agents Overview

### Classic Traders
Simple baseline agents trading **1 unit at a time**:

- `RandomTrader`
- `TrendTrader`
- `MeanReversionTrader`
- `HoldTrader`

---

### Research Agents

- **BullishResearcher** → optimistic analysis (rule-based)  
- **BearishResearcher** → pessimistic analysis (rule-based)  
- **GeneralResearchAgent (LLM)** → neutral, high-level reasoning  

These agents **do not trade**.  
They only provide **market analysis** to support decision-making.

---

### LLM Trader

- Synthesizes all research outputs  
- Chooses **BUY / SELL / HOLD**  
- Decides **position size (0–3)**  
- Subject to governance and risk checks  

This agent represents an **institutional-style trader**.

---

### Governance

- **Risk Agents**  
  - Aggressive  
  - Neutral  
  - Conservative  

- **Manager Agent**  
  - Majority vote  
  - Median position size  

- **Execution Agent**  
  - Safe portfolio updates  
  - Prevents invalid trades  

---

## 🖥️ Frontend

- Modern landing page  
- Live trading dashboard  
- Real-time price chart (Chart.js)  
- Market news & sentiment display  
- Agent activity tracking  
- LLM decision pipeline visualization  
- Responsive & animated UI  

---

## 📂 Project Structure
.
├─ app.py              # Flask + Socket.IO backend
├─ simulation.py       # Core MAS logic
├─ market.py           # Market environment
├─ agents.py           # Rule-based traders
├─ llm_module.py       # LLM interface
│
├─ templates/
│   ├─ index.html
│   └─ dashboard.html
│
├─ static/
│   ├─ css/
│   │   └─ styles.css
│   └─ js/
│       ├─ landing.js
│       └─ dashboard.js
│
└─ README.md


---

## ▶️ Getting Started

### Prerequisites

- Python **3.9+**
- An LLM backend (e.g. **Ollama**)

---

### Install dependencies

pip install flask flask-socketio gevent


### Run the app
python app.py

### Open in browser
http://127.0.0.1:5000


### Click Start Simulation to begin.

## 🧪 Scope & Assumptions

- Single-asset market (stock/crypto-like)

- No learning (no RL)

- Fixed environment

- Focus on decision-making quality, not prediction accuracy

## 🎓 Why This Project?

This project shows how LLMs can be integrated into a Multi-Agent System without replacing traditional agents:

LLMs are used only where reasoning is needed

Risk & execution remain deterministic

Decisions are explainable and structured

## 🚀 Future Improvements

Dynamic volatility regimes

Market shocks (crashes / bull runs)

Multiple assets

Learning agents (RL)

User-defined simulation parameters

## 📜 License

This project is for educational and research purposes done by Rania GUELMAMI, Wejden Nasfi and Eya BENOUHIBA