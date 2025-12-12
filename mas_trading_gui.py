import random
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable

import ollama  # pip install ollama

# For the small GUI
import tkinter as tk
from tkinter import scrolledtext


# =================================
# 0. Generic LLM call (via Ollama)
# =================================

def call_llm(prompt: str, model: str = "llama3") -> str:
    """
    Helper to call the local LLM via Ollama.
    Returns generated text (string).
    """
    try:
        response = ollama.generate(model=model, prompt=prompt)
        return response["response"].strip()
    except Exception as e:
        # If anything goes wrong, we fallback to a neutral answer
        print(f"[LLM ERROR] {e}")
        return "ACTION: HOLD\nSIZE: 0\nREASON: Fallback due to LLM error."


# ======================
# 1. Market Environment
# ======================

class MarketEnvironment:
    """
    Simple single-asset market:
    - price evolves as a random walk
    - generates pseudo-news based on price change
    """

    def __init__(self, initial_price: float = 100.0):
        self.price = initial_price
        self.history: List[float] = [initial_price]
        self.last_return: float = 0.0

    def step(self) -> None:
        change = random.uniform(-1.5, 1.5)
        new_price = max(1.0, self.price + change)
        self.last_return = new_price - self.price
        self.price = new_price
        self.history.append(self.price)

    def get_recent_history(self, window: int = 10) -> List[float]:
        return self.history[-window:]

    def generate_news(self) -> str:
        if self.last_return > 1.0:
            sentiment = "very positive"
            headline = "Strong rally after optimistic earnings reports."
        elif self.last_return > 0.2:
            sentiment = "slightly positive"
            headline = "Market moves up on mild positive news."
        elif self.last_return < -1.0:
            sentiment = "very negative"
            headline = "Sharp drop after unexpected bad macroeconomic data."
        elif self.last_return < -0.2:
            sentiment = "slightly negative"
            headline = "Market declines amid cautious investor sentiment."
        else:
            sentiment = "neutral"
            headline = "Market remains relatively stable with no major news."
        return f"Sentiment: {sentiment}. Headline: {headline}"

    def get_observation(self, window: int = 10) -> Dict:
        return {
            "price": self.price,
            "history": self.get_recent_history(window),
            "news": self.generate_news(),
        }


# ===============================
# 2. Basic Traders (benchmarks)
# ===============================

class Trader:
    def __init__(self, name: str, initial_cash: float = 1000.0):
        self.name = name
        self.cash = initial_cash
        self.position = 0

    def decide(self, observation: Dict) -> str:
        return "hold"

    def apply_action(self, action: str, price: float, quantity: int = 1) -> None:
        if action == "buy":
            cost = quantity * price
            if self.cash >= cost:
                self.cash -= cost
                self.position += quantity
        elif action == "sell":
            if self.position >= quantity:
                self.cash += quantity * price
                self.position -= quantity

    def get_portfolio_value(self, price: float) -> float:
        return self.cash + self.position * price


class RandomTrader(Trader):
    def decide(self, observation: Dict) -> str:
        return random.choice(["buy", "sell", "hold"])


class TrendTrader(Trader):
    def decide(self, observation: Dict) -> str:
        history = observation["history"]
        if len(history) < 2:
            return "hold"
        if history[-1] > history[-2]:
            return "buy"
        elif history[-1] < history[-2]:
            return "sell"
        return "hold"


class MeanReversionTrader(Trader):
    def decide(self, observation: Dict) -> str:
        price = observation["price"]
        history = observation["history"]
        if not history:
            return "hold"
        avg_price = sum(history) / len(history)
        if price > avg_price * 1.02:
            return "sell"
        if price < avg_price * 0.98:
            return "buy"
        return "hold"


class HoldTrader(Trader):
    def decide(self, observation: Dict) -> str:
        return "hold"


# ============================
# 3. Data classes for pipeline
# ============================

@dataclass
class Evidence:
    stance: str          # "bullish" or "bearish"
    text: str            # explanation / bullet points


