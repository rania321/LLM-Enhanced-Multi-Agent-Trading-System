from dataclasses import dataclass
from typing import List, Dict
import random

from market import MarketEnvironment
from agents import RandomTrader, TrendTrader, MeanReversionTrader, HoldTrader
from llm_module import call_llm


# =========================
# Data structures
# =========================

@dataclass
class Portfolio:
    cash: float = 1000.0
    position: int = 0

    def value(self, price: float) -> float:
        return self.cash + self.position * price


@dataclass
class Evidence:
    stance: str
    text: str


@dataclass
class TradeProposal:
    action: str  # "buy" / "sell" / "hold"
    size: int
    rationale: str


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


# =========================
# Research Agents
# =========================

class BullishResearcher:
    def analyze(self, obs: Dict) -> Evidence:
        price = obs["price"]
        h = obs["history"]
        news = obs["news"]

        if len(h) >= 2 and h[-1] > h[-2]:
            trend = "Recent price trend is upward."
        else:
            trend = "Price may recover from recent levels."

        text = (
            f"- Current price: {price:.2f}\n"
            f"- {trend}\n"
            f"- News context: {news}\n"
            f"=> Arguments in favor of a BUY position."
        )
        return Evidence("bullish", text)


class BearishResearcher:
    def analyze(self, obs: Dict) -> Evidence:
        price = obs["price"]
        h = obs["history"]
        news = obs["news"]

        if len(h) >= 2 and h[-1] < h[-2]:
            trend = "Recent price trend is downward."
        else:
            trend = "Price may be overvalued vs. recent history."

        text = (
            f"- Current price: {price:.2f}\n"
            f"- {trend}\n"
            f"- News context: {news}\n"
            f"=> Arguments in favor of a SELL or cautious stance."
        )
        return Evidence("bearish", text)


class GeneralResearchAgent:
    """
    Neutral LLM-based research agent.
    Provides a balanced market analysis.
    """

    def analyze(self, obs: Dict) -> Evidence:
        prompt = f"""
You are a senior financial market analyst.

Market data:
- Current price: {obs['price']:.2f}
- Recent price history: {obs['history'][-10:]}
- News: {obs['news']}

Task:
1. Analyze the overall market situation.
2. Indicate whether the market is BULLISH, BEARISH, or NEUTRAL.
3. Give a short explanation (2–3 sentences).

Return format:
STANCE: <BULLISH / BEARISH / NEUTRAL>
ANALYSIS: <short explanation>
"""
        raw = call_llm(prompt)

        stance = "neutral"
        up = raw.upper()
        if "BULLISH" in up:
            stance = "bullish"
        elif "BEARISH" in up:
            stance = "bearish"

        return Evidence(stance=stance, text=raw)


# =========================
# LLM Trader Agent
# =========================

class LLMTraderAgent:
    def __init__(self):
        self.portfolio = Portfolio()

    def build_prompt(
        self,
        obs: Dict,
        bull: Evidence,
        bear: Evidence,
        general: Evidence
    ) -> str:
        price = obs["price"]
        h = obs["history"]
        hist_str = ", ".join(f"{p:.2f}" for p in h)

        prompt = f"""
You are an experienced portfolio manager in a trading team.

Market context:
- Current price: {price:.2f}
- Recent prices: [{hist_str}]
- News: {obs['news']}

Bullish research:
{bull.text}

Bearish research:
{bear.text}

General market analysis:
{general.text}

Task:
1. Decide a trading ACTION among: BUY, SELL, HOLD.
2. Choose a position SIZE between 0 and 3 (integer).
3. Explain your decision in one short sentence.

IMPORTANT RULE:
- If ACTION is HOLD, SIZE must be 0.

Return exactly this format:
ACTION: <BUY/SELL/HOLD>
SIZE: <0-3>
REASON: <short text>
"""
        return prompt

    def propose_trade(
        self,
        obs: Dict,
        bull: Evidence,
        bear: Evidence,
        general: Evidence
    ) -> TradeProposal:

        prompt = self.build_prompt(obs, bull, bear, general)
        raw = call_llm(prompt)

        action = "HOLD"
        size = 0
        rationale = raw.replace("\n", " ")

        for line in raw.splitlines():
            up = line.upper()
            if "ACTION:" in up:
                if "BUY" in up:
                    action = "BUY"
                elif "SELL" in up:
                    action = "SELL"
                else:
                    action = "HOLD"
            elif "SIZE:" in up:
                digits = "".join(c for c in up if c.isdigit())
                if digits:
                    size = int(digits)

        # Safety clamp
        if action == "HOLD":
            size = 0
        size = max(0, min(size, 3))

        return TradeProposal(action=action.lower(), size=size, rationale=rationale)


# =========================
# Risk, Manager, Execution
# =========================

