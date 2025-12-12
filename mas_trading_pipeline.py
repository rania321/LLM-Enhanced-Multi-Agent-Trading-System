import random
from dataclasses import dataclass
from typing import List, Dict, Optional

import ollama  # make sure `pip install ollama` and `ollama pull llama3`


# ============================
# 0. Generic LLM call (Ollama)
# ============================

def call_llm(prompt: str, model: str = "llama3") -> str:
    """
    Generic helper to call the local LLM via Ollama.
    Returns plain text.
    """
    try:
        response = ollama.generate(model=model, prompt=prompt)
        return response["response"].strip()
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return ""


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
    (Here done with simple rules & a bit of LLM-style phrasing.)
    """

    def analyze(self, obs: Dict) -> Evidence:
        price = obs["price"]
        history = obs["history"]
        news = obs["news"]

        trend_text = ""
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

        trend_text = ""
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

        # Very simple parsing
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

        # clamp
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
        # risk: fraction of capital involved
        trade_value = proposal.size * price
        total_value = portfolio.value(price)
        fraction = trade_value / total_value if total_value > 0 else 0.0

        approved = True
        suggested_size = proposal.size
        comment = f"{self.risk_level} review: "

        if self.risk_level == "aggressive":
            # allows up to 40% of capital in one trade
            if fraction > 0.4:
                suggested_size = max(1, int(0.4 * total_value // price))
                comment += "trade is quite large, reducing size slightly."
            else:
                comment += "trade size acceptable."
        elif self.risk_level == "neutral":
            # allows up to 25%
            if fraction > 0.25:
                suggested_size = max(0, int(0.25 * total_value // price))
                comment += "trade too large, scaling down to medium size."
            else:
                comment += "trade size is fine."
        elif self.risk_level == "conservative":
            # allows up to 10%
            if fraction > 0.10:
                suggested_size = 0  # reject by setting size 0
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
    Simple rule: if at least 2/3 risk agents approve -> approve.
    """

    def decide(self, proposal: TradeProposal, assessments: List[RiskAssessment]) -> ManagerDecision:
        approvals = sum(1 for a in assessments if a.approved)
        if approvals >= 2 and proposal.size > 0 and proposal.action != "hold":
            final_size = min(a.suggested_size for a in assessments)
            comment = f"Approved by {approvals}/3 risk agents. Final size={final_size}."
            return ManagerDecision(
                approved=True,
                final_action=proposal.action,
                final_size=final_size,
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

def run_simulation(num_steps: int = 20, seed: Optional[int] = None) -> None:
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

    # LLM Fund team
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
        print(f"\n===== STEP {t + 1} =====")
        market.step()
        obs = market.get_observation(window=10)
        price = obs["price"]
        print(f"Market price: {price:.2f}")
        print(f"Market news:  {obs['news']}")

        # Baseline traders
        for trader in baseline_traders:
            action = trader.decide(obs)
            trader.apply_action(action, price, quantity=1)
            value = trader.get_portfolio_value(price)
            print(
                f"- {trader.name:12s} | action={action:>4} "
                f"| cash={trader.cash:7.2f} | pos={trader.position:3d} | value={value:7.2f}"
            )

        # === LLM Fund pipeline ===
        print("\n[LLM FUND PIPELINE]")
        bull_evidence = bull.analyze(obs)
        bear_evidence = bear.analyze(obs)
        print("Bullish evidence:\n", bull_evidence.text)
        print("Bearish evidence:\n", bear_evidence.text)

        proposal = llm_trader.propose_trade(obs, bull_evidence, bear_evidence)
        print(f"LLM Trader proposal: action={proposal.action}, size={proposal.size}")
        print(f"Rationale: {proposal.rationale}")

        assessments = [
            r.evaluate(proposal, llm_trader.portfolio, price) for r in risk_team
        ]
        for a in assessments:
            print(f"- {a.agent_name}: approved={a.approved}, suggested_size={a.suggested_size}")
            print(f"  comment: {a.comment}")

        decision = manager.decide(proposal, assessments)
        print(
            f"Manager decision: approved={decision.approved}, "
            f"final_action={decision.final_action}, final_size={decision.final_size}"
        )
        print(f"Manager comment: {decision.comment}")

        # Execute if approved
        executor.execute(decision, llm_trader.portfolio, price)
        print(
            f"LLM Fund portfolio: cash={llm_trader.portfolio.cash:.2f}, "
            f"pos={llm_trader.portfolio.position}, "
            f"value={llm_trader.portfolio.value(price):.2f}"
        )

    # === Final results ===
    print("\n===== FINAL RESULTS =====")
    final_price = market.price
    for trader in baseline_traders:
        value = trader.get_portfolio_value(final_price)
        print(f"{trader.name:12s}: final portfolio value = {value:.2f}")
    print(
        f"LLMFund     : final portfolio value = "
        f"{llm_trader.portfolio.value(final_price):.2f}"
    )


if __name__ == "__main__":
    run_simulation(num_steps=10, seed=42)
