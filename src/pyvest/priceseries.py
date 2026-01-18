import math

class PriceSeries:
    trading_days_per_year = 252
    
    def __init__(self, values: list[float], name: str) -> None:
        self.name = name
        self.values = list(values)

    def __repr__(self):
        return f"PriceSeries({self.name!r}, {self.values!r})"

    def __str__(self):
        if self.values:
            return f"{self.name}: {self.values[-1]: 2f} (latest)"
        
    def __len__(self):
        return len(self.values)
    
    def get_linear_return(self, t) -> list[float]:
        return (self.values[t] - self.values[t - 1]) / self.values[t - 1]
    
    def get_log_return(self, t):
        return math.log(self.values[t] / self.values[t - 1])
    
    def total_return(self) -> float:
        return (self.values[-1] - self.values[0]) / self.values[0]
    
    def get_all_linear_returns(self) -> list[float]:
        return [self.linear_return(t) for t in range(1, len(self.values))]
    
    def get_all_log_returns(self) -> list[float]:
        return [self.log_return(t) for t in range(1, len(self.values))]
    
    def annualized_volatility(self) -> float:
        log_returns = self.get_all_log_returns()
        n = len(log_returns)
        if n == 0:
            return 0.0
        mean_log_return = sum(log_returns) / n
        variance = sum((r - mean_log_return) ** 2 for r in log_returns) / n
        daily_volatility = math.sqrt(variance)
        annualized_volatility = daily_volatility * math.sqrt(self.trading_days_per_year)
        return annualized_volatility