@dataclass
class TradeProposal:
    action: str          # "buy" / "sell" / "hold"
    size: int            # number of units
    rationale: str       # explanation text


@dataclass
class RiskAssessment:
    agent_name: str
    approved: bool
    suggested_size: int
    comment: str


@dataclass
class ManagerDecision:
    approved: bool
    final_action: str
    final_size: int
    comment: str


@dataclass
class Portfolio:
    cash: float = 1000.0
    position: int = 0

    def value(self, price: float) -> float:
        return self.cash + self.position * price


# ===============================
# 4. Researcher Team (Bull/Bear)
# ===============================

class BullishResearcher:
    """
    Generates bullish evidence based on price, history and news.
    """

    def analyze(self, obs: Dict) -> Evidence:
        price = obs["price"]
        history = obs["history"]
        news = obs["news"]

        if len(history) >= 2 and history[-1] > history[-2]:
            trend_text = "Recent price trend is upward."
        else:
            trend_text = "Price shows potential for recovery."

        text = (
            f"- Current price: {price:.2f}\n"
            f"- {trend_text}\n"
            f"- News context: {news}\n"
            f"=> Overall, there are arguments in favor of a BUY position."
        )
        return Evidence(stance="bullish", text=text)


class BearishResearcher:
    """
    Generates bearish evidence based on price, history and news.
    """

    def analyze(self, obs: Dict) -> Evidence:
        price = obs["price"]
        history = obs["history"]
        news = obs["news"]

        if len(history) >= 2 and history[-1] < history[-2]:
            trend_text = "Recent price trend is downward."
        else:
            trend_text = "Price may be overvalued compared to recent history."

        text = (
            f"- Current price: {price:.2f}\n"
            f"- {trend_text}\n"
            f"- News context: {news}\n"
            f"=> Overall, there are arguments in favor of a SELL or cautious stance."
        )
        return Evidence(stance="bearish", text=text)


# ==============================
# 5. LLM Trader (Strategy Agent)
# ==============================

class LLMTraderAgent:
    """
    Central cognitive agent that:
    - receives bullish & bearish evidence
    - reads market context
    - uses LLM to propose a trade (action + size + rationale)
    """

    def __init__(self, name: str = "LLMFund"):
        self.name = name
        self.portfolio = Portfolio()

    def build_prompt(self, obs: Dict, bull: Evidence, bear: Evidence) -> str:
        price = obs["price"]
        history = obs["history"]
        history_str = ", ".join(f"{p:.2f}" for p in history)

        prompt = f"""
You are an experienced portfolio manager.

Market context:
- Current price: {price:.2f}
- Recent prices: [{history_str}]
- News: {obs['news']}

Bullish research team says:
{bull.text}

Bearish research team says:
{bear.text}

Task:
1. Decide a trading action among: BUY, SELL, HOLD.
2. Choose a position size between 0 and 3 units (integer).
3. Give a short one-sentence rationale.

Return your answer in the following format:
ACTION: <BUY/SELL/HOLD>
SIZE: <0-3>
REASON: <short reason>
"""
        return prompt

    def propose_trade(self, obs: Dict, bull: Evidence, bear: Evidence) -> TradeProposal:
        prompt = self.build_prompt(obs, bull, bear)
        raw = call_llm(prompt)

        action = "HOLD"
        size = 0
        rationale = raw.replace("\n", " ")

        for line in raw.splitlines():
            line_up = line.upper()
            if "ACTION:" in line_up:
                if "BUY" in line_up:
                    action = "BUY"
                elif "SELL" in line_up:
                    action = "SELL"
                else:
                    action = "HOLD"
            elif "SIZE:" in line_up:
                digits = "".join(ch for ch in line_up if ch.isdigit())
                if digits:
                    size = int(digits)

        size = max(0, min(size, 3))

        return TradeProposal(
            action=action.lower(), size=size, rationale=rationale
        )


# ==============================
# 6. Risk Management Team
# ==============================

