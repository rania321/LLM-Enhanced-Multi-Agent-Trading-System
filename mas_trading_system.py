import os
import random
from typing import List, Dict, Optional

# =========================================
# 0. (Optionnel) Gemini / LLM configuration
# =========================================


import ollama

def call_llm_for_signal(context_text: str) -> str:
    prompt = f"""
You are a trading signal generator for a financial market simulation.
Given the following context, output ONLY ONE WORD: BUY, SELL, or HOLD.

Context:
{context_text}

Answer with exactly one word: BUY or SELL or HOLD.
"""

    # Ask the local LLM
    response = ollama.generate(model="llama3", prompt=prompt)
    output = response["response"].strip().upper()

    # Normalize output
    if "BUY" in output:
        return "buy"
    if "SELL" in output:
        return "sell"
    return "hold"


# ======================
# 1. Market Environment
# ======================

class MarketEnvironment:
    """
    Environnement = notre marché.
    - Gère le prix
    - Gère l'historique
    - Génère des "fake news" textuelles
    """

    def __init__(self, initial_price: float = 100.0):
        self.price = initial_price
        self.history: List[float] = [initial_price]
        self.last_return: float = 0.0  # variation du dernier step

    def step(self) -> None:
        """
        Fait évoluer le prix selon un random walk simple.
        """
        change = random.uniform(-1.5, 1.5)  # variation entre -1.5 et +1.5
        new_price = max(1.0, self.price + change)  # éviter prix <= 0
        self.last_return = new_price - self.price
        self.price = new_price
        self.history.append(self.price)

    def get_recent_history(self, window: int = 10) -> List[float]:
        return self.history[-window:]

    def generate_news(self) -> str:
        """
        Génère une pseudo news textuelle en fonction de la variation récente.
        C'est ce texte qu'on enverra au LLM.
        """
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

        news = f"Sentiment: {sentiment}. Headline: {headline}"
        return news

    def get_observation(self, window: int = 10) -> Dict:
        """
        Observation partagée à tous les agents.
        """
        return {
            "price": self.price,
            "history": self.get_recent_history(window),
            "news": self.generate_news(),
        }


# ======================
# 2. Base Trader class
# ======================

class Trader:
    """
    Classe de base pour un trader.
    Chaque trader a:
    - un nom
    - du cash
    - une position (nombre d'actions)
    """

    def __init__(self, name: str, initial_cash: float = 1000.0):
        self.name = name
        self.cash = initial_cash
        self.position = 0

    def decide(self, observation: Dict) -> str:
        """
        Décide une action: 'buy', 'sell' ou 'hold'.
        Les classes enfants surchargent cette méthode.
        """
        return "hold"

    def apply_action(self, action: str, price: float, quantity: int = 1) -> None:
        """
        Applique l'action au portefeuille (cash + position).
        Marché très simple: ordre à prix courant.
        """
        if action == "buy":
            cost = quantity * price
            if self.cash >= cost:
                self.cash -= cost
                self.position += quantity
        elif action == "sell":
            if self.position >= quantity:
                self.cash += quantity * price
                self.position -= quantity
        # 'hold' -> on ne fait rien

    def get_portfolio_value(self, price: float) -> float:
        return self.cash + self.position * price


# ======================
# 3. Différents types de traders
# ======================

class RandomTrader(Trader):
    """
    Trader qui achète / vend / hold au hasard.
    """

    def decide(self, observation: Dict) -> str:
        return random.choice(["buy", "sell", "hold"])


class TrendTrader(Trader):
    """
    Trader "trend-following":
    - Si le prix monte -> buy
    - Si le prix baisse -> sell
    """

    def decide(self, observation: Dict) -> str:
        history = observation["history"]
        if len(history) < 2:
            return "hold"
        if history[-1] > history[-2]:
            return "buy"
        elif history[-1] < history[-2]:
            return "sell"
        else:
            return "hold"


class MeanReversionTrader(Trader):
    """
    Trader 'mean-reversion':
    - Si le prix est > moyenne * 1.02 -> sell
    - Si le prix est < moyenne * 0.98 -> buy
    """

    def decide(self, observation: Dict) -> str:
        price = observation["price"]
        history = observation["history"]
        if not history:
            return "hold"
        avg_price = sum(history) / len(history)
        if price > avg_price * 1.02:
            return "sell"
        elif price < avg_price * 0.98:
            return "buy"
        else:
            return "hold"


class HoldTrader(Trader):
    """
    Trader très conservateur qui ne fait rien.
    """

    def decide(self, observation: Dict) -> str:
        return "hold"


class LLMTrader(Trader):
    """
    Trader "intelligent" qui demande conseil au LLM.
    """

    def decide(self, observation: Dict) -> str:
        price = observation["price"]
        history = observation["history"]
        news = observation["news"]

        # On construit un texte de contexte pour le LLM
        history_str = ", ".join(f"{p:.2f}" for p in history)
        context = f"""
Current price: {price:.2f}
Recent prices: [{history_str}]
Market news: {news}

Based on this context, decide whether it is better to BUY, SELL, or HOLD the asset for the next step.
"""

        action = call_llm_for_signal(context)
        # Optionnel: print pour debug
        # print(f"[LLMTrader] Context: {context}\n -> Action: {action}")
        return action


# ======================
# 4. Simulation MAS
# ======================

def run_simulation(num_steps: int = 30, seed: Optional[int] = None) -> None:
    """
    Fonction principale qui lance la simulation.
    """

    if seed is not None:
        random.seed(seed)

    market = MarketEnvironment(initial_price=100.0)

    traders: List[Trader] = [
        RandomTrader("Random"),
        TrendTrader("Trend"),
        MeanReversionTrader("MeanReversion"),
        HoldTrader("Holder"),
        LLMTrader("LLM"),
    ]

    for t in range(num_steps):
        print(f"\n===== Step {t + 1} =====")

        # 1) Le marché avance d'un pas de temps
        market.step()
        observation = market.get_observation(window=10)
        price = observation["price"]

        print(f"Market price: {price:.2f}")
        print(f"Market news:  {observation['news']}")

        # 2) Chaque trader décide et applique son action
        for trader in traders:
            action = trader.decide(observation)
            trader.apply_action(action, price, quantity=1)
            value = trader.get_portfolio_value(price)
            print(
                f"- {trader.name:12s} | action={action:>4} "
                f"| cash={trader.cash:7.2f} "
                f"| pos={trader.position:3d} "
                f"| value={value:7.2f}"
            )

    # 3) Résultats finaux
    print("\n===== FINAL RESULTS =====")
    final_price = market.price
    for trader in traders:
        value = trader.get_portfolio_value(final_price)
        print(f"{trader.name:12s}: final portfolio value = {value:.2f}")


if __name__ == "__main__":
    # Tu peux changer le seed pour des runs reproductibles
    run_simulation(num_steps=30, seed=42)
