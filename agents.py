import random


class Trader:
    def __init__(self, name, cash=1000.0):
        self.name = name
        self.cash = cash
        self.position = 0

    def decide(self, obs):
        return "hold"

    def apply_action(self, action, price):
        if action == "buy" and self.cash >= price:
            self.cash -= price
            self.position += 1
        elif action == "sell" and self.position > 0:
            self.cash += price
            self.position -= 1

    def portfolio_value(self, price):
        return self.cash + self.position * price


class RandomTrader(Trader):
    def decide(self, obs):
        return random.choice(["buy", "sell", "hold"])


class TrendTrader(Trader):
    def decide(self, obs):
        h = obs["history"]
        if len(h) < 2:
            return "hold"
        return "buy" if h[-1] > h[-2] else "sell"


class MeanReversionTrader(Trader):
    def decide(self, obs):
        price = obs["price"]
        h = obs["history"]
        if not h:
            return "hold"
        avg = sum(h) / len(h)
        if price > avg * 1.02:
            return "sell"
        if price < avg * 0.98:
            return "buy"
        return "hold"


class HoldTrader(Trader):
    def decide(self, obs):
        return "hold"