class RiskAgent:
    def __init__(self, name: str, level: str):
        self.name = name
        self.level = level  # "aggressive", "neutral", "conservative"

    def evaluate(
        self,
        proposal: TradeProposal,
        portfolio: Portfolio,
        price: float
    ) -> RiskAssessment:

        trade_value = proposal.size * price
        total = portfolio.value(price)
        fraction = trade_value / total if total > 0 else 0.0

        approved = True
        suggested_size = proposal.size
        comment = f"{self.level} review: "

        if self.level == "aggressive":
            if fraction > 0.4:
                suggested_size = max(1, int(0.4 * total // price))
                comment += "trade large, scaling down slightly."
            else:
                comment += "size acceptable."

        elif self.level == "neutral":
            if fraction > 0.25:
                suggested_size = max(0, int(0.25 * total // price))
                comment += "trade too big, scaling to medium size."
            else:
                comment += "size fine."

        else:  # conservative
            if fraction > 0.10:
                approved = False
                suggested_size = 0
                comment += "exceeds conservative risk limits, rejecting."
            else:
                comment += "acceptable under conservative policy."

        return RiskAssessment(self.name, approved, suggested_size, comment)


class ManagerAgent:
    """
    Majority vote + median size rule.
    """

    def decide(
        self,
        proposal: TradeProposal,
        assessments: List[RiskAssessment]
    ) -> ManagerDecision:

        approvals = sum(1 for a in assessments if a.approved)

        if approvals >= 2 and proposal.action != "hold" and proposal.size > 0:
            sizes = sorted(a.suggested_size for a in assessments)
            median_size = sizes[1]

            if median_size <= 0:
                return ManagerDecision(
                    False, "hold", 0,
                    "Median size is zero, downgraded to HOLD."
                )

            return ManagerDecision(
                True,
                proposal.action,
                median_size,
                f"Approved by {approvals}/3 risk agents. Final size={median_size}."
            )

        return ManagerDecision(
            False, "hold", 0,
            "Proposal rejected or downgraded to HOLD."
        )


class ExecutionAgent:
    def execute(
        self,
        decision: ManagerDecision,
        portfolio: Portfolio,
        price: float
    ):
        if not decision.approved or decision.final_action == "hold" or decision.final_size == 0:
            return

        q = decision.final_size

        if decision.final_action == "buy":
            cost = q * price
            if portfolio.cash >= cost:
                portfolio.cash -= cost
                portfolio.position += q

        elif decision.final_action == "sell":
            if portfolio.position >= q:
                portfolio.cash += q * price
                portfolio.position -= q


# =========================
# Simulation
# =========================

class Simulation:
    def __init__(self):
        self.market = MarketEnvironment()

        self.traders = [
            RandomTrader("Random"),
            TrendTrader("Trend"),
            MeanReversionTrader("MeanReversion"),
            HoldTrader("Holder"),
        ]

        self.bull = BullishResearcher()
        self.bear = BearishResearcher()
        self.general = GeneralResearchAgent()

        self.llm_trader = LLMTraderAgent()

        self.risk_team = [
            RiskAgent("AggressiveRisk", "aggressive"),
            RiskAgent("NeutralRisk", "neutral"),
            RiskAgent("ConservativeRisk", "conservative"),
        ]

        self.manager = ManagerAgent()
        self.executor = ExecutionAgent()

    def step(self) -> Dict:
        self.market.step()
        obs = self.market.get_obs()
        price = obs["price"]

        # 1) Classic traders
        decisions = []
        for t in self.traders:
            action = t.decide(obs)
            t.apply_action(action, price)
            decisions.append({
                "name": t.name,
                "action": action,
                "cash": round(t.cash, 2),
                "pos": t.position,
                "value": round(t.portfolio_value(price), 2),
            })

        # 2) LLM Fund pipeline
        bull_ev = self.bull.analyze(obs)
        bear_ev = self.bear.analyze(obs)
        general_ev = self.general.analyze(obs)

        proposal = self.llm_trader.propose_trade(
            obs, bull_ev, bear_ev, general_ev
        )

        assessments = [
            r.evaluate(proposal, self.llm_trader.portfolio, price)
            for r in self.risk_team
        ]

        decision = self.manager.decide(proposal, assessments)
        self.executor.execute(decision, self.llm_trader.portfolio, price)

        llm_info = {
            "bullish": bull_ev.text,
            "bearish": bear_ev.text,
            "general_analysis": {
                "stance": general_ev.stance,
                "text": general_ev.text,
            },
            "proposal": {
                "action": proposal.action,
                "size": proposal.size,
                "rationale": proposal.rationale,
            },
            "risk_assessments": [
                {
                    "name": a.agent_name,
                    "approved": a.approved,
                    "size": a.suggested_size,
                    "comment": a.comment,
                } for a in assessments
            ],
            "manager_decision": {
                "approved": decision.approved,
                "final_action": decision.final_action,
                "final_size": decision.final_size,
                "comment": decision.comment,
            },
            "portfolio": {
                "cash": round(self.llm_trader.portfolio.cash, 2),
                "pos": self.llm_trader.portfolio.position,
                "value": round(self.llm_trader.portfolio.value(price), 2),
            },
        }

        return {
            "price": price,
            "history": self.market.history[-40:],
            "news": obs["news"],
            "decisions": decisions,
            "llm": llm_info,
        }