class RiskAgent:
    def __init__(self, name: str, risk_level: str):
        self.name = name
        self.risk_level = risk_level  # "aggressive" / "neutral" / "conservative"

    def evaluate(self, proposal: TradeProposal, portfolio: Portfolio, price: float) -> RiskAssessment:
        trade_value = proposal.size * price
        total_value = portfolio.value(price)
        fraction = trade_value / total_value if total_value > 0 else 0.0

        approved = True
        suggested_size = proposal.size
        comment = f"{self.risk_level} review: "

        if self.risk_level == "aggressive":
            if fraction > 0.4:
                suggested_size = max(1, int(0.4 * total_value // price))
                comment += "trade is quite large, reducing size slightly."
            else:
                comment += "trade size acceptable."
        elif self.risk_level == "neutral":
            if fraction > 0.25:
                suggested_size = max(0, int(0.25 * total_value // price))
                comment += "trade too large, scaling down to medium size."
            else:
                comment += "trade size is fine."
        elif self.risk_level == "conservative":
            if fraction > 0.10:
                suggested_size = 0
                approved = False
                comment += "trade exceeds conservative risk limits, rejecting."
            else:
                comment += "trade acceptable under conservative limits."

        return RiskAssessment(
            agent_name=self.name,
            approved=approved,
            suggested_size=suggested_size,
            comment=comment,
        )


# =================
# 7. Manager Agent
# =================

class ManagerAgent:
    """
    Aggregates risk assessments and decides final action/size.

    OPTION 2:
    - If at least 2/3 risk agents approve => approve.
    - Use the MEDIAN suggested size instead of the minimum.
    """

    def decide(self, proposal: TradeProposal, assessments: List[RiskAssessment]) -> ManagerDecision:
        approvals = sum(1 for a in assessments if a.approved)

        if approvals >= 2 and proposal.size > 0 and proposal.action != "hold":
            sizes = sorted(a.suggested_size for a in assessments)
            median_size = sizes[1]  # median of 3 suggested sizes

            if median_size <= 0:
                return ManagerDecision(
                    approved=False,
                    final_action="hold",
                    final_size=0,
                    comment="Median suggested size is zero, downgraded to HOLD.",
                )

            comment = f"Approved by {approvals}/3 risk agents. Final size={median_size}."
            return ManagerDecision(
                approved=True,
                final_action=proposal.action,
                final_size=median_size,
                comment=comment,
            )
        else:
            return ManagerDecision(
                approved=False,
                final_action="hold",
                final_size=0,
                comment="Proposal rejected or downgraded to HOLD.",
            )


# ====================
# 8. Execution Agent
# ====================

class ExecutionAgent:
    """
    Applies manager decision to the LLM fund portfolio.
    """

    def execute(self, decision: ManagerDecision, portfolio: Portfolio, price: float) -> None:
        if not decision.approved or decision.final_action == "hold" or decision.final_size == 0:
            return

        qty = decision.final_size
        if decision.final_action == "buy":
            cost = qty * price
            if portfolio.cash >= cost:
                portfolio.cash -= cost
                portfolio.position += qty
        elif decision.final_action == "sell":
            if portfolio.position >= qty:
                portfolio.cash += qty * price
                portfolio.position -= qty


# ============================
# 9. Full simulation function
# ============================

def run_simulation(
    num_steps: int = 10,
    seed: Optional[int] = None,
    log: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Main simulation.
    `log` is a function for printing (default = print).
    In the GUI, we pass a function that writes into the text box.
    """

    if log is None:
        log = print

    if seed is not None:
        random.seed(seed)

    market = MarketEnvironment(initial_price=100.0)

    # baseline agents
    baseline_traders: List[Trader] = [
        RandomTrader("Random"),
        TrendTrader("Trend"),
        MeanReversionTrader("MeanReversion"),
        HoldTrader("Holder"),
    ]

    # LLM fund team
    bull = BullishResearcher()
    bear = BearishResearcher()
    llm_trader = LLMTraderAgent()
    risk_team = [
        RiskAgent("AggressiveRisk", "aggressive"),
        RiskAgent("NeutralRisk", "neutral"),
        RiskAgent("ConservativeRisk", "conservative"),
    ]
    manager = ManagerAgent()
    executor = ExecutionAgent()

    for t in range(num_steps):
        log(f"\n===== STEP {t + 1} =====")
        market.step()
        obs = market.get_observation(window=10)
        price = obs["price"]
        log(f"Market price: {price:.2f}")
        log(f"Market news:  {obs['news']}")

        # Baseline traders
        for trader in baseline_traders:
            action = trader.decide(obs)
            trader.apply_action(action, price, quantity=1)
            value = trader.get_portfolio_value(price)
            log(
                f"- {trader.name:12s} | action={action:>4} "
                f"| cash={trader.cash:7.2f} | pos={trader.position:3d} | value={value:7.2f}"
            )

        # === LLM Fund pipeline ===
        log("\n[LLM FUND PIPELINE]")
        bull_evidence = bull.analyze(obs)
        bear_evidence = bear.analyze(obs)
        log("Bullish evidence:\n" + bull_evidence.text)
        log("Bearish evidence:\n" + bear_evidence.text)

        proposal = llm_trader.propose_trade(obs, bull_evidence, bear_evidence)
        log(f"LLM Trader proposal: action={proposal.action}, size={proposal.size}")
        log(f"Rationale: {proposal.rationale}")

        assessments = [
            r.evaluate(proposal, llm_trader.portfolio, price) for r in risk_team
        ]
        for a in assessments:
            log(
                f"- {a.agent_name}: approved={a.approved}, "
                f"suggested_size={a.suggested_size}"
            )
            log(f"  comment: {a.comment}")

        decision = manager.decide(proposal, assessments)
        log(
            f"Manager decision: approved={decision.approved}, "
            f"final_action={decision.final_action}, final_size={decision.final_size}"
        )
        log(f"Manager comment: {decision.comment}")

        executor.execute(decision, llm_trader.portfolio, price)
        log(
            f"LLM Fund portfolio: cash={llm_trader.portfolio.cash:.2f}, "
            f"pos={llm_trader.portfolio.position}, "
            f"value={llm_trader.portfolio.value(price):.2f}"
        )

    # Final results
    log("\n===== FINAL RESULTS =====")
    final_price = market.price
    for trader in baseline_traders:
        value = trader.get_portfolio_value(final_price)
        log(f"{trader.name:12s}: final portfolio value = {value:.2f}")
    log(
        f"LLMFund     : final portfolio value = "
        f"{llm_trader.portfolio.value(final_price):.2f}"
    )


# ============================
# 10. Small Tkinter GUI
# ============================

def launch_gui():
    root = tk.Tk()
    root.title("LLM-Enhanced Multi-Agent Trading System")

    # Top frame for controls
    control_frame = tk.Frame(root)
    control_frame.pack(fill=tk.X, padx=5, pady=5)

    tk.Label(control_frame, text="Number of steps:").pack(side=tk.LEFT)
    steps_var = tk.StringVar(value="10")
    steps_entry = tk.Entry(control_frame, width=5, textvariable=steps_var)
    steps_entry.pack(side=tk.LEFT, padx=5)

    run_button = tk.Button(control_frame, text="Run Simulation")
    run_button.pack(side=tk.LEFT, padx=5)

    # Text area for logs
    text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=35)
    text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def gui_log(message: str):
        text_area.insert(tk.END, message + "\n")
        text_area.see(tk.END)
        root.update_idletasks()

    def on_run():
        text_area.delete("1.0", tk.END)
        try:
            n_steps = int(steps_var.get())
        except ValueError:
            n_steps = 10
        gui_log(f"Running simulation with {n_steps} steps...\n")
        run_simulation(num_steps=n_steps, seed=42, log=gui_log)
        gui_log("\nSimulation finished.")

    run_button.config(command=on_run)

    root.mainloop()


if __name__ == "__main__":
    # Launch the graphical interface instead of printing in the terminal
    launch_gui()
