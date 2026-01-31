# Fichier: pyvest/src/asset.py

from .priceseries import PriceSeries
from .constant import CurrencyEnum


class Asset:
    """
    Représente un actif financier avec son historique de prix.
    Pattern de conception : COMPOSITION
    Asset POSSÈDE une PriceSeries (relation HAS-A, pas IS-A).
    ───────────────────────────────────
    Attributes:
        ticker: Symbole (ex: 'AAPL')
        prices: Instance PriceSeries contenant l'historique
        sector: Classification sectorielle optionnelle
        currency: Devise des prix (défaut: USD)
    """
    
    def __init__(
        self, 
        ticker: str, 
        prices: PriceSeries,
        sector: str | None = None,
        currency: CurrencyEnum = CurrencyEnum.USD
    ) -> None:
        # Validation des entrées dans le constructeur
        if not ticker or not ticker.strip():
            raise ValueError("Le ticker ne peut pas être vide")
        if len(prices) == 0:
            raise ValueError("La série de prix ne peut pas être vide")
        
        self.ticker = ticker.upper()  # Normalisation en majuscules
        self.prices = prices  # Composition : Asset POSSÈDE une PriceSeries
        self.sector = sector
        self.currency = currency
    
    def __repr__(self) -> str:
        """Représentation pour le développement."""
        return f"Asset({self.ticker!r}, {len(self.prices)} prices)"
    
    #Gemini
    @property
    def current_price(self) -> float:
        return self.prices.values[-1]
    #Fin gemini

    def __str__(self) -> str:
        """Représentation pour l'utilisateur."""
        return f"{self.ticker}: ${self.current_price:.2f}"