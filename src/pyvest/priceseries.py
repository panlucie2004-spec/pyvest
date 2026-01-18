import math

class PriceSeries:
    """
    Représentation d'une série temporelle de prix financiers.
    
    Attributes:
        values: Liste de prix indexés par le temps
        name: Identifiant de la série
    
    Class Attributes:
        TRADING_DAYS_PER_YEAR: Constante d'annualisation 
        (convention US equities, peut varier selon l'actif)
    """
    
    TRADING_DAYS_PER_YEAR: int = 252
    
    def __init__(self, values: list[float], name: str = "unnamed") -> None:
        self.values = list(values)  # Copie défensive
        self.name = name
    
    def __repr__(self) -> str:
        return f"PriceSeries({self.name!r}, {len(self.values)} values)"
    
    def __str__(self) -> str:
        if self.values:
            return f"{self.name}: {self.values[-1]:.2f} (latest)"
        return f"{self.name}: empty"
    
    def __len__(self) -> int:
        return len(self.values)
    
    def linear_return(self, t: int) -> float:
        """
        Calcule le rendement linéaire (arithmétique) entre t-1 et t.
        
        - Non ajusté des dividendes (utiliser le prix ajusté pour cela)
        - Additif entre actifs : r_portfolio = Σ(weight_i × r_i)
        
        Args:
            t: Position temporelle (doit être >= 1)

        Returns:
            Rendement en décimal (0.05 = 5%)
        """
        return (self.values[t] - self.values[t-1]) / self.values[t-1]
    
    def log_return(self, t: int) -> float:
        """
        Calcule le log-rendement entre t-1 et t.
        
        - Additif dans le temps : Σ(log returns) = log(P_T / P_0)
        - Permet d'approximer la variance multipériode par la somme des variances
        
        Args:
            t: index temporel

        Returns:
            Log-rendement
        """
        return math.log(self.values[t] / self.values[t-1])
    
    @property
    def total_return(self) -> float:
        """
        Rendement total (non annualisé) sur toute la période.
        """
        if len(self.values) < 2:
            return 0.0
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
