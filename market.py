import random


class MarketEnvironment:
    def __init__(self, initial_price=100.0):
        self.price = initial_price
        self.history = [initial_price]
        self.last_return = 0.0

    def step(self):
        change = random.uniform(-1.5, 1.5)
        new_price = max(1, self.price + change)
        self.last_return = new_price - self.price
        self.price = new_price
        self.history.append(self.price)

    def get_news(self):
        if self.last_return > 1.0:
            return "Very positive news! Market rally after strong earnings."
        elif self.last_return > 0.2:
            return "Slightly positive news. Market moving upward."
        elif self.last_return < -1.0:
            return "Very negative news! Market crashing because of macro data."
        elif self.last_return < -0.2:
            return "Slightly negative sentiment. Market declining."
        else:
            return "Neutral news. No significant changes."

    def get_obs(self):
        return {
            "price": self.price,
            "history": self.history[-20:],
            "news": self.get_news(),
        }
